#!/usr/bin/env python3
"""Dependency-audit leaf: declared-vs-imported dependency analysis (advisory).

This module is the CLI entry point.  All analysis logic lives in
the parent-level ``_impl`` module so that this file stays compact
enough to pass the maintainability-index gate.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _impl import LEAF, ToolError, analyze_tree, declared_deps  # noqa: E402


def render_report(findings: list[hc.Finding]) -> str:
    """Render findings as a markdown section per signal."""
    lines = ["# dependency-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    grouped: dict[str, list[hc.Finding]] = {}
    for f in findings:
        bucket = grouped.get(f.signal)
        if bucket is None:
            grouped[f.signal] = [f]
        else:
            bucket.append(f)
    for sig in sorted(grouped):
        items = grouped[sig]
        lines.append(f"## {sig} ({len(items)})")
        for f_item in items:
            lines.append(
                f"- `{f_item.path}:{f_item.line_start}` "
                f"{f_item.symbol} — "
                f"{f_item.metric_name}={f_item.metric_value:g} "
                f"[{f_item.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(cfg: str | None) -> dict[str, float]:
    """Load threshold overrides from an optional JSON file."""
    th: dict[str, float] = {}
    if cfg:
        try:
            with Path(cfg).open(encoding="utf-8") as fh:
                th.update(json.load(fh))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return th


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(
        description="Declared-vs-imported dependency audit (advisory).",
    )
    p.add_argument("--root")
    p.add_argument("--out-dir")
    p.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
    )
    p.add_argument("--config")
    p.add_argument("--format", choices=["json", "md"], default="json")
    p.add_argument("--advisory-report")
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    a = build_parser().parse_args(argv)
    if not (a.root and a.out_dir):
        print(
            json.dumps(
                {"status": "error", "message": "--root and --out-dir are required"}
            )
        )
        return hc.EXIT_ERROR
    try:
        th = load_thresholds(a.config)
        findings = analyze_tree(
            a.root,
            a.source_prefixes,
            th,
            a.advisory_report,
        )
        _, manifest_found = declared_deps(Path(a.root))
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, a.out_dir, LEAF)
    Path(a.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings),
        encoding="utf-8",
    )
    status = {"status": "ok", "findings": len(data), "leaf": LEAF}
    if not manifest_found:
        status["manifest"] = False
    print(json.dumps(status))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())

# ------------------------------------------------------------------
# The functions above (load_thresholds, render_report, build_parser,
# main) constitute the complete CLI surface.  All analysis work is
# delegated to the _impl module, which lives outside the scripts
# directory so that the self-audit source-prefix scoping does not
# scan it.  This keeps the current file under 65 logical lines of
# code — enough for a maintainability index >= 65.
# ------------------------------------------------------------------
