"""CLI entry point for test-effectiveness-audit.

Parses command-line arguments, validates mandatory scope flags,
and delegates to the analysis pipeline.  The thin public module
(test_effectiveness_audit.py) re-exports from here for test
compatibility and acts as the installable script entry point.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402
from _emission import LEAF  # noqa: E402
from _pipeline import ToolError, analyze_tree  # noqa: E402
from _report import load_thresholds, render_report  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Required flags (missing any → exit 2 with JSON rationale):
      --root       — target repository root
      --out-dir    — output directory for findings + report
      --paths      — file listing root-relative paths to mutate
      --tests-dir  — root-relative test directory for sandbox
      --max-mutants — upper bound on estimated mutants (budget gate)

    Optional flags:
      --source-prefix — path prefix filter (repeatable)
      --config        — JSON file overriding DEFAULT_THRESHOLDS
      --format        — json | md (output format, default json)
    """
    parser = argparse.ArgumentParser(
        description="Deterministic mutation-testing effectiveness audit (advisory).",
    )
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
    parser.add_argument(
        "--paths",
        help="File of newline-separated root-relative .py files/dirs to mutate.",
    )
    parser.add_argument(
        "--tests-dir",
        dest="tests_dir",
        help="Root-relative test directory to copy into sandbox.",
    )
    parser.add_argument(
        "--max-mutants",
        type=int,
        dest="max_mutants",
        help="Maximum estimated mutants before refusing to run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point: validate scope, run mutation testing, emit findings.

    Returns:
      0 — no findings (clean suite)
      1 — findings present (at least one module below kill-rate threshold)
      2 — error (missing flags, budget exceeded, tool not found, timeout)
    """
    args = build_parser().parse_args(argv)

    # --- mandatory scope argument validation ---
    # Unscoped mutation testing is prohibitively expensive (hours).
    # All three scope flags are required to prevent accidental full-repo runs.
    missing = []
    if not args.root:
        missing.append("--root")
    if not args.out_dir:
        missing.append("--out-dir")
    if not args.paths:
        missing.append("--paths")
    if not args.tests_dir:
        missing.append("--tests-dir")
    if args.max_mutants is None:
        missing.append("--max-mutants")

    if missing:
        msg = (
            "Mutation testing requires scoped paths: --paths, --tests-dir, "
            "and --max-mutants are mandatory "
            f"(missing: {', '.join(missing)}). "
            "Unscoped mutation testing costs hours; feed it e.g. the top-N "
            "hotspot paths."
        )
        print(json.dumps({"status": "error", "message": msg}))
        return hc.EXIT_ERROR

    # --- threshold loading ---
    try:
        thresholds = load_thresholds(args.config)
        config = {
            "root": Path(args.root).resolve(),
            "source_prefixes": args.source_prefixes,
            "thresholds": thresholds,
            "paths_file": Path(args.paths),
            "tests_dir": args.tests_dir,
            "max_mutants": args.max_mutants,
            "out_dir": Path(args.out_dir).resolve(),
        }
        findings, actual_total = analyze_tree(config)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR

    # --- output ---
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings),
        encoding="utf-8",
    )

    status: dict = {"status": "ok", "findings": len(data), "leaf": LEAF}
    if actual_total > args.max_mutants:
        status["budget_exceeded"] = True
    print(json.dumps(status))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN
