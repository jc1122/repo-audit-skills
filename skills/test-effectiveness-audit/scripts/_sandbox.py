"""Isolated mutmut sandbox setup for test-effectiveness-audit.

Creates a self-contained work directory under out-dir/.mutmut-work so
that mutmut never touches the target repo root.  The sandbox includes:
- scoped source files copied from *rel_paths*
- the test directory (--tests-dir) copied as-is
- a setup.cfg with [mutmut] source_paths

All mutmut subprocess invocations throughout the pipeline use cwd
pointing at the returned work directory, never the target repo root.
"""

from __future__ import annotations
import shutil
from pathlib import Path


def prepare_sandbox(
    root: Path,
    rel_paths: list[str],
    tests_dir: str,
    out_dir: Path,
) -> Path:
    """Set up an isolated mutmut sandbox; return the work directory path.

    Copies every file/directory listed in *rel_paths* (root-relative)
    into work/ preserving their relative layout.  Then copies *tests_dir*
    (also root-relative) into work/.  Finally writes a minimal setup.cfg
    so mutmut knows which source paths to mutate.

    The caller must ensure *out_dir* exists or is creatable.
    """
    work = out_dir / ".mutmut-work"
    # Start fresh — remove any previous run artifacts
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    # Copy every scoped source path into the sandbox
    top_entries: list[str] = []
    for rel in rel_paths:
        src = root / rel
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)
        top = rel.split("/")[0]
        if top not in top_entries:
            top_entries.append(top)

    # Copy the test directory so mutmut can discover + run tests
    tests_src = root / tests_dir
    tests_dst = work / tests_dir
    if tests_src.is_dir():
        if tests_dst.exists():
            shutil.rmtree(tests_dst)
        shutil.copytree(tests_src, tests_dst)

    # Write mutmut configuration pointing at the top-level source dirs
    source_paths_str = " ".join(top_entries)
    (work / "setup.cfg").write_text(
        f"[mutmut]\nsource_paths={source_paths_str}\n",
        encoding="utf-8",
    )
    return work
