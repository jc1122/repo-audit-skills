#!/usr/bin/env python3
"""Docs-consistency audit.

Checks documentation commands, paths, and versions against reality.
"""

from __future__ import annotations

import argparse
import ast as _ast
import importlib.util as _importlib_util
import json
import re as _re
import shlex as _shlex
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

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
_PLACEHOLDER = _re.compile(r"[<>{}*$]")
_OUTPUT_PATH_ROOTS = (".self_audit_out/", "/".join(("", "tmp", "")))
_LAST_ANALYSIS_META = {
    "skipped_placeholder_tokens": 0,
    "skipped_output_path_tokens": 0,
}


class ToolError(RuntimeError):
    pass


# -- helpers ----------------------------------------------------------------


def _in_scope(rel: str, prefixes: list[str], excludes=()) -> bool:
    """Return True if *rel* is in scope per the prefix filter."""
    included = not prefixes or any(rel.startswith(p) for p in prefixes)
    excluded = any(rel.startswith(p) for p in excludes)
    return included and not excluded


def _rel(root: Path, path: Path) -> str:
    """Return root-relative POSIX path."""
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_text(path: Path) -> str | None:
    """Return file text (UTF-8, errors replaced), or None when unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _in_scope_files(
    root_path: Path, pattern: str, prefixes: list[str], excludes=()
) -> list[Path]:
    """Return sorted in-scope files matching *pattern* (byte-determinism)."""
    return sorted(
        f
        for f in root_path.rglob(pattern)
        if _in_scope(_rel(root_path, f), prefixes, excludes)
    )


# -- Group 1: unknown flags in fenced commands ------------------------------


def _extract_fenced_blocks(
    text: str,
) -> list[tuple[int, list[str]]]:
    """Return [(fence_start_line, [lines])] for bash/sh/shell/console fences."""
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


def _has_argparse_import(tree: _ast.Module) -> bool:
    """Return True when the module AST imports argparse in any form."""
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import) and any(
            alias.name == "argparse" for alias in node.names
        ):
            return True
        if isinstance(node, _ast.ImportFrom) and node.module == "argparse":
            return True
    return False


def _has_top_level_build_parser(tree: _ast.Module) -> bool:
    """Return True when the module AST has a top-level ``def build_parser``."""
    return any(
        isinstance(node, _ast.FunctionDef) and node.name == "build_parser"
        for node in _ast.iter_child_nodes(tree)
    )


def _load_script_module(script_path: Path, module_name: str) -> ModuleType | None:
    """Import *script_path* as *module_name*, returning None on failure."""
    spec = _importlib_util.spec_from_file_location(module_name, script_path)
    if spec is None:
        return None
    mod = _importlib_util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        return None  # import failed -- skip silently
    return mod


def _parser_flags(parser: argparse.ArgumentParser, rel: str) -> set[str]:
    """Return every option string exposed by *parser*.

    Pinned private argparse API: ``parser._actions``.  argparse has no
    public action enumeration; pin the attribute here.
    """
    if not hasattr(parser, "_actions"):
        raise ToolError(f"argparse parser has no _actions attribute for {rel}")
    flags: set[str] = set()
    for action in parser._actions:
        flags.update(action.option_strings)
    return flags


def _known_flags(script_path: Path, root_path: Path) -> set[str] | None:
    """Return known long-flag set for a script, or None to skip.

    Uses an AST guard: only imports the module when its AST contains
    ``import argparse`` (or ``from argparse import ...``) AND a
    top-level ``def build_parser``.  Modules failing this guard are
    skipped silently (never imported).
    """
    source = _read_text(script_path)
    if source is None:
        return None
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return None
    if not (_has_argparse_import(tree) and _has_top_level_build_parser(tree)):
        return None  # guard failed -- never imported
    rel = _rel(root_path, script_path)
    mod = _load_script_module(script_path, rel.replace("/", ".").removesuffix(".py"))
    if mod is None:
        return None
    try:
        parser = mod.build_parser()
    except Exception:
        return None
    return _parser_flags(parser, rel)


class _FlagCache:
    """Per-run cache of script flag introspection (one import per script)."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self._flags: dict[str, set[str] | None] = {}

    def flags_for(self, script_path: Path) -> set[str] | None:
        """Return known flags for *script_path*, introspecting at most once."""
        key = str(script_path)
        if key not in self._flags:
            self._flags[key] = _known_flags(script_path, self.root_path)
        return self._flags[key]


def _line_tokens(line: str) -> list[str]:
    """Shell-tokenize one fenced-block line, stripping a leading ``$ `` prompt."""
    stripped = line.strip()
    if stripped.startswith("$ "):
        stripped = stripped[2:]
    try:
        return _shlex.split(stripped)
    except ValueError:
        return []


def _script_for_tokens(tokens: list[str], root_path: Path) -> tuple[str, Path] | None:
    """Return (token, path) for the first token naming an existing in-root .py file."""
    root_resolved = root_path.resolve()
    for tok in tokens[1:]:
        if tok.endswith(".py"):
            candidate = root_path / tok
            if candidate.is_file():
                try:
                    candidate.resolve().relative_to(root_resolved)
                except ValueError:
                    continue  # token resolves outside --root; skip (env-dependent)
                return tok, candidate
    return None


def _unknown_flag_finding(
    md_relpath: str, fence_start: int, script_token: str, flag: str
) -> hc.Finding:
    """Build the finding for one unknown ``--flag`` occurrence."""
    return hc.Finding(
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


def _check_fenced_flags(
    md_relpath: str,
    fence_start: int,
    fence_lines: list[str],
    cache: _FlagCache,
    findings: list[hc.Finding],
) -> None:
    """Check each line in a fenced block for unknown flags."""
    for line in fence_lines:
        tokens = _line_tokens(line)
        if not tokens or tokens[0] not in ("python", "python3"):
            continue
        script = _script_for_tokens(tokens, cache.root_path)
        if script is None:
            continue
        script_token, script_path = script
        known = cache.flags_for(script_path)
        if known is None:
            continue  # guard rejected -- skip silently
        for tok in tokens[1:]:
            if not tok.startswith("--"):
                continue
            flag = tok.split("=", 1)[0]
            if flag not in known:
                findings.append(
                    _unknown_flag_finding(md_relpath, fence_start, script_token, flag)
                )


def _check_markdown_fences(
    md_relpath: str, text: str, cache: _FlagCache, findings: list[hc.Finding]
) -> None:
    """Run the unknown-flag check over every fenced block in *text*."""
    for fence_start, fence_lines in _extract_fenced_blocks(text):
        if fence_lines:
            _check_fenced_flags(md_relpath, fence_start, fence_lines, cache, findings)


# -- Group 2: dead doc paths ------------------------------------------------


def _check_dead_paths(
    md_relpath: str,
    text: str,
    root_path: Path,
    findings: list[hc.Finding],
) -> tuple[int, int]:
    """Emit findings for inline code spans referencing non-existent files."""
    skipped_placeholder_tokens = 0
    skipped_output_path_tokens = 0
    for i, line in enumerate(text.split("\n"), start=1):
        for match in _INLINE_CODE_RE.finditer(line):
            span = match.group(1)
            if _PLACEHOLDER.search(span):
                skipped_placeholder_tokens += 1
                continue
            if not _DEAD_PATH_RE.match(span):
                continue
            if "://" in span:
                continue
            if "/" not in span:
                continue
            suffix = Path(span).suffix
            if suffix not in _DEAD_PATH_SUFFIXES:
                continue
            if span.startswith(_OUTPUT_PATH_ROOTS):
                skipped_output_path_tokens += 1
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
    return skipped_placeholder_tokens, skipped_output_path_tokens


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
        text = _read_text(md_file)
        if text is None:
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
                                f"found {name}=={found}, current version is {version}"
                            ),
                            confidence="high",
                            suggested_action=(
                                f"Update version pin in {rel} from {found} to {version}"
                            ),
                        )
                    )


# -- Group 4: docstring coverage (config-gated) -----------------------------


def _has_docstring(
    node: _ast.FunctionDef | _ast.ClassDef | _ast.AsyncFunctionDef,
) -> bool:
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


def _iter_public_methods(
    cls: _ast.ClassDef,
) -> Iterator[_ast.FunctionDef | _ast.AsyncFunctionDef]:
    """Yield public function members of *cls*."""
    for member in _ast.iter_child_nodes(cls):
        if isinstance(
            member, (_ast.FunctionDef, _ast.AsyncFunctionDef)
        ) and not member.name.startswith("_"):
            yield member


def _iter_public_symbols(
    tree: _ast.Module,
) -> Iterator[_ast.FunctionDef | _ast.AsyncFunctionDef | _ast.ClassDef]:
    """Yield public top-level defs/classes and public methods of public classes."""
    for node in _ast.iter_child_nodes(tree):
        if isinstance(
            node, (_ast.FunctionDef, _ast.AsyncFunctionDef)
        ) and not node.name.startswith("_"):
            yield node
        elif isinstance(node, _ast.ClassDef) and not node.name.startswith("_"):
            yield node
            yield from _iter_public_methods(node)


def _docstring_stats(tree: _ast.Module) -> tuple[int, int]:
    """Return (public_total, documented) docstring counts for *tree*."""
    public_total = 0
    documented = 0
    for node in _iter_public_symbols(tree):
        public_total += 1
        if _has_docstring(node):
            documented += 1
    return public_total, documented


def _docstring_finding(
    rel: str, pct: float, documented: int, public_total: int, threshold: float
) -> hc.Finding:
    """Build the docstring_percent finding for one module."""
    return hc.Finding(
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
            f"{documented}/{public_total} public symbols documented ({pct}%)"
        ),
        confidence="medium",
        suggested_action=(
            f"Add docstrings to undocumented functions in {rel} to reach {threshold}%"
        ),
    )


def _check_docstring_coverage(
    root_path: Path,
    py_files: list[Path],
    threshold: float,
    findings: list[hc.Finding],
) -> None:
    """Emit docstring_percent findings for modules below *threshold*."""
    for py_file in py_files:
        rel = _rel(root_path, py_file)
        source = _read_text(py_file)
        if source is None:
            continue
        try:
            tree = _ast.parse(source)
        except SyntaxError:
            continue
        public_total, documented = _docstring_stats(tree)
        if public_total == 0:
            continue
        pct = round(100 * documented / public_total, 1)
        if pct < threshold:
            findings.append(
                _docstring_finding(rel, pct, documented, public_total, threshold)
            )


# -- main analysis ----------------------------------------------------------


def analyze_tree(
    root: str,
    source_prefixes: list[str],
    thresholds: dict,
    exclude_prefixes: list[str] | None = None,
) -> list[hc.Finding]:
    """Run all four audit groups and return sorted findings."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ToolError(f"--root is not a directory: {root}")

    excludes = exclude_prefixes or []
    findings: list[hc.Finding] = []
    skipped_placeholder_tokens = 0
    skipped_output_path_tokens = 0
    md_files = _in_scope_files(root_path, "*.md", source_prefixes, excludes)
    py_files = _in_scope_files(root_path, "*.py", source_prefixes, excludes)

    # Group 1: unknown flags in fenced commands
    cache = _FlagCache(root_path)
    for md_file in md_files:
        text = _read_text(md_file)
        if text is not None:
            _check_markdown_fences(_rel(root_path, md_file), text, cache, findings)

    # Group 2: dead doc paths
    for md_file in md_files:
        text = _read_text(md_file)
        if text is not None:
            skipped_placeholders, skipped_outputs = _check_dead_paths(
                _rel(root_path, md_file), text, root_path, findings
            )
            skipped_placeholder_tokens += skipped_placeholders
            skipped_output_path_tokens += skipped_outputs

    # Group 3: stale version pins
    pkg_name, pkg_version = _get_package_version(root_path)
    if pkg_name is not None and pkg_version is not None:
        _check_version_pins(pkg_name, pkg_version, root_path, md_files, findings)

    # Group 4: docstring coverage (opt-in)
    docstring_min = thresholds.get("docstring_min_percent")
    if docstring_min is not None:
        _check_docstring_coverage(root_path, py_files, float(docstring_min), findings)

    _LAST_ANALYSIS_META["skipped_placeholder_tokens"] = skipped_placeholder_tokens
    _LAST_ANALYSIS_META["skipped_output_path_tokens"] = skipped_output_path_tokens
    return findings


# -- CLI --------------------------------------------------------------------


def _group_by_signal(findings: list[hc.Finding]) -> dict[str, list[hc.Finding]]:
    """Group findings by signal, preserving insertion order within groups."""
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    return by_signal


def _signal_section(signal: str, group: list[hc.Finding]) -> list[str]:
    """Render one ``## SIGNAL (n)`` report section."""
    lines = [f"## {signal} ({len(group)})"]
    for f in group:
        lines.append(
            f"- `{f.path}:{f.line_start}` {f.symbol} -- "
            f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
        )
    lines.append("")
    return lines


def render_report(
    findings: list[hc.Finding],
    skipped_placeholder_tokens: int = 0,
    skipped_output_path_tokens: int = 0,
) -> str:
    """Render the advisory markdown report grouped by signal."""
    header = [
        "# docs-consistency-audit report",
        "",
        f"Skipped placeholder tokens: {skipped_placeholder_tokens}",
        f"Skipped output-path tokens: {skipped_output_path_tokens}",
        "",
    ]
    if not findings:
        return "\n".join([*header, "No findings."]) + "\n"
    sections: list[str] = header
    for signal, group in sorted(_group_by_signal(findings).items()):
        sections.extend(_signal_section(signal, group))
    return "\n".join(sections) + "\n"


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
    parser.add_argument(
        "--exclude-prefix",
        action="append",
        default=[],
        dest="exclude_prefixes",
        help=(
            "Path prefix(es) relative to --root to exclude after inclusion. Repeatable."
        ),
    )
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def load_thresholds(config_path: str | None) -> dict:
    """Return DEFAULT_THRESHOLDS overlaid with the optional JSON config."""
    merged = dict(DEFAULT_THRESHOLDS)
    if not config_path:
        return merged
    try:
        raw = Path(config_path).read_text(encoding="utf-8")
        merged.update(json.loads(raw))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"invalid --config: {exc}") from exc
    return merged


def _run_audit(args: argparse.Namespace) -> int:
    """Execute the audit for parsed *args*; emit the summary JSON on stdout."""
    try:
        findings = analyze_tree(
            args.root,
            args.source_prefixes,
            load_thresholds(args.config),
            args.exclude_prefixes,
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    report_path = Path(args.out_dir, f"{LEAF}_report.md")
    skipped_placeholder_tokens = _LAST_ANALYSIS_META["skipped_placeholder_tokens"]
    skipped_output_path_tokens = _LAST_ANALYSIS_META["skipped_output_path_tokens"]
    report_path.write_text(
        render_report(findings, skipped_placeholder_tokens, skipped_output_path_tokens),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "findings": len(data),
                "leaf": LEAF,
                "skipped_placeholder_tokens": skipped_placeholder_tokens,
                "skipped_output_path_tokens": skipped_output_path_tokens,
            }
        )
    )
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: validate required args, then run the audit."""
    args = build_parser().parse_args(argv)
    if args.root and args.out_dir:
        return _run_audit(args)
    error = {"status": "error", "message": "--root and --out-dir are required"}
    print(json.dumps(error))
    return hc.EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
