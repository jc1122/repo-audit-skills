"""Tracked-tree hygiene checks for repo-hygiene-audit.

These checks operate on the set of paths returned by ``git ls-files``
and emit findings for build artifacts, ignored-but-tracked files,
oversized files, and broken symlinks.
"""

from __future__ import annotations

import os
from pathlib import Path

import health_common as hc  # noqa: E402

LEAF = "repo-hygiene"

# Directory names that should never be committed.
_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})

# File-name heuristics for build artifacts (suffix, exact name, prefix).
_ARTIFACT_SUFFIXES = frozenset({".pyc", ".pyo", ".orig", ".rej"})
_ARTIFACT_NAMES = frozenset({".coverage", ".DS_Store"})
_ARTIFACT_PREFIXES = frozenset({".coverage."})


# ---------------------------------------------------------------------------
# Tracked artifact check
# ---------------------------------------------------------------------------


def _check_tracked_artifacts(root: Path, tracked: set[str]) -> list[hc.Finding]:
    """Emit DELETE findings for build artifacts that are tracked by git.

    Artifacts are identified by cache-directory membership or by
    matching well-known file-name patterns (``.pyc``, ``.coverage``,
    ``.DS_Store``, etc.).
    """
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        reason = _artifact_reason(rel)
        if reason is None:
            continue
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity="medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol=rel,
                metric_name="tracked_artifact",
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="git",
                evidence_raw=f"Tracked build artifact: {reason}",
                confidence="high",
                suggested_action=(
                    "Remove from git tracking and add to .gitignore if appropriate"
                ),
            )
        )
    return findings


def _artifact_reason(rel: str) -> str | None:
    """Return a human-readable reason if *rel* is a build artifact."""
    parts = tuple(Path(rel).parts)
    name = parts[-1] if parts else ""

    # Cache-directory membership (e.g. pkg/__pycache__/x.pyc)
    for p in parts:
        if p in _CACHE_DIRS:
            return f"path contains {p}"

    # Well-known artifact name patterns
    if _name_matches_artifact(name):
        return f"filename matches artifact pattern: {name}"

    return None


def _name_matches_artifact(name: str) -> bool:
    """Check if *name* matches well-known build-artifact patterns."""
    return (
        name in _ARTIFACT_NAMES
        or any(name.endswith(s) for s in _ARTIFACT_SUFFIXES)
        or any(name.startswith(p) for p in _ARTIFACT_PREFIXES)
    )


# ---------------------------------------------------------------------------
# Tracked-but-ignored check
# ---------------------------------------------------------------------------


def _check_tracked_ignored(root: Path, tracked_ignored: set[str]) -> list[hc.Finding]:
    """Emit DELETE findings for files tracked despite matching ``.gitignore``.

    These files were force-added (``git add -f``) after an ignore rule
    was already in place.
    """
    findings: list[hc.Finding] = []
    for rel in sorted(tracked_ignored):
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity="medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol=rel,
                metric_name="tracked_ignored",
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="git",
                evidence_raw=("Tracked by git but excluded by .gitignore patterns"),
                confidence="high",
                suggested_action=f"Remove from git tracking: git rm --cached {rel}",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Oversized tracked file check
# ---------------------------------------------------------------------------


def _check_oversized_tracked(
    root: Path, tracked: set[str], max_bytes: int
) -> list[hc.Finding]:
    """Emit RESTRUCTURE findings for tracked files exceeding *max_bytes*.

    Large files (binaries, datasets, etc.) should normally live outside
    the repository or use Git LFS.
    """
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        fpath = root / rel
        try:
            st_size = fpath.stat().st_size
        except OSError:
            continue
        if st_size <= max_bytes:
            continue
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="RESTRUCTURE",
                severity="medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol=rel,
                metric_name="tracked_file_bytes",
                metric_value=float(st_size),
                metric_threshold=float(max_bytes),
                evidence_tool="git",
                evidence_raw=(
                    f"File size {st_size} bytes exceeds threshold {max_bytes} bytes"
                ),
                confidence="high",
                suggested_action=(
                    "Move large file out of the repository or use Git LFS"
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Broken symlink check
# ---------------------------------------------------------------------------


def _check_broken_symlinks(root: Path, tracked: set[str]) -> list[hc.Finding]:
    """Emit DELETE findings for tracked symlinks whose targets are missing.

    A broken symlink in version control usually means a file was deleted
    without removing the symlink that pointed to it.
    """
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        fpath = root / rel
        try:
            if not (fpath.is_symlink() and not fpath.exists()):
                continue
        except OSError:
            continue
        target = os.readlink(str(fpath))
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity="low",
                path=rel,
                line_start=1,
                line_end=1,
                symbol=rel,
                metric_name="broken_symlink",
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="git",
                evidence_raw=f"Broken symlink: {rel} -> {target}",
                confidence="high",
                suggested_action=("Remove the broken symlink or fix its target"),
            )
        )
    return findings
