"""Finding construction for hotspot-audit temporal coupling."""

from __future__ import annotations

from _audit_shared import LEAF, _EvidenceCtx, hc


def coupling_finding(
    pair: tuple[str, str],
    co_changes: int,
    ratio: float,
    min_ratio: float,
    ev: _EvidenceCtx,
) -> hc.Finding:
    """Build the shared-schema finding for one temporal-coupling pair."""
    a, b = pair
    return hc.Finding(
        leaf=LEAF,
        signal="RESTRUCTURE",
        severity="medium",
        path=a,
        line_start=1,
        line_end=1,
        symbol=f"{a}<->{b}",
        metric_name="temporal_coupling_ratio",
        metric_value=round(ratio, 2),
        metric_threshold=min_ratio,
        evidence_tool="git",
        evidence_raw=(
            f"{co_changes} co-changes of {a} and {b} "
            f"in last {ev.num_commits_read} commits "
            f"(max {ev.max_commits}) from {ev.short_sha}"
        ),
        confidence="medium",
        suggested_action=(
            "Files co-change; move the shared concern into one module or merge them"
        ),
    )
