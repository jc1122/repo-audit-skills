#!/usr/bin/env python3
"""Dependency-audit leaf: declared-vs-imported dependency analysis (advisory)."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import sys as _sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "dependency"

DEFAULT_THRESHOLDS = {}

MODULE_TO_DIST = {
    "PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml", "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4", "dateutil": "python-dateutil", "dotenv": "python-dotenv",
    "jwt": "pyjwt", "OpenSSL": "pyopenssl", "Crypto": "pycryptodome", "git": "gitpython",
    "fitz": "pymupdf", "attr": "attrs", "pkg_resources": "setuptools", "serial": "pyserial",
    "usb": "pyusb", "websocket": "websocket-client", "zmq": "pyzmq", "magic": "python-magic",
    "docx": "python-docx", "pptx": "python-pptx",
}
STDLIB = frozenset(_sys.stdlib_module_names)


class ToolError(RuntimeError):
    pass


def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


def _dist_candidates(module: str) -> tuple[str, str]:
    """(candidate dist name, confidence): exact table hit -> high, else normalized guess -> medium."""
    if module in MODULE_TO_DIST:
        return MODULE_TO_DIST[module], "high"
    return _norm(module), "medium"


def _spec_name(spec: str) -> str:
    return _norm(re.split(r"[\s\[<>=!~;]", spec.strip(), maxsplit=1)[0])


def collect_imports(root: Path, prefixes: list[str]) -> dict[str, list[tuple[str, int, bool]]]:
    """top-level module -> [(relpath, lineno, is_test_scope)]"""
    out: dict[str, list[tuple[str, int, bool]]] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if prefixes and not any(rel.startswith(p) for p in prefixes):
            continue
        is_test = "tests" in Path(rel).parts or Path(rel).name.startswith("test_")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module.split(".")[0]]
            for m in mods:
                out.setdefault(m, []).append((rel, node.lineno, is_test))
    return out


def declared_deps(root: Path) -> tuple[dict[str, str], bool]:
    """normalized dist -> manifest relpath; bool = any manifest found."""
    declared: dict[str, str] = {}
    found = False
    py = root / "pyproject.toml"
    if py.exists():
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ToolError(f"invalid pyproject.toml: {exc}") from exc
        project = data.get("project")
        if isinstance(project, dict):
            found = True
            specs = list(project.get("dependencies", []))
            for extra in (project.get("optional-dependencies") or {}).values():
                specs.extend(extra)
            for spec in specs:
                declared.setdefault(_spec_name(spec), "pyproject.toml")
    for req in sorted(root.glob("requirements*.txt")):
        found = True
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                declared.setdefault(_spec_name(line), req.name)
    return declared, found


def _is_local_module(root: Path, module: str, source_prefixes: list[str]) -> bool:
    """A top-level import name is LOCAL when root/<name>.py or root/<name>/__init__.py
    exists, or <name> is a directory directly under any --source-prefix."""
    if (root / f"{module}.py").exists() or (root / module / "__init__.py").exists():
        return True
    for p in source_prefixes:
        if (root / p / module).is_dir():
            return True
    return False


def _runtime_dep_names(root: Path) -> set[str]:
    """Set of normalized dist names from [project.dependencies] only (not optional/requirements)."""
    py = root / "pyproject.toml"
    if not py.exists():
        return set()
    try:
        data = tomllib.loads(py.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return set()
    project = data.get("project")
    if not isinstance(project, dict):
        return set()
    return {_spec_name(s) for s in project.get("dependencies", [])}


def _load_advisory(path_str: str) -> list[dict]:
    """Load and validate C-8 advisory report JSON. Raises ToolError on failure."""
    try:
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"unreadable or malformed --advisory-report: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("packages"), list):
        raise ToolError("--advisory-report is not in C-8 shape (missing 'packages' list)")
    packages = data["packages"]
    for pkg in packages:
        if not isinstance(pkg, dict) or "name" not in pkg:
            raise ToolError("--advisory-report package entry missing 'name'")
    return packages


def analyze_tree(
    root: str | Path,
    source_prefixes: list[str],
    thresholds: dict,
    advisory_report: str | None = None,
) -> list[hc.Finding]:
    root = Path(root)
    findings: list[hc.Finding] = []

    declared, manifest_found = declared_deps(root)
    if not manifest_found:
        return []

    runtime_names = _runtime_dep_names(root)
    imports = collect_imports(root, list(source_prefixes or []))

    # Classify third-party imports: module -> {dist, confidence, sites}
    third_party: dict[str, dict] = {}
    for module, sites in imports.items():
        if module in STDLIB:
            continue
        if _is_local_module(root, module, list(source_prefixes or [])):
            continue
        dist, conf = _dist_candidates(module)
        third_party[module] = {"dist": dist, "confidence": conf, "sites": sites}

    declared_dists = set(declared.keys())
    imported_dists = {v["dist"] for v in third_party.values()}

    # 1. Unused declared (DELETE)
    for dist in sorted(declared_dists):
        if dist not in imported_dists:
            manifest_path = declared[dist]
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="DELETE",
                    severity="low",
                    path=manifest_path,
                    line_start=1,
                    line_end=1,
                    symbol=dist,
                    metric_name="declared_unused",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw="Dynamic imports/plugins/extension modules are invisible to AST analysis.",
                    confidence="medium",
                    suggested_action=(
                        f"Remove unused declared dependency `{dist}` "
                        f"from {manifest_path} or add code that imports it."
                    ),
                )
            )

    # 2. Runtime dep only used in tests (RESTRUCTURE)
    for dist in sorted(runtime_names & imported_dists):
        matching_modules = [m for m, v in third_party.items() if v["dist"] == dist]
        all_sites = []
        for m in matching_modules:
            all_sites.extend(third_party[m]["sites"])
        if all_sites and all(is_test for _, _, is_test in all_sites):
            manifest_path = declared.get(dist, "pyproject.toml")
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="low",
                    path=manifest_path,
                    line_start=1,
                    line_end=1,
                    symbol=dist,
                    metric_name="runtime_dep_test_only",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw="Declared in [project.dependencies] but only imported in test files.",
                    confidence="medium",
                    suggested_action=(
                        f"Move `{dist}` from [project.dependencies] to a "
                        f"test/dev extra or [project.optional-dependencies]."
                    ),
                )
            )

    # 3. Undeclared imported (RESTRUCTURE)
    for module in sorted(third_party):
        info = third_party[module]
        if info["dist"] not in declared_dists:
            first_site = sorted(info["sites"])[0]
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=first_site[0],
                    line_start=first_site[1],
                    line_end=first_site[1],
                    symbol=module,
                    metric_name="import_undeclared",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="ast",
                    evidence_raw="Imported but not declared in pyproject.toml or requirements*.txt.",
                    confidence=info["confidence"],
                    suggested_action=(
                        f"Declare `{module}` (dist: {info['dist']}) "
                        f"as a dependency in pyproject.toml."
                    ),
                )
            )

    # 4. Advisory findings (RESTRUCTURE)
    if advisory_report:
        packages = _load_advisory(advisory_report)
        pyproject = root / "pyproject.toml"
        manifest_fallback = "pyproject.toml" if pyproject.exists() else None

        for pkg in packages:
            name = pkg["name"]
            norm_name = _norm(name)
            pkg_path = declared.get(norm_name) or manifest_fallback or "pyproject.toml"

            # Vulnerability findings
            vulns = pkg.get("vulns", [])
            if vulns:
                vuln_sevs = {v.get("severity") for v in vulns}
                sev_order = {"info": 0, "low": 1, "medium": 2, "high": 3}
                mapped_sevs = []
                for s in vuln_sevs:
                    if s in ("critical", "high"):
                        mapped_sevs.append("high")
                    elif s in ("medium",):
                        mapped_sevs.append("medium")
                    elif s in ("low",):
                        mapped_sevs.append("low")
                    else:
                        mapped_sevs.append("medium")  # null -> medium
                max_sev = max(mapped_sevs, key=lambda s: sev_order.get(s, 0))
                has_null = None in vuln_sevs
                confidence = "medium" if has_null else "high"

                fix_info = ", ".join(
                    f"{v['id']} (fix: {', '.join(v.get('fix_versions', []))})"
                    for v in vulns
                )

                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="RESTRUCTURE",
                        severity=max_sev,
                        path=pkg_path,
                        line_start=1,
                        line_end=1,
                        symbol=norm_name,
                        metric_name="dependency_vulnerabilities",
                        metric_value=float(len(vulns)),
                        metric_threshold=0.0,
                        evidence_tool="advisory-report",
                        evidence_raw=fix_info,
                        confidence=confidence,
                        suggested_action=(
                            f"Upgrade `{norm_name}` to fix "
                            f"{len(vulns)} known vulnerabilit"
                            f"{'y' if len(vulns) == 1 else 'ies'}: {fix_info}."
                        ),
                    )
                )

            # Outdated findings
            installed = pkg.get("installed_version")
            latest = pkg.get("latest_version")
            if latest is not None and installed is not None and latest != installed:
                findings.append(
                    hc.Finding(
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
                            f"Consider updating `{norm_name}` from {installed} to {latest}."
                        ),
                    )
                )

    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# dependency-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(
                f"- `{f.path}:{f.line_start}` {f.symbol} — "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Declared-vs-imported dependency audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix", action="append", default=[], dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument(
        "--advisory-report",
        help="C-8 advisory JSON report path (optional).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(
            args.root, args.source_prefixes, thresholds, args.advisory_report
        )
        _, manifest_found = declared_deps(Path(args.root))
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    status = {"status": "ok", "findings": len(data), "leaf": LEAF}
    if not manifest_found:
        status["manifest"] = False
    print(json.dumps(status))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
