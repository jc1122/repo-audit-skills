"""Git operations and commit-history reading for the hotspot-audit leaf.

Parsing assumptions
-------------------
- ``git log --numstat --no-renames`` produces tab-separated numstat lines
  with three fields (added, deleted, path).  Only lines with a non-empty
  path are treated as file references.
- Commit blocks are delimited by the ASCII SOH character (``\\x01``);
  within a block the commit SHA and author name are separated by STX
  (``\\x02``).  This avoids ambiguity with any characters that could
  appear in author names or file paths.
- The ``--no-renames`` flag ensures renamed files are reported as a
  delete + add pair; the audit does not track churn across renames.
- A 120-second timeout guards against hung git processes on large or
  network filesystem repositories.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from _audit_shared import ToolError


def _git(root: Path, *args: str) -> str:
    """Run a git command in *root* and return its stdout.

    Raises ``ToolError`` if git is not installed or the command fails.
    All output is captured so the caller sees only the result text.
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


def _resolve_rev(root: Path, rev: str) -> str:
    """Resolve *rev* to a full 40-character commit SHA.

    Uses ``git rev-parse --verify`` so the caller always works with the
    canonical commit identity, not a branch name or relative ref.
    """
    out = _git(root, "rev-parse", "--verify", f"{rev}^{{commit}}")
    return out.strip()


def _validate_git_root(root: Path) -> None:
    """Confirm that *root* is inside a valid git working tree.

    Raises ``ToolError`` when the directory is not a git repository.
    """
    if (
        subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
        ).returncode
        != 0
    ):
        raise ToolError(f"not a git repository: {root}")


def read_history(root: Path, rev: str, max_commits: int) -> list[dict]:
    """Return a deterministic list of commit dicts from git history.

    Each dict has keys ``sha``, ``author``, and ``files`` (a list of
    relative paths).  Commits are ordered oldest-first by git default
    ordering, capped at *max_commits*.
    """
    sha = _resolve_rev(root, rev)
    raw = _git(
        root,
        "log",
        sha,
        f"--max-count={max_commits}",
        "--numstat",
        "--no-renames",
        "--format=%x01%H%x02%an",
    )
    commits: list[dict] = []
    for block in raw.split("\x01"):
        if not block.strip():
            continue
        head, _, body = block.partition("\n")
        commit_sha, _, author = head.partition("\x02")
        files = []
        for line in body.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2]:
                files.append(parts[2])
        commits.append({"sha": commit_sha, "author": author, "files": files})
    return commits
