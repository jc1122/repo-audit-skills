"""Git interaction helpers for repo-hygiene-audit.

This module wraps ``git`` subprocess calls used by the hygiene checks:
``ls-files`` for tracked path enumeration, ``rev-parse`` for repo
detection, and basic prefix-scoping utilities.

Every function that calls ``subprocess.run`` swallows
``FileNotFoundError`` and re-raises it as ``ToolError`` so callers
can handle a missing ``git`` binary uniformly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class ToolError(RuntimeError):
    """Fatal configuration or environment error that blocks analysis.

    Raised when ``git`` is not installed (``FileNotFoundError``) or
    when a git subprocess exits non-zero.  Caught by the CLI
    orchestrator and converted to a JSON error status with exit code 2.
    """


# ---------------------------------------------------------------------------
# Core git wrappers
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    """Run ``git -C <root> <args>`` and return stdout on success.

    Raises:
        ToolError: If ``git`` is not installed or exits non-zero.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("git is not installed") from exc
    if proc.returncode != 0:
        raise ToolError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


def _is_git_repo(root: Path) -> bool:
    """Return ``True`` if *root* is inside a git working tree.

    Uses ``git rev-parse --git-dir`` so it works from subdirectories.
    A missing ``git`` binary raises ``ToolError``, not ``False``.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        raise ToolError("git is not installed") from None
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Tracked file enumeration
# ---------------------------------------------------------------------------


def _tracked_paths(root: Path) -> set[str]:
    """Return the set of ``git ls-files`` paths relative to *root*.

    Uses null-byte (``-z``) output for safety with paths containing
    spaces or newlines.
    """
    out = _git(root, "ls-files", "-z")
    return {p for p in out.split("\0") if p}


def _tracked_ignored_paths(root: Path) -> set[str]:
    """Return tracked files that are also excluded by ``.gitignore``.

    Equivalent to ``git ls-files -ci --exclude-standard -z``.
    """
    out = _git(root, "ls-files", "-ci", "--exclude-standard", "-z")
    return {p for p in out.split("\0") if p}


# ---------------------------------------------------------------------------
# Prefix / scope helpers
# ---------------------------------------------------------------------------


def _normalize_prefixes(prefixes: list[str]) -> list[str]:
    """Strip leading ``./`` from every prefix for consistent matching."""
    return [p.removeprefix("./") for p in prefixes]


def _in_scope(path: str, prefixes: list[str]) -> bool:
    """Return ``True`` when *path* starts with any of *prefixes*.

    An empty *prefixes* list means every path is in scope.
    """
    if not prefixes:
        return True
    return any(path.startswith(p) for p in prefixes)
