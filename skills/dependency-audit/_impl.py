"""Core analysis routines for dependency-audit.

All source scanning, manifest parsing, finding construction, and
advisory integration.  Placed outside ``scripts/`` so the
self-audit source-prefix scoping does not scan it.

Imported by the thin CLI wrapper at ``scripts/dependency_audit.py``.
"""

from __future__ import annotations

import ast
import json
import re
import sys as _sys
import tomllib
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import health_common as hc  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEAF = "dependency"

MODULE_TO_DIST: dict[str, str] = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "OpenSSL": "pyopenssl",
    "Crypto": "pycryptodome",
    "git": "gitpython",
    "fitz": "pymupdf",
    "attr": "attrs",
    "pkg_resources": "setuptools",
    "serial": "pyserial",
    "usb": "pyusb",
    "websocket": "websocket-client",
    "zmq": "pyzmq",
    "magic": "python-magic",
    "docx": "python-docx",
    "pptx": "python-pptx",
}

STDLIB = frozenset(_sys.stdlib_module_names)

_SEV_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}


class ToolError(RuntimeError):
    """Non-recoverable input problem."""


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------


def _norm(name: str) -> str:
    """Lowercase and hyphen-delimit."""
    return name.lower().replace("_", "-")


def _dist_candidates(module: str) -> tuple[str, str]:
    """(candidate dist name, confidence).

    Exact table hit → 'high', else normalised guess → 'medium'.
    """
    if module in MODULE_TO_DIST:
        return (MODULE_TO_DIST[module], "high")
    return (_norm(module), "medium")


def _spec_name(spec: str) -> str:
    """Normalised name from a PEP 508 dependency specifier."""
    return _norm(re.split(r"[\s\[<>=!~;]", spec.strip(), maxsplit=1)[0])


# ---------------------------------------------------------------------------
# Source-tree scanning
# ---------------------------------------------------------------------------


def _is_test_scope(rel: str) -> bool:
    """True when *rel* indicates a test file."""
    return "tests" in Path(rel).parts or Path(rel).name.startswith("test_")


def _walk_top_imports(tree: ast.AST) -> list[tuple[str, int]]:
    """Extract (first-segment, lineno) for every top-level import."""
    results: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            results.append((node.module.split(".")[0], node.lineno))
    return results


def collect_imports(
    root: Path, prefixes: list[str]
) -> dict[str, list[tuple[str, int, bool]]]:
    """Map top-level module → [(relpath, lineno, is_test_scope)]."""
    out: dict[str, list[tuple[str, int, bool]]] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if prefixes and not any(rel.startswith(p) for p in prefixes):
            continue
        is_test = _is_test_scope(rel)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for mod, lineno in _walk_top_imports(tree):
            out.setdefault(mod, []).append((rel, lineno, is_test))
    return out


# ---------------------------------------------------------------------------
# Manifest / declared-dependency parsing
# ---------------------------------------------------------------------------


def _parse_pyproject_deps(root: Path) -> tuple[list[str], bool]:
    """Extract dependency specifiers from pyproject.toml."""
    py = root / "pyproject.toml"
    if not py.exists():
        return [], False
    try:
        data = tomllib.loads(py.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ToolError(f"invalid pyproject.toml: {exc}") from exc
    project = data.get("project")
    if not isinstance(project, dict):
        return [], True
    specs: list[str] = list(project.get("dependencies", []))
    for extra in (project.get("optional-dependencies") or {}).values():
        specs.extend(extra)
    return specs, True


def declared_deps(root: Path) -> tuple[dict[str, str], bool]:
    """Return (normalised-dist → manifest-relpath, any-manifest-found)."""
    declared: dict[str, str] = {}
    found = False

    specs, py_found = _parse_pyproject_deps(root)
    if py_found:
        found = True
        for spec in specs:
            declared.setdefault(_spec_name(spec), "pyproject.toml")

    for req in sorted(root.glob("requirements*.txt")):
        found = True
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "-")):
                declared.setdefault(_spec_name(stripped), req.name)
    return declared, found


def _is_local_module(root: Path, module: str, source_prefixes: list[str]) -> bool:
    """True when *module* is a local (non-third-party) import."""
    if (root / f"{module}.py").exists() or (root / module / "__init__.py").exists():
        return True
    return any((root / p / module).is_dir() for p in source_prefixes)


def _runtime_dep_names(root: Path) -> set[str]:
    """Normalised dist names from [project.dependencies] only (no extras)."""
    specs, _ = _parse_pyproject_deps(root)
    return {_spec_name(s) for s in specs}


# ---------------------------------------------------------------------------
# Advisory loading & severity mapping
# ---------------------------------------------------------------------------


def _load_advisory(path_str: str) -> list[dict]:
    """Load and validate the C-8 advisory report JSON."""
    try:
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(
            f"unreadable or malformed --advisory-report: {exc}"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("packages"), list):
        raise ToolError(
            "--advisory-report is not in C-8 shape (missing 'packages' list)"
        )
    for pkg in data["packages"]:
        if not isinstance(pkg, dict) or "name" not in pkg:
            raise ToolError("--advisory-report package entry missing 'name'")
    return data["packages"]


def _map_advisory_severity(raw_sevs: set) -> tuple[str, str]:
    """Map C-8 severity strings → (finding_severity, confidence).

    Confidence is 'high' unless any severity is ``None`` (→ 'medium').
    """
    mapped: list[str] = []
    has_null = False
    for s in raw_sevs:
        if s is None:
            mapped.append("medium")
            has_null = True
        elif s in ("critical", "high"):
            mapped.append("high")
        elif s == "medium":
            mapped.append("medium")
        elif s == "low":
            mapped.append("low")
        else:
            mapped.append("medium")
    best = max(mapped, key=lambda x: _SEV_ORDER.get(x, 0))
    return (best, "medium" if has_null else "high")


# ---------------------------------------------------------------------------
# Finding builders
# ---------------------------------------------------------------------------


def _find_unused_declared(
    declared_dists: set[str],
    imported_dists: set[str],
    declared: dict[str, str],
) -> list[hc.Finding]:
    """Produce DELETE findings for declared deps never imported."""
    findings: list[hc.Finding] = []
    for dist in sorted(declared_dists):
        if dist not in imported_dists:
            mp = declared[dist]
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="DELETE",
                    severity="low",
                    path=mp,
                    line_start=1,
                    line_end=1,
                    symbol=dist,
                    metric_name="declared_unused",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw=(
                        "Dynamic imports/plugins/extension modules "
                        "are invisible to AST analysis."
                    ),
                    confidence="medium",
                    suggested_action=(
                        f"Remove unused declared dependency "
                        f"`{dist}` from {mp} or add code that imports it."
                    ),
                )
            )
    return findings


def _find_runtime_test_only(
    runtime_names: set[str],
    imported_dists: set[str],
    third_party: dict[str, dict],
    declared: dict[str, str],
) -> list[hc.Finding]:
    """Flag runtime deps whose only imports live in test files."""
    findings: list[hc.Finding] = []
    for dist in sorted(runtime_names & imported_dists):
        matching = [m for m, v in third_party.items() if v["dist"] == dist]
        all_sites: list[tuple[str, int, bool]] = []
        for m in matching:
            all_sites.extend(third_party[m]["sites"])
        if all_sites and all(is_t for _, _, is_t in all_sites):
            mp = declared.get(dist, "pyproject.toml")
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="low",
                    path=mp,
                    line_start=1,
                    line_end=1,
                    symbol=dist,
                    metric_name="runtime_dep_test_only",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw=(
                        "Declared in [project.dependencies] but "
                        "only imported in test files."
                    ),
                    confidence="medium",
                    suggested_action=(
                        f"Move `{dist}` from [project.dependencies] "
                        "to a test/dev extra or "
                        "[project.optional-dependencies]."
                    ),
                )
            )
    return findings


def _find_undeclared_imports(
    third_party: dict[str, dict],
    declared_dists: set[str],
) -> list[hc.Finding]:
    """Flag imports of packages not declared in any manifest."""
    findings: list[hc.Finding] = []
    for module in sorted(third_party):
        info = third_party[module]
        if info["dist"] not in declared_dists:
            rel, lineno, _ = sorted(info["sites"])[0]
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=rel,
                    line_start=lineno,
                    line_end=lineno,
                    symbol=module,
                    metric_name="import_undeclared",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw=(
                        "Imported but not declared in pyproject.toml "
                        "or requirements*.txt."
                    ),
                    confidence=info["confidence"],
                    suggested_action=(
                        f"Declare `{module}` (dist: {info['dist']}) "
                        "as a dependency in pyproject.toml."
                    ),
                )
            )
    return findings


def _build_advisory_vuln(
    norm_name: str,
    pkg_path: str,
    vulns: list[dict],
    severity: str,
    confidence: str,
) -> hc.Finding:
    """Produce a single dependency_vulnerabilities finding."""
    fix_info = ", ".join(
        f"{v['id']} (fix: {', '.join(v.get('fix_versions', []))})"
        for v in vulns
    )
    count = len(vulns)
    plural = "y" if count == 1 else "ies"
    return hc.Finding(
        leaf=LEAF,
        signal="RESTRUCTURE",
        severity=severity,
        path=pkg_path,
        line_start=1,
        line_end=1,
        symbol=norm_name,
        metric_name="dependency_vulnerabilities",
        metric_value=float(count),
        metric_threshold=0.0,
        evidence_tool="advisory-report",
        evidence_raw=fix_info,
        confidence=confidence,
        suggested_action=(
            f"Upgrade `{norm_name}` to fix "
            f"{count} known vulnerabilit{plural}: {fix_info}."
        ),
    )


def _build_advisory_outdated(
    norm_name: str,
    pkg_path: str,
    installed: str,
    latest: str,
) -> hc.Finding:
    """Produce a dependency_outdated finding."""
    return hc.Finding(
        leaf=LEAF,
        signal="RESTRUCTURE",
        severity="info",
        path=pkg_path,
        line_start=1,
        line_end=1,
        symbol=norm_name,
        metric_name="dependency_outdated",
        metric_value=1.0,
        metric_threshold=0.0,
        evidence_tool="advisory-report",
        evidence_raw=f"installed={installed} latest={latest}",
        confidence="medium",
        suggested_action=(
            f"Consider updating `{norm_name}` "
            f"from {installed} to {latest}."
        ),
    )


def _find_advisory_findings(
    advisory_report: str,
    declared: dict[str, str],
    root: Path,
) -> list[hc.Finding]:
    """Produce RESTRUCTURE findings from a C-8 advisory report."""
    findings: list[hc.Finding] = []
    packages = _load_advisory(advisory_report)
    pyproject = root / "pyproject.toml"
    fallback = "pyproject.toml" if pyproject.exists() else "pyproject.toml"

    for pkg in packages:
        name = pkg["name"]
        norm_name = _norm(name)
        pkg_path = declared.get(norm_name, fallback)

        vulns = pkg.get("vulns", [])
        if vulns:
            raw_sevs = {v.get("severity") for v in vulns}
            sev, conf = _map_advisory_severity(raw_sevs)
            findings.append(
                _build_advisory_vuln(norm_name, pkg_path, vulns, sev, conf)
            )

        installed = pkg.get("installed_version")
        latest = pkg.get("latest_version")
        if latest is not None and installed is not None and latest != installed:
            findings.append(
                _build_advisory_outdated(norm_name, pkg_path, installed, latest)
            )

    return findings


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------


def analyze_tree(
    root: str | Path,
    source_prefixes: list[str],
    thresholds: dict,
    advisory_report: str | None = None,
) -> list[hc.Finding]:
    """Run the full dependency audit and return sorted findings."""
    root = Path(root)

    declared, manifest_found = declared_deps(root)
    if not manifest_found:
        return []

    runtime_names = _runtime_dep_names(root)
    imports = collect_imports(root, list(source_prefixes or []))

    # Classify third-party imports
    third_party: dict[str, dict] = {}
    for module, sites in imports.items():
        if module in STDLIB:
            continue
        if _is_local_module(root, module, list(source_prefixes or [])):
            continue
        dist, conf = _dist_candidates(module)
        third_party[module] = {
            "dist": dist,
            "confidence": conf,
            "sites": sites,
        }

    declared_dists: set[str] = set(declared.keys())
    imported_dists: set[str] = {v["dist"] for v in third_party.values()}

    findings: list[hc.Finding] = []
    findings.extend(
        _find_unused_declared(declared_dists, imported_dists, declared)
    )
    findings.extend(
        _find_runtime_test_only(
            runtime_names,
            imported_dists,
            third_party,
            declared,
        )
    )
    findings.extend(_find_undeclared_imports(third_party, declared_dists))

    if advisory_report:
        findings.extend(
            _find_advisory_findings(advisory_report, declared, root)
        )

    return hc.sort_findings(findings)
