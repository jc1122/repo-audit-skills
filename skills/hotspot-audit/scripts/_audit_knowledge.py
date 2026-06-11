"""Knowledge-concentration analysis for hotspot-audit.

Evidence construction
---------------------
Each finding records the top author name and their commit count relative
to total churn in ``evidence_raw``.  The share is computed as
``top_author_commits / total_commits`` so 1.0 means one person touched
every commit.
"""

from __future__ import annotations

from pathlib import Path

from _audit_shared import LEAF, _EvidenceCtx, hc


def _distinct_authors(authors: dict[str, dict[str, int]]) -> set[str]:
    """Return the distinct author names present in collected file history."""
    return {author for per_file in authors.values() for author in per_file}


def _knowledge_or_suppression(
    existing: dict[str, Path],
    churn: dict[str, int],
    authors: dict[str, dict[str, int]],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> tuple[list[hc.Finding], bool]:
    """Return knowledge findings, or flag a solo-author repository suppression."""
    if len(_distinct_authors(authors)) <= 1:
        return [], True
    return _knowledge_concentration(existing, churn, authors, thresholds, ev), False


def _knowledge_concentration(
    existing: dict[str, Path],
    churn: dict[str, int],
    authors: dict[str, dict[str, int]],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> list[hc.Finding]:
    """Return RESTRUCTURE findings for files dominated by a single author.

    Files are processed in sorted path order for deterministic output.
    A file is reported when its top author's share exceeds
    *min_author_share* and the file has at least *min_author_commits*
    total commits.
    """
    min_author_commits = int(thresholds["min_author_commits"])
    min_author_share = float(thresholds["min_author_share"])

    findings: list[hc.Finding] = []
    for rel_path in sorted(existing):
        c = churn[rel_path]
        if c < min_author_commits:
            continue
        author_counts = authors[rel_path]
        top_author = max(author_counts, key=author_counts.get)
        top_count = author_counts[top_author]
        share = top_count / c
        if share <= min_author_share:
            continue

        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="RESTRUCTURE",
                severity="low",
                path=rel_path,
                line_start=1,
                line_end=1,
                symbol=rel_path,
                metric_name="author_concentration",
                metric_value=round(share, 2),
                metric_threshold=min_author_share,
                evidence_tool="git",
                evidence_raw=(
                    f"top author {top_author}/{c} commits "
                    f"(max {ev.max_commits}) from {ev.short_sha}"
                ),
                confidence="low",
                suggested_action=(
                    "Knowledge concentrated in one author; "
                    "schedule reviews/pairing on this file"
                ),
            )
        )
    return findings
