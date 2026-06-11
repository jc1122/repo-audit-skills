"""Temporal-coupling analysis for hotspot-audit.

Deterministic ordering
----------------------
File pairs are processed in lexicographic order on the pair tuple
``(min_path, max_path)`` so two runs with the same input produce an
identical findings list.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from _audit_coupling_finding import coupling_finding
from _audit_shared import _EvidenceCtx, hc


def _source_name_for_test(path: str) -> str | None:
    name = PurePosixPath(path).name
    if not name.startswith("test_") or not name.endswith(".py"):
        return None
    return f"{name.removeprefix('test_').removesuffix('.py')}.py"


def _is_own_test_pair(a: str, b: str) -> bool:
    """Return True when a source file is paired with its own test file."""
    return _source_name_for_test(a) == PurePosixPath(b).name or (
        _source_name_for_test(b) == PurePosixPath(a).name
    )


def _valid_glob_pair(pair: object) -> bool:
    return (
        isinstance(pair, (list, tuple))
        and len(pair) == 2
        and all(isinstance(item, str) for item in pair)
    )


def _is_declared_coupling(a: str, b: str, declared_pairs: object) -> bool:
    if not isinstance(declared_pairs, list):
        return False
    return any(
        _valid_glob_pair(pair)
        and (
            (fnmatchcase(a, pair[0]) and fnmatchcase(b, pair[1]))
            or (fnmatchcase(a, pair[1]) and fnmatchcase(b, pair[0]))
        )
        for pair in declared_pairs
    )


def _temporal_coupling(
    pair_co: dict[tuple[str, str], int],
    churn: dict[str, int],
    thresholds: dict,
    ev: _EvidenceCtx,
) -> tuple[list[hc.Finding], int, int]:
    """Return RESTRUCTURE findings for co-changing file pairs.

    The coupling ratio is ``co_changes / min(churn[a], churn[b])``.
    Pairs with fewer than *min_coupling_changes* co-changes or a ratio
    below *min_coupling_ratio* are filtered out.
    """
    min_co = int(thresholds["min_coupling_changes"])
    min_ratio = float(thresholds["min_coupling_ratio"])

    findings: list[hc.Finding] = []
    suppressed_own_test_pairs = 0
    suppressed_declared_coupling = 0
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
        if _is_declared_coupling(
            a,
            b,
            thresholds.get("coupling_allow_pairs", []),
        ):
            suppressed_declared_coupling += 1
            continue

        findings.append(coupling_finding((a, b), co, ratio, min_ratio, ev))
    return findings, suppressed_own_test_pairs, suppressed_declared_coupling
