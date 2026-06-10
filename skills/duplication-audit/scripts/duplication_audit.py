#!/usr/bin/env python3
"""duplication-audit leaf: jscpd clone detection → EXTRACT/MERGE findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "duplication"
TOOL_TIMEOUT = 120

DEFAULT_THRESHOLDS = {
    "min_tokens": 50,
    "min_lines": 5,
}


class ToolError(RuntimeError):
    pass


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


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _run_jscpd(root: Path, files: list[Path], thresholds: dict, out_dir: Path) -> dict:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    repo_root = Path(__file__).resolve().parents[3]
    jscpd_bin = repo_root / "node_modules" / ".bin" / "jscpd"
    cmd = [
        str(jscpd_bin),
        "--silent",
        "--reporters",
        "json",
        "--output",
        str(out_dir),
        "--min-tokens",
        str(thresholds["min_tokens"]),
        "--min-lines",
        str(thresholds["min_lines"]),
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
        raise ToolError(
            "local jscpd binary not found at node_modules/.bin/jscpd (run npm install)"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"jscpd timed out after {TOOL_TIMEOUT}s") from exc
    report_path = out_dir / "jscpd-report.json"
    if not report_path.exists():
        raise ToolError(
            f"jscpd produced no report: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return json.loads(report_path.read_text(encoding="utf-8"))


def _findings_from_report(
    report: dict, root: Path, thresholds: dict
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    min_tokens = thresholds["min_tokens"]
    for dup in report.get("duplicates", []):
        ff, sf = dup["firstFile"], dup["secondFile"]
        p1, p2 = _rel(ff["name"], root), _rel(sf["name"], root)
        tokens = int(dup.get("tokens", 0))
        signal = "MERGE" if p1 == p2 else "EXTRACT"
        severity = "high" if tokens > 3 * min_tokens else "medium"
        symbol = f"{p2}:{sf['start']}-{sf['end']}"
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal=signal,
                severity=severity,
                path=p1,
                line_start=int(ff["start"]),
                line_end=int(ff["end"]),
                symbol=symbol,
                metric_name="duplicate_tokens",
                metric_value=float(tokens),
                metric_threshold=float(min_tokens),
                evidence_tool="jscpd",
                evidence_raw=(
                    f"{p1}:{ff['start']}-{ff['end']} == "
                    f"{p2}:{sf['start']}-{sf['end']} ({tokens} tokens)"
                ),
                confidence="high",
                suggested_action=(
                    f"Extract shared code between {p1} and {p2}"
                    if signal == "EXTRACT"
                    else f"Merge duplicated block within {p1}"
                ),
            )
        )
    return findings


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        report = _run_jscpd(root, files, thresholds, Path(tmp))
    return hc.sort_findings(_findings_from_report(report, root, thresholds))


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# duplication-audit report", ""]
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
                f"- `{f.path}:{f.line_start}` ↔ `{f.symbol}` — "
                f"{f.metric_value:g} tokens [{f.severity}]"
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
        description="Deterministic duplication audit (advisory)."
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
        "--config", help="JSON file overriding thresholds (min_tokens, min_lines)."
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
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "duplication_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
