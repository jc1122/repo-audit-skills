"""Temporal-coupling analysis for hotspot-audit.

Deterministic ordering
----------------------
File pairs are processed in lexicographic order on the pair tuple
``(min_path, max_path)`` so two runs with the same input produce an
identical findings list.
"""

from __future__ import annotations

from _audit_shared import LEAF, _EvidenceCtx, hc


def _temporal_coupling(
    pair_co: dict[tuple[str, str], int],
    churn: dict[str, int],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> list[hc.Finding]:
    """Return RESTRUCTURE findings for co-changing file pairs.

    The coupling ratio is ``co_changes / min(churn[a], churn[b])``.
    Pairs with fewer than *min_coupling_changes* co-changes or a ratio
    below *min_coupling_ratio* are filtered out.
    """
    min_co = int(thresholds["min_coupling_changes"])
    min_ratio = float(thresholds["min_coupling_ratio"])

    findings: list[hc.Finding] = []
    for a, b in sorted(pair_co):
        co = pair_co[(a, b)]
        if co < min_co:
            continue
        ratio = co / min(churn[a], churn[b])
        if ratio < min_ratio:
            continue

        findings.append(
            hc.Finding(
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
                    f"{co} co-changes of {a} and {b} "
                    f"in last {ev.num_commits_read} commits "
                    f"(max {ev.max_commits}) from {ev.short_sha}"
                ),
                confidence="medium",
                suggested_action=(
                    "Files co-change; move the shared concern into one module "
                    "or merge them"
                ),
            )
        )
    return findings
