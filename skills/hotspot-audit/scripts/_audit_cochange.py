"""Co-change pair counting for hotspot-audit temporal coupling.

Deterministic ordering
----------------------
Pair keys are always stored as ``(min(a,b), max(a,b))`` so every pair
has a single canonical representation regardless of which file appears
first in commit ordering.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def _count_cochange_pairs(
    commits: list[dict],
    existing: dict[str, Path],
    max_files: int,
) -> dict[tuple[str, str], int]:
    """Count how many commits change each pair of in-scope files together.

    Commits touching more than *max_files* files are skipped (huge
    mechanical refactors / merge commits are considered noise).
    """
    pair_co: dict[tuple[str, str], int] = defaultdict(int)
    for c in commits:
        in_scope = [f for f in c["files"] if f in existing]
        nf = len(in_scope)
        if not (1 < nf <= max_files):
            continue
        for i in range(nf):
            for j in range(i + 1, nf):
                a, b = in_scope[i], in_scope[j]
                key = (a, b) if a < b else (b, a)
                pair_co[key] += 1
    return dict(pair_co)
