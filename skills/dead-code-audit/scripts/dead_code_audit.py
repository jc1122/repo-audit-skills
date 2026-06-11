#!/usr/bin/env python3
"""dead-code-audit leaf: vulture (defs) + ruff F401/F811/F841 → DELETE findings."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "dead-code"
TOOL_TIMEOUT = 120

DEFAULT_THRESHOLDS = {
    "min_confidence": 60,
}

OWNED_RUFF_CODES = ("F401", "F811", "F841")
VULTURE_KEEP = {"function", "class", "method", "property"}
_LAST_SUPPRESSED_TEST_REFERENCED = 0
_VULTURE_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+): unused (?P<kind>[\w ]+?) "
    r"'(?P<name>[^']+)' \((?P<conf>\d+)% confidence\)$"
)


class ToolError(RuntimeError):
    pass


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [
        p
        for p in files
        if any(
            p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes
        )
    ]


def _severity_for_conf(conf: int) -> str:
    if conf >= 90:
        return "high"
    if conf >= 70:
        return "medium"
    return "low"


def _confidence_for_conf(conf: int) -> str:
    if conf >= 90:
        return "high"
    if conf >= 70:
        return "medium"
    return "low"


def _vulture_findings(
    root: Path, files: list[Path], thresholds: dict, allowlist: str | None
) -> list[hc.Finding]:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = ["vulture", "--min-confidence", str(thresholds["min_confidence"]), *rel_files]
    if allowlist:
        cmd.append(allowlist)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=TOOL_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise ToolError("vulture is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"vulture timed out after {TOOL_TIMEOUT}s") from exc
    findings: list[hc.Finding] = []
    for line in proc.stdout.splitlines():
        m = _VULTURE_RE.match(line.strip())
        if not m:
            continue
        kind = m.group("kind").strip()
        if kind not in VULTURE_KEEP:
            continue  # imports/variables are owned by ruff
        conf = int(m.group("conf"))
        ln = int(m.group("line"))
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity=_severity_for_conf(conf),
                path=_rel(m.group("path"), root),
                line_start=ln,
                line_end=ln,
                symbol=m.group("name"),
                metric_name="dead_code_confidence",
                metric_value=float(conf),
                metric_threshold=float(thresholds["min_confidence"]),
                evidence_tool="vulture",
                evidence_raw=line.strip(),
                confidence=_confidence_for_conf(conf),
                suggested_action=f"Remove unused {kind} '{m.group('name')}' "
                f"if truly dead",
            )
        )
    return findings


def _test_referenced(
    symbols: set[str], root: Path, source_prefixes: list[str]
) -> set[str]:
    dirs = {root / "tests"} | {
        root / PurePosixPath(prefix).parent / "tests" for prefix in source_prefixes
    }
    dirs |= {root / PurePosixPath(prefix) / "tests" for prefix in source_prefixes}
    hits: set[str] = set()
    for directory in sorted(dirs):
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("test_*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            hits |= {symbol for symbol in symbols if symbol in text}
    return hits


def _ruff_findings(root: Path, files: list[Path]) -> list[hc.Finding]:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = [
        "ruff",
        "check",
        "--select",
        ",".join(OWNED_RUFF_CODES),
        "--output-format",
        "json",
        "--no-cache",
        *rel_files,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=TOOL_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"ruff timed out after {TOOL_TIMEOUT}s") from exc
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(
            f"ruff produced unparseable output: {proc.stderr.strip()}"
        ) from exc
    findings: list[hc.Finding] = []
    for item in items:
        code = item.get("code") or ""
        if code not in OWNED_RUFF_CODES:
            continue
        loc = item.get("location") or {}
        row = int(loc.get("row", 1))
        col = int(loc.get("column", 1))
        end_row = int((item.get("end_location") or {}).get("row", row))
        path = _rel(item.get("filename", ""), root)
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity="medium",
                path=path,
                line_start=row,
                line_end=end_row,
                symbol=f"{code}@{row}:{col}",
                metric_name=code,
                metric_value=0.0,
                metric_threshold=0.0,
                evidence_tool="ruff",
                evidence_raw=item.get("message", ""),
                confidence="high",
                suggested_action=item.get("message", f"Remove {code} occurrence"),
            )
        )
    return findings


def analyze_tree(root, source_prefixes, thresholds, allowlist=None) -> list[hc.Finding]:
    global _LAST_SUPPRESSED_TEST_REFERENCED
    _LAST_SUPPRESSED_TEST_REFERENCED = 0
    root = Path(root)
    source_prefixes = list(source_prefixes or [])
    files = _iter_python_files(root, source_prefixes)
    if not files:
        return []
    vulture_findings = _vulture_findings(root, files, thresholds, allowlist)
    referenced = _test_referenced(
        {finding.symbol for finding in vulture_findings}, root, source_prefixes
    )
    if referenced:
        before = len(vulture_findings)
        vulture_findings = [
            finding for finding in vulture_findings if finding.symbol not in referenced
        ]
        _LAST_SUPPRESSED_TEST_REFERENCED = before - len(vulture_findings)
    findings = vulture_findings + _ruff_findings(root, files)
    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding]) -> str:
    lines = [
        "# dead-code-audit report",
        "",
        f"suppressed_test_referenced: {_LAST_SUPPRESSED_TEST_REFERENCED}",
        "",
    ]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## DELETE ({len(findings)})")
    for f in findings:
        lines.append(
            f"- `{f.path}:{f.line_start}` {f.symbol} — {f.evidence_tool} [{f.severity}]"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic dead-code audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--config", help="JSON file overriding thresholds (min_confidence)."
    )
    parser.add_argument(
        "--allowlist", help="Vulture whitelist file to suppress false positives."
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument(
        "--simulate-missing-tool", action="store_true", help=argparse.SUPPRESS
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(
            json.dumps(
                {"status": "error", "message": "--root and --out-dir are required"}
            )
        )
        return hc.EXIT_ERROR
    try:
        if args.simulate_missing_tool:
            raise ToolError("simulated missing tool")
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(
            args.root, args.source_prefixes, thresholds, allowlist=args.allowlist
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "dead-code_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "findings": len(data),
                "leaf": LEAF,
                "suppressed_test_referenced": _LAST_SUPPRESSED_TEST_REFERENCED,
            }
        )
    )
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
