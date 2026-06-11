"""Temporal-coupling analysis for hotspot-audit.

Deterministic ordering
----------------------
File pairs are processed in lexicographic order on the pair tuple
``(min_path, max_path)`` so two runs with the same input produce an
identical findings list.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from _audit_shared import LEAF, _EvidenceCtx, hc


def _is_own_test_pair(a: str, b: str) -> bool:
    """Return True when a source file is paired with its own test file."""
    a_name = PurePosixPath(a).name
    b_name = PurePosixPath(b).name

    def source_stem_for_test(filename: str) -> str | None:
        if not filename.startswith("test_") or not filename.endswith(".py"):
            return None
        return filename.removeprefix("test_").removesuffix(".py")

    a_test_stem = source_stem_for_test(a_name)
    b_test_stem = source_stem_for_test(b_name)
    return (a_test_stem is not None and b_name == f"{a_test_stem}.py") or (
        b_test_stem is not None and a_name == f"{b_test_stem}.py"
    )


def _temporal_coupling(
    pair_co: dict[tuple[str, str], int],
    churn: dict[str, int],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> tuple[list[hc.Finding], int]:
    """Return RESTRUCTURE findings for co-changing file pairs.

    The coupling ratio is ``co_changes / min(churn[a], churn[b])``.
    Pairs with fewer than *min_coupling_changes* co-changes or a ratio
    below *min_coupling_ratio* are filtered out.
    """
    min_co = int(thresholds["min_coupling_changes"])
    min_ratio = float(thresholds["min_coupling_ratio"])

    findings: list[hc.Finding] = []
    suppressed_own_test_pairs = 0
    for a, b in sorted(pair_co):
        co = pair_co[(a, b)]
        if co < min_co:
            continue
        ratio = co / min(churn[a], churn[b])
        if ratio < min_ratio:
            continue
        if _is_own_test_pair(a, b):
            suppressed_own_test_pairs += 1
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
    return findings, suppressed_own_test_pairs
