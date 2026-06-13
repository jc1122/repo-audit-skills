"""Static algorithmic-smell audit: wrap perflint (via pylint) → PERF findings.

Deterministic, advisory, never mutates source. High-precision subset only —
wrong-container, loop-invariant, and related performance anti-patterns.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "perf-smell"
# perflint reserves the 8xxx message range; we keep ONLY those ids. (`pylint --enable` takes
# message ids, not a plugin name, and pylint always emits its own fatals/syntax errors, which
# start with F/E and are therefore dropped by this prefix filter.)
_PERFLINT_PREFIXES = ("W81", "W82", "W83", "W84", "R81", "R82")


class ToolError(RuntimeError):
    """Underlying tool missing or produced unusable output (→ EXIT_ERROR, never silent-clean).

    Mirrors the convention in dead_code_audit.py / quality_audit.py: a missing tool is a
    hard error, not zero findings.
    """


def _python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files: list[Path] = []
    for prefix in source_prefixes or [""]:
        base = root / prefix
        if base.is_dir():
            files.extend(sorted(base.rglob("*.py")))
        elif base.suffix == ".py" and base.is_file():
            files.append(base)
    return files


def _run_perflint(files: list[Path], root: Path) -> list[dict]:
    if not files:
        return []
    # Missing tool is a hard error, never silent-clean (matches dead_code_audit / quality_audit).
    # find_spec also catches a missing perflint plugin, which `--load-plugins` would otherwise
    # surface only as a JSON fatal we'd filter out (a false "clean").
    for tool in ("pylint", "perflint"):
        if importlib.util.find_spec(tool) is None:
            raise ToolError(f"{tool} is not installed")
    cmd = [
        sys.executable, "-m", "pylint",
        "--load-plugins=perflint",
        "--output-format=json",
        "--score=n",
        "--persistent=no",
        *[str(f) for f in files],
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    except FileNotFoundError as exc:  # pylint entrypoint absent
        raise ToolError("pylint is not installed") from exc
    try:
        return json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(
            f"pylint produced unparseable output: {(proc.stderr or '').strip()[:300]}"
        ) from exc


def _rel(path_str: str, root: Path) -> str:
    p = Path(path_str)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def analyze_tree(root: str | Path, source_prefixes: list[str]) -> list[hc.Finding]:
    root = Path(root)
    files = _python_files(root, source_prefixes)
    findings: list[hc.Finding] = []
    for msg in _run_perflint(files, root):
        code = msg.get("message-id", "") or ""
        if not code.startswith(_PERFLINT_PREFIXES):
            continue  # keep only perflint's own messages; drop pylint core + syntax/import errors
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="PERF",
                severity="low",
                path=_rel(msg.get("path", ""), root),
                line_start=int(msg.get("line", 0) or 0),
                line_end=int(msg.get("line", 0) or 0),
                symbol=msg.get("symbol", "") or code,
                metric_name=code,
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="perflint",
                evidence_raw=msg.get("message", "")[:400],
                confidence="medium",
                suggested_action=msg.get("message", "")[:200],
            )
        )
    return hc.sort_findings(findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Static algorithmic-smell audit (perflint).")
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes")
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        findings = analyze_tree(args.root, args.source_prefixes)
    except ToolError as exc:  # missing/broken tool → EXIT_ERROR, matching sibling leaves
        print(f"perf-smell-audit tool error: {exc}", file=sys.stderr)
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
