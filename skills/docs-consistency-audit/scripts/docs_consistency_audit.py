#!/usr/bin/env python3
"""Docs-consistency audit — checks documentation commands, paths, and versions against reality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "docs-consistency"

DEFAULT_THRESHOLDS: dict = {"docstring_min_percent": None}


class ToolError(RuntimeError):
    pass


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


def render_report(findings: list) -> str:
    lines = ["# docs-consistency-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list] = {}
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


def analyze_tree(
    root: str,
    source_prefixes: list[str],
    thresholds: dict,
) -> list:
    """Placeholder — Wave 2 implements the full analysis logic."""
    return []


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
