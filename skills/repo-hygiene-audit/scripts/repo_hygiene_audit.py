#!/usr/bin/env python3
"""Repo hygiene audit: tracked-tree hygiene + release hygiene checks.

This is a thin CLI/orchestrator.  Check logic lives in sibling modules:
_git_utils, _thresholds, _tracked_checks, _config_checks, _version_checks,
_release_checks, _reporting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

import _git_utils  # noqa: E402
import _thresholds  # noqa: E402
import _tracked_checks  # noqa: E402
import _config_checks  # noqa: E402
import _version_checks  # noqa: E402
import _release_checks  # noqa: E402
import _reporting  # noqa: E402

LEAF = "repo-hygiene"
ToolError = _git_utils.ToolError  # re-export for tests


def analyze_tree(
    root: Path,
    source_prefixes: list[str],
    thresholds: dict,
) -> tuple[list[hc.Finding], bool]:
    """Run all checks against *root* and return (findings, is_git_repo)."""
    max_bytes = thresholds.get("max_tracked_file_bytes", 1048576)
    prefixes = _git_utils._normalize_prefixes(source_prefixes)
    findings: list[hc.Finding] = []
    git_repo = _git_utils._is_git_repo(root)

    if git_repo:
        try:
            tracked = _git_utils._tracked_paths(root)
            tracked_ignored = _git_utils._tracked_ignored_paths(root)
        except Exception as exc:
            raise _git_utils.ToolError(str(exc)) from exc
        findings.extend(_tracked_checks._check_tracked_artifacts(root, tracked))
        findings.extend(_tracked_checks._check_tracked_ignored(root, tracked_ignored))
        findings.extend(
            _tracked_checks._check_oversized_tracked(root, tracked, max_bytes)
        )
        findings.extend(_tracked_checks._check_broken_symlinks(root, tracked))

    findings.extend(_config_checks._check_conflicting_configs(root))
    findings.extend(_version_checks._check_version_mismatch(root))
    findings.extend(_release_checks._check_missing_ci(root))
    findings.extend(_release_checks._check_missing_license(root))

    if prefixes:
        findings = [f for f in findings if _git_utils._in_scope(f.path, prefixes)]

    return findings, git_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repo hygiene audit (advisory).",
        epilog="Thresholds are configurable via --config.",
    )
    parser.add_argument("--root")
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="JSON file overriding thresholds.",
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
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

    root = Path(args.root).resolve()
    try:
        thresholds = _thresholds.load_thresholds(args.config)
        findings, git_repo = analyze_tree(root, args.source_prefixes, thresholds)
    except _git_utils.ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR

    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        _reporting.render_report(findings), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "findings": len(data),
                "leaf": LEAF,
                "git": git_repo,
            }
        )
    )
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
