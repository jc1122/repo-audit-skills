#!/usr/bin/env python3
"""Docs-consistency audit -- checks documentation commands, paths, and versions against reality."""

from __future__ import annotations

import argparse
import ast as _ast
import importlib.util as _importlib_util
import json
import re as _re
import shlex as _shlex
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "docs-consistency"

DEFAULT_THRESHOLDS: dict = {"docstring_min_percent": None}

# Regex for inline code spans `` `...` `` that look like file paths.
_DEAD_PATH_RE = _re.compile(r"^[A-Za-z0-9_.\-/]+$")
_DEAD_PATH_SUFFIXES = frozenset(
    {".py", ".md", ".json", ".toml", ".cfg", ".yml", ".yaml", ".sh", ".js", ".txt"}
)
# Inline code span extractor.
_INLINE_CODE_RE = _re.compile(r"`([^`]*)`")


class ToolError(RuntimeError):
    pass


# -- helpers ----------------------------------------------------------------


def _in_scope(rel: str, prefixes: list[str]) -> bool:
    """Return True if *rel* is in scope per the prefix filter."""
    return not prefixes or any(rel.startswith(p) for p in prefixes)


def _rel(root: Path, path: Path) -> str:
    """Return root-relative POSIX path."""
    return path.resolve().relative_to(root.resolve()).as_posix()


# -- Group 1: unknown flags in fenced commands ------------------------------


def _extract_fenced_blocks(
    text: str,
) -> list[tuple[int, list[str]]]:
    """Return [(fence_start_line, [enclosed_lines])] for bash/sh/shell/console fences."""
    blocks: list[tuple[int, list[str]]] = []
    in_fence = False
    fence_start = 0
    fence_lines: list[str] = []

    for i, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if not in_fence:
            m = _re.match(r"^(```|~~~)(bash|sh|shell|console)\s*$", stripped)
            if m:
                in_fence = True
                fence_start = i
                fence_lines = []
        else:
            if _re.match(r"^(```|~~~)\s*$", stripped):
                blocks.append((fence_start, fence_lines))
                in_fence = False
            else:
                fence_lines.append(line)
    return blocks


def _known_flags(script_path: Path, root_path: Path) -> set[str] | None:
    """Return known long-flag set for a script, or None to skip.

    Uses an AST guard: only imports the module when its AST contains
    ``import argparse`` (or ``from argparse import ...``) AND a
    top-level ``def build_parser``.  Modules failing this guard are
    skipped silently (never imported).
    """
    try:
        source = script_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return None

    # Guard: argparse import anywhere in the AST.
    has_argparse = False
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                if alias.name == "argparse":
                    has_argparse = True
        elif isinstance(node, _ast.ImportFrom):
            if node.module == "argparse":
                has_argparse = True

    # Guard: top-level ``def build_parser``.
    has_build_parser = False
    for node in _ast.iter_child_nodes(tree):
        if isinstance(node, _ast.FunctionDef) and node.name == "build_parser":
            has_build_parser = True
            break

    if not has_argparse or not has_build_parser:
        return None  # skip silently -- never imported

    # Import the module without mutating sys.argv.
    rel = _rel(root_path, script_path)
    module_name = rel.replace("/", ".").removesuffix(".py")
    spec = _importlib_util.spec_from_file_location(module_name, script_path)
    if spec is None:
        return None
    mod = _importlib_util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        return None  # import failed -- skip silently

    try:
        parser = mod.build_parser()
    except Exception:
        return None

    # Pinned private argparse API: ``parser._actions``.
    # argparse has no public action enumeration; pin the attribute here.
    if not hasattr(parser, "_actions"):
        raise ToolError(
            f"argparse parser has no _actions attribute for {rel}"
        )

    flags: set[str] = set()
    for action in parser._actions:  # type: ignore[attr-defined]
        for opt in action.option_strings:
            flags.add(opt)
    return flags


def _check_fenced_flags(
    md_relpath: str,
    fence_start: int,
    fence_lines: list[str],
    root_path: Path,
    findings: list[hc.Finding],
    _flag_cache: dict[str, set[str] | None],
) -> None:
    """Check each line in a fenced block for unknown flags."""
    for line in fence_lines:
        stripped = line.strip()
        # Strip leading ``$ `` prompt.
        if stripped.startswith("$ "):
            stripped = stripped[2:]
        try:
            tokens = _shlex.split(stripped)
        except ValueError:
            continue

        if not tokens or tokens[0] not in ("python", "python3"):
            continue

        # Find the .py script token that exists under root.
        script_token = ""
        script_path: Path | None = None
        for tok in tokens[1:]:
            if tok.endswith(".py"):
                candidate = root_path / tok
                if candidate.is_file():
                    script_token = tok
                    script_path = candidate
                    break

        if not script_token or script_path is None:
            continue

        # Introspect the script (cached per absolute path).
        cache_key = str(script_path)
        if cache_key not in _flag_cache:
            _flag_cache[cache_key] = _known_flags(script_path, root_path)
        known = _flag_cache[cache_key]

        if known is None:
            continue  # guard rejected -- skip silently

        # Check each ``--`` flag in the line.
        for tok in tokens[1:]:
            if tok.startswith("--"):
                flag = tok.split("=", 1)[0]
                if flag not in known:
                    findings.append(
                        hc.Finding(
                            leaf=LEAF,
                            signal="LINT",
                            severity="medium",
                            path=md_relpath,
                            line_start=fence_start,
                            line_end=fence_start,
                            symbol=script_token,
                            metric_name="doc_flag_unknown",
                            metric_value=1.0,
                            metric_threshold=0.0,
                            evidence_tool="argparse",
                            evidence_raw=f"flag {flag} unknown for {script_token}",
                            confidence="medium",
                            suggested_action=(
                                f"Remove or fix unknown flag {flag} "
                                f"in {md_relpath} references to {script_token}"
                            ),
                        )
                    )


# -- Group 2: dead doc paths ------------------------------------------------


def _check_dead_paths(
    md_relpath: str,
    text: str,
    root_path: Path,
    findings: list[hc.Finding],
) -> None:
    """Emit findings for inline code spans referencing non-existent files."""
    for i, line in enumerate(text.split("\n"), start=1):
        for match in _INLINE_CODE_RE.finditer(line):
            span = match.group(1)
            if not _DEAD_PATH_RE.match(span):
                continue
            if "://" in span:
                continue
            if "/" not in span:
                continue
            suffix = Path(span).suffix
            if suffix not in _DEAD_PATH_SUFFIXES:
                continue
            if not (root_path / span).exists():
                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="LINT",
                        severity="low",
                        path=md_relpath,
                        line_start=i,
                        line_end=i,
                        symbol=span,
                        metric_name="doc_path_missing",
                        metric_value=1.0,
                        metric_threshold=0.0,
                        evidence_tool="markdown",
                        evidence_raw=span,
                        confidence="medium",
                        suggested_action=(
                            f"Create {span} or update {md_relpath} reference"
                        ),
                    )
                )


# -- Group 3: stale version pins --------------------------------------------


def _get_package_version(root_path: Path) -> tuple[str | None, str | None]:
    """Return (name, version) from pyproject.toml [project] or package.json."""
    pyproject = root_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ToolError(f"invalid pyproject.toml: {exc}") from exc
        project = data.get("project")
        if isinstance(project, dict):
            name = project.get("name")
            version = project.get("version")
            if name and version:
                return str(name), str(version)

    pkg_json = root_path / "package.json"
    if pkg_json.is_file():
        data = json.loads(pkg_json.read_text(encoding="utf-8"))
        name = data.get("name")
        version = data.get("version")
        if name and version:
            return str(name), str(version)

    return None, None


def _check_version_pins(
    name: str,
    version: str,
    root_path: Path,
    md_files: list[Path],
    findings: list[hc.Finding],
) -> None:
    """Scan markdown for stale version pins like ``name==X.Y.Z``."""
    version_re = _re.compile(rf"{_re.escape(name)}==(\d+\.\d+\.\d+)")

    for md_file in md_files:
        rel = _rel(root_path, md_file)
        if md_file.name.startswith("CHANGELOG"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.split("\n"), start=1):
            for match in version_re.finditer(line):
                found = match.group(1)
                if found != version:
                    findings.append(
                        hc.Finding(
                            leaf=LEAF,
                            signal="LINT",
                            severity="medium",
                            path=rel,
                            line_start=i,
                            line_end=i,
                            symbol=name,
                            metric_name="doc_version_stale",
                            metric_value=1.0,
                            metric_threshold=0.0,
                            evidence_tool="semver",
                            evidence_raw=(
                                f"found {name}=={found}, "
                                f"current version is {version}"
                            ),
                            confidence="high",
                            suggested_action=(
                                f"Update version pin in {rel} "
                                f"from {found} to {version}"
                            ),
                        )
                    )


# -- Group 4: docstring coverage (config-gated) -----------------------------


def _has_docstring(node: _ast.FunctionDef | _ast.ClassDef | _ast.AsyncFunctionDef) -> bool:
    """Return True when *node* starts with a docstring expression."""
    if node.body:
        first = node.body[0]
        if (
            isinstance(first, _ast.Expr)
            and isinstance(first.value, _ast.Constant)
            and isinstance(first.value.value, str)
        ):
            return True
    return False


def _check_docstring_coverage(
    root_path: Path,
    py_files: list[Path],
    threshold: float,
    findings: list[hc.Finding],
) -> None:
    """Emit docstring_percent findings for modules below *threshold*."""
    for py_file in py_files:
        rel = _rel(root_path, py_file)
        try:
            tree = _ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue

        public_total = 0
        documented = 0

        for node in _ast.iter_child_nodes(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    public_total += 1
                    if _has_docstring(node):
                        documented += 1
            elif isinstance(node, _ast.ClassDef):
                if not node.name.startswith("_"):
                    public_total += 1
                    if _has_docstring(node):
                        documented += 1
                    # Also count public methods of public classes.
                    for member in _ast.iter_child_nodes(node):
                        if isinstance(member, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                            if not member.name.startswith("_"):
                                public_total += 1
                                if _has_docstring(member):
                                    documented += 1

        if public_total == 0:
            continue

        pct = round(100 * documented / public_total, 1)

        if pct < threshold:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="LINT",
                    severity="low",
                    path=rel,
                    line_start=1,
                    line_end=1,
                    symbol="<module>",
                    metric_name="docstring_percent",
                    metric_value=pct,
                    metric_threshold=threshold,
                    evidence_tool="ast",
                    evidence_raw=(
                        f"{documented}/{public_total} "
                        f"public symbols documented ({pct}%)"
                    ),
                    confidence="medium",
                    suggested_action=(
                        f"Add docstrings to undocumented functions "
                        f"in {rel} to reach {threshold}%"
                    ),
                )
            )


# -- main analysis ----------------------------------------------------------


def analyze_tree(
    root: str,
    source_prefixes: list[str],
    thresholds: dict,
) -> list[hc.Finding]:
    """Run all four audit groups and return sorted findings."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ToolError(f"--root is not a directory: {root}")

    findings: list[hc.Finding] = []

    # Collect in-scope files (sorted for byte-determinism).
    md_files = sorted(
        f for f in root_path.rglob("*.md")
        if _in_scope(_rel(root_path, f), source_prefixes)
    )
    py_files = sorted(
        f for f in root_path.rglob("*.py")
        if _in_scope(_rel(root_path, f), source_prefixes)
    )

    # Group 1: unknown flags in fenced commands
    flag_cache: dict[str, set[str] | None] = {}
    for md_file in md_files:
        rel = _rel(root_path, md_file)
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for fence_start, fence_lines in _extract_fenced_blocks(text):
            if not fence_lines:
                continue
            _check_fenced_flags(rel, fence_start, fence_lines, root_path, findings, flag_cache)

    # Group 2: dead doc paths
    for md_file in md_files:
        rel = _rel(root_path, md_file)
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        _check_dead_paths(rel, text, root_path, findings)

    # Group 3: stale version pins
    pkg_name, pkg_version = _get_package_version(root_path)
    if pkg_name is not None and pkg_version is not None:
        _check_version_pins(pkg_name, pkg_version, root_path, md_files, findings)

    # Group 4: docstring coverage (opt-in)
    docstring_min = thresholds.get("docstring_min_percent")
    if docstring_min is not None:
        _check_docstring_coverage(root_path, py_files, float(docstring_min), findings)

    return findings


# -- CLI --------------------------------------------------------------------


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# docs-consistency-audit report", ""]
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
                f"- `{f.path}:{f.line_start}` {f.symbol} -- "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Docs-consistency audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
