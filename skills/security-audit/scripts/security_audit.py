#!/usr/bin/env python3
"""security-audit leaf: pinned bandit wrapper -> SECURITY findings.

Thin CLI orchestrator. Analysis logic lives in sibling modules: ``_bandit``
(bandit invocation + mapping), ``_advisory`` (pip-audit ingestion),
``_reporting`` (markdown report + thresholds).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

import _advisory  # noqa: E402
import _bandit  # noqa: E402
import _reporting  # noqa: E402

LEAF = "security"
ToolError = _bandit.ToolError  # re-export for tests/back-compat


def analyze_tree(
    root: str,
    source_prefixes: list[str],
    thresholds: dict,
    advisory_report: str | None = None,
) -> list[hc.Finding]:
    """Bandit findings for *root*, plus advisory findings when requested."""
    findings = _bandit.scan(root, source_prefixes)
    if advisory_report:
        findings = findings + _advisory.scan(advisory_report, root)
    return hc.sort_findings(findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pinned bandit security audit (advisory).",
        epilog="Requires bandit==1.9.4 on the interpreter running this script.",
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument("--root", metavar="DIR")
    parser.add_argument("--out-dir", metavar="DIR")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--config", metavar="PATH", help="JSON threshold overrides.")
    parser.add_argument(
        "--advisory-report",
        metavar="PATH",
        help="pip-audit-shaped JSON adding dependency-vulnerability findings.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    required = {"--root": args.root, "--out-dir": args.out_dir}
    absent = [flag for flag, value in required.items() if not value]
    if absent:
        message = "missing required argument(s): " + ", ".join(absent)
        print(json.dumps({"status": "error", "message": message}))
        return hc.EXIT_ERROR
    try:
        thresholds = _reporting.load_thresholds(args.config)
        findings = analyze_tree(
            args.root, args.source_prefixes, thresholds, args.advisory_report
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    written = hc.write_findings(findings, args.out_dir, LEAF)
    report_path = Path(args.out_dir) / f"{LEAF}_report.md"
    report_path.write_text(_reporting.render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(written), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if written else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
