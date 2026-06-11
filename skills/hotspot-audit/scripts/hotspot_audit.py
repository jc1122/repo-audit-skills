#!/usr/bin/env python3
"""hotspot-audit leaf: git-history mining for churn hotspots, temporal coupling,
and knowledge concentration findings.  Uses stdlib + git subprocess only.

Analysis pipeline
-----------------
1. Validate the git repository and resolve the target revision.
2. Read commit history via ``git log --numstat``.
3. Collect per-file churn counts and per-file author statistics.
4. Run three independent sub-analyses:
   (a) **Churn hotspots**  -- ``churn * nloc`` beyond threshold -> DECOMPOSE.
   (b) **Temporal coupling** -- co-changing file pairs beyond ratio -> RESTRUCTURE.
   (c) **Knowledge concentration** -- single-author dominance -> RESTRUCTURE.
5. Write findings as JSON + optional Markdown report.

All analysis is deterministic; no network, no external tools beyond git.

Precision suppressions count solo-author knowledge skips, own-test temporal
pair skips, and explicit family-policy suppressions in both stdout and the
Markdown report, so filtered noise remains auditable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audit_shared import (  # noqa: E402
    DECLARED_COUPLING,
    DEFAULT_THRESHOLDS,
    LEAF,
    SINGLE_MAINTAINER,
    ToolError,
    _EvidenceCtx,
    default_suppression_counts,
    hc,
)
from _audit_git import (  # noqa: E402
    _resolve_rev,
    _validate_git_root,
    read_history,
)
from _audit_collect import _collect_file_stats  # noqa: E402
from _audit_churn import _churn_hotspots  # noqa: E402
from _audit_cochange import _count_cochange_pairs  # noqa: E402
from _audit_coupling import _temporal_coupling  # noqa: E402
from _audit_knowledge import _knowledge_or_suppression  # noqa: E402


_LAST_ANALYSIS_META = {
    "suppressed_solo_author": False,
    "suppressed_own_test_pairs": 0,
    "suppression_counts": default_suppression_counts(),
}


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def _reset_analysis_meta() -> None:
    _LAST_ANALYSIS_META.update(
        suppressed_solo_author=False,
        suppressed_own_test_pairs=0,
        suppression_counts=default_suppression_counts(),
    )


def _record_suppression_count(name: str, count: int) -> None:
    _LAST_ANALYSIS_META["suppression_counts"][name] = count


def _collect_coupling_findings(
    commits: list[dict],
    existing: dict[str, Path],
    churn: dict[str, int],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> list[hc.Finding]:
    coupling_findings, own_test_count, declared_count = _temporal_coupling(
        _count_cochange_pairs(
            commits,
            existing,
            int(thresholds["max_commit_files"]),
        ),
        churn,
        thresholds,
        ev,
    )
    _LAST_ANALYSIS_META["suppressed_own_test_pairs"] = own_test_count
    _record_suppression_count(DECLARED_COUPLING, declared_count)
    return coupling_findings


def _collect_knowledge_findings(
    file_stats: tuple[dict[str, Path], dict[str, int], dict[str, dict[str, int]]],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> list[hc.Finding]:
    existing, churn, authors = file_stats
    knowledge_findings, solo_author, single_maintainer_count = (
        _knowledge_or_suppression(existing, churn, authors, thresholds, ev)
    )
    _LAST_ANALYSIS_META["suppressed_solo_author"] = solo_author
    _record_suppression_count(SINGLE_MAINTAINER, single_maintainer_count)
    return knowledge_findings


def analyze_tree(
    root: str | Path,
    source_prefixes: list[str],
    thresholds: dict,
    rev: str,
    max_commits: int,
) -> list[hc.Finding]:
    """Core analysis.  Raises ToolError on input / git errors."""
    _reset_analysis_meta()

    root = Path(root)
    _validate_git_root(root)

    try:
        resolved_sha = _resolve_rev(root, rev)
    except ToolError as exc:
        raise ToolError(f"no commits reachable from --rev {rev}") from exc

    commits = read_history(root, rev, max_commits)
    if not commits:
        raise ToolError(f"no commits reachable from --rev {rev}")

    ev = _EvidenceCtx(len(commits), max_commits, resolved_sha[:12])
    churn, authors, existing = _collect_file_stats(commits, source_prefixes, root)
    findings: list[hc.Finding] = []
    findings.extend(_churn_hotspots(existing, churn, thresholds, ev))
    findings.extend(
        _collect_coupling_findings(commits, existing, churn, thresholds, ev)
    )
    findings.extend(
        _collect_knowledge_findings((existing, churn, authors), thresholds, ev)
    )
    return hc.sort_findings(findings)


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------


def render_report(findings: list[hc.Finding]) -> str:
    """Human-readable markdown report grouped by signal.

    Each finding is listed with its path, symbol, metric name, numeric
    value, and severity level.  Groups are sorted alphabetically by
    signal name; within each group findings appear in sort order.
    """
    suppression_counts = _LAST_ANALYSIS_META["suppression_counts"]
    lines = [
        "# hotspot-audit report",
        "",
        f"Suppressions: `suppressed_solo_author`="
        f"{int(_LAST_ANALYSIS_META['suppressed_solo_author'])}",
        f"`suppressed_own_test_pairs`="
        f"{_LAST_ANALYSIS_META['suppressed_own_test_pairs']}",
        f"`{DECLARED_COUPLING}`={suppression_counts[DECLARED_COUPLING]}",
        f"`{SINGLE_MAINTAINER}`={suppression_counts[SINGLE_MAINTAINER]}",
        "",
    ]
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
                f"- `{f.path}:{f.line_start}` {f.symbol} -- "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_thresholds(config_path: str | None) -> dict:
    """Merge optional JSON config into DEFAULT_THRESHOLDS.

    The config file must be valid JSON.  Keys present in the config
    override the corresponding entries in ``DEFAULT_THRESHOLDS``;
    missing keys keep their default values.  Neither the config file
    nor the defaults are mutated in place.
    """
    base = dict(DEFAULT_THRESHOLDS)
    if config_path is None:
        return base
    cfg_file = Path(config_path)
    try:
        raw = cfg_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"cannot read config file: {exc}") from exc
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid JSON in config: {exc}") from exc
    base.update(overrides)
    return base


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for the hotspot-audit leaf.

    All arguments are optional on the command line but ``--root`` and
    ``--out-dir`` are validated as required by ``main()``.
    """
    p = argparse.ArgumentParser(
        description="Deterministic git-history hotspot audit (advisory).",
    )
    p.add_argument("--root", help="Repository root directory")
    p.add_argument("--out-dir", help="Output directory for findings")
    p.add_argument("--rev", default="HEAD", help="Git revision to analyse from")
    p.add_argument(
        "--max-commits",
        type=int,
        default=500,
        help="Maximum commits of history to examine",
    )
    p.add_argument("--config", help="Optional JSON file overriding thresholds")
    p.add_argument("--format", choices=["json", "md"], default="json")
    p.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include",
    )
    return p


def _emit_error(message: str) -> None:
    """Print error status JSON to stdout."""
    print(json.dumps({"status": "error", "message": message}))


def _emit_status(count: int, rev: str, max_commits: int) -> None:
    """Print success status JSON to stdout."""
    print(
        json.dumps(
            {
                "status": "ok",
                "findings": count,
                "leaf": LEAF,
                "rev": rev,
                "max_commits": max_commits,
                **_LAST_ANALYSIS_META,
            }
        )
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns exit code."""
    ns = build_parser().parse_args(argv)

    if not ns.root or not ns.out_dir:
        _emit_error("--root and --out-dir are required")
        return hc.EXIT_ERROR

    try:
        cfg = load_thresholds(ns.config)
        result = analyze_tree(
            ns.root,
            ns.source_prefixes,
            cfg,
            ns.rev,
            ns.max_commits,
        )
    except ToolError as exc:
        _emit_error(str(exc))
        return hc.EXIT_ERROR

    findings_json = hc.write_findings(result, ns.out_dir, LEAF)
    Path(ns.out_dir, f"{LEAF}_report.md").write_text(
        render_report(result),
        encoding="utf-8",
    )

    try:
        head_sha = _resolve_rev(ns.root, ns.rev)
    except ToolError:
        head_sha = "unknown"

    _emit_status(len(findings_json), head_sha, ns.max_commits)
    return hc.EXIT_FINDINGS if findings_json else hc.EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
