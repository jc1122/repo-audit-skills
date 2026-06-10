"""Per-file churn, author, and existence collection for hotspot-audit.

Audit boundaries
----------------
- Only files that exist *on disk at analysis time* are included in the
  ``existing`` mapping.  Deleted files leave traces in git history but
  never produce findings.
- The ``source_prefixes`` list controls which on-disk files enter the
  scope.  An empty list means all files are in scope.
- NLOC (non-blank non-comment lines) is computed with a simple
  ``splitlines()`` heuristic.  It is fast enough for thousands of files
  and agrees with lizard's approximate count for the churn-complexity
  product.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def _nloc(path: Path) -> int:
    """Return the number of non-blank physical lines in *path*.

    Returns 0 when the file cannot be read (OSError).
    """
    try:
        return sum(
            1
            for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        )
    except OSError:
        return 0


def _in_scope(rel: str, prefixes: list[str]) -> bool:
    """Check whether *rel* starts with any of *prefixes*.

    Empty *prefixes* means everything is in scope (match-all).
    """
    return not prefixes or any(rel.startswith(p) for p in prefixes)


def _collect_file_stats(
    commits: list[dict],
    source_prefixes: list[str],
    root: Path,
) -> tuple[dict[str, int], dict[str, dict[str, int]], dict[str, Path]]:
    """Derive per-file churn, per-file author counts, and extant file paths.

    Returns three mappings suitable for downstream analysis:
    ``(churn, authors, existing)``.

    *churn* maps relative-path -> total-commit-count.
    *authors* maps relative-path -> {author-name -> commit-count}.
    *existing* maps relative-path -> absolute-Path (only for in-scope
    files that exist on disk).
    """
    churn: dict[str, int] = defaultdict(int)
    authors: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for c in commits:
        for f in c["files"]:
            churn[f] += 1
            authors[f][c["author"]] += 1

    existing: dict[str, Path] = {}
    for rel_path in churn:
        if not _in_scope(rel_path, source_prefixes):
            continue
        p = root / rel_path
        if p.is_file():
            existing[rel_path] = p
    return dict(churn), dict(authors), existing
