"""Churn-complexity hotspot analysis for hotspot-audit.

Deterministic ordering
----------------------
Files are processed in sorted order by relative path.  Two runs with the
same git history, thresholds, and file tree on disk produce bit-identical
findings lists.

Evidence construction
---------------------
Each finding captures the raw churn and NLOC counts in ``evidence_raw``
so downstream consumers can inspect why the product crossed the threshold
without rerunning git.
"""

from __future__ import annotations

from pathlib import Path

from _audit_shared import LEAF, _EvidenceCtx, hc
from _audit_collect import _nloc


def _churn_hotspots(
    existing: dict[str, Path],
    churn: dict[str, int],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> list[hc.Finding]:
    """Return DECOMPOSE findings for files with high churn-complexity product.

    The product is ``churn * nloc``.  Severity thresholds:
    * >=4x -> high
    * >=2x -> medium
    * >=1x -> low
    """
    min_churn = int(thresholds["min_churn_commits"])
    min_product = float(thresholds["min_churn_complexity_product"])

    findings: list[hc.Finding] = []
    for rel_path in sorted(existing):
        c = churn[rel_path]
        if c < min_churn:
            continue
        p = existing[rel_path]
        nloc = _nloc(p)
        product = float(c * nloc)
        if product < min_product:
            continue

        severity = (
            "high"
            if product >= 4 * min_product
            else "medium"
            if product >= 2 * min_product
            else "low"
        )

        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DECOMPOSE",
                severity=severity,
                path=rel_path,
                line_start=1,
                line_end=1,
                symbol=rel_path,
                metric_name="churn_complexity_product",
                metric_value=product,
                metric_threshold=min_product,
                evidence_tool="git",
                evidence_raw=(
                    f"{c} commits x {nloc} nloc in last {ev.num_commits_read} commits "
                    f"(max {ev.max_commits}) from {ev.short_sha}"
                ),
                confidence="medium",
                suggested_action=(
                    f"Hotspot: {rel_path} changes often and is large; "
                    "split along change axes"
                ),
            )
        )
    return findings
