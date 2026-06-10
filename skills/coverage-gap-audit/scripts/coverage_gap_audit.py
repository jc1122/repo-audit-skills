#!/usr/bin/env python3
"""coverage-gap-audit leaf: coverage.py JSON report(s) -> TEST findings for
untested / under-tested files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "coverage-gap"

DEFAULT_THRESHOLDS = {
    "min_file_coverage": 50.0,
}


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


def load_coverage(paths: list[str], root: Path) -> dict[str, dict]:
    """Merge coverage.py JSON reports keyed by root-relative posix path."""
    merged: dict[str, dict] = {}
    for raw in paths:
        try:
            report = json.loads(Path(raw).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"unreadable coverage report {raw}: {exc}") from exc
        files = report.get("files")
        if not isinstance(files, dict):
            raise ToolError(f"{raw} is not a coverage.py JSON report (no 'files' map)")
        for name, data in files.items():
            key = _rel(name, root)
            entry = merged.setdefault(key, {"executed": set(), "statements": 0})
            entry["executed"] |= set(data.get("executed_lines", []))
            summary = data.get("summary", {})
            entry["statements"] = max(
                entry["statements"], int(summary.get("num_statements", 0))
            )
    return merged


def _coverage_percent(entry: dict | None) -> float:
    if entry is None:
        return 0.0
    if entry["statements"] == 0:
        return 100.0
    return round(100.0 * len(entry["executed"]) / entry["statements"], 2)


def analyze_tree(root, source_prefixes, thresholds, coverage_jsons) -> list[hc.Finding]:
    root = Path(root)
    merged = load_coverage(list(coverage_jsons), root)
    minimum = float(thresholds["min_file_coverage"])
    findings: list[hc.Finding] = []
    for path in _iter_python_files(root, list(source_prefixes or [])):
        rel = path.relative_to(root).as_posix()
        pct = _coverage_percent(merged.get(rel))
        if pct > minimum:
            continue
        untested = pct == 0.0
        entry = merged.get(rel)
        if entry is None:
            evidence = "absent from all coverage reports"
        else:
            evidence = (
                f"{len(entry['executed'])}/{entry['statements']} statements executed"
            )
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="TEST",
                severity="high" if untested else "medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol="<file>",
                metric_name="file_coverage_percent",
                metric_value=pct,
                metric_threshold=minimum,
                evidence_tool="coverage",
                evidence_raw=evidence,
                confidence="high" if untested else "medium",
                suggested_action=f"Add behavior tests covering {rel} "
                f"(coverage {pct}% < {minimum}%)",
            )
        )
    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# coverage-gap-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## TEST ({len(findings)})")
    for f in findings:
        lines.append(
            f"- `{f.path}` {f.metric_value}% covered — {f.evidence_raw} [{f.severity}]"
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
        description="Deterministic testedness audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument(
        "--coverage-json",
        action="append",
        default=[],
        dest="coverage_jsons",
        help="coverage.py JSON report. Repeatable; reports are merged.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--config", help="JSON file overriding thresholds (min_file_coverage)."
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir or not args.coverage_jsons:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "--root, --out-dir and --coverage-json are required",
                }
            )
        )
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(
            args.root, args.source_prefixes, thresholds, args.coverage_jsons
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "coverage-gap_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
