#!/usr/bin/env python3
"""Gate: run every pytest suite in isolation; aggregate results."""

from __future__ import annotations

import json
import contextlib
import io
import multiprocessing
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "scripts" / "full_pytest_snapshot.json"


def suite_dirs() -> list[Path]:
    dirs = [ROOT / "tests"] if (ROOT / "tests").is_dir() else []
    dirs += sorted(path for path in ROOT.glob("skills/*/tests") if path.is_dir())
    return dirs


def _run_suite(suite: str, cwd: str, queue) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = 1
    try:
        os.chdir(cwd)
        script_dir = Path(__file__).resolve().parent
        sys.path = [
            path
            for path in sys.path
            if Path(path or cwd).resolve() != script_dir
        ]
        sys.path.insert(0, cwd)
        import pytest

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = int(pytest.main([suite, "-q", "--color=no"]))
    except Exception:
        stderr.write(traceback.format_exc())
    queue.put((code, stdout.getvalue(), stderr.getvalue()))


def main() -> int:
    results = []
    context = multiprocessing.get_context("fork")
    for suite in suite_dirs():
        queue = context.Queue()
        process = context.Process(
            target=_run_suite,
            args=(str(suite), str(suite.parent), queue),
        )
        process.start()
        process.join()
        code, stdout, stderr = queue.get() if not queue.empty() else (1, "", "")
        stdout_tail = stdout.strip().splitlines()[-1:]
        stderr_tail = stderr.strip().splitlines()[-1:]
        results.append(
            {
                "suite": str(suite.relative_to(ROOT)),
                "returncode": code if process.exitcode == 0 else process.exitcode,
                "tail": stdout_tail or stderr_tail,
            }
        )
    SNAPSHOT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failed = [result for result in results if result["returncode"] != 0]
    print(f"full-pytest: {len(results) - len(failed)}/{len(results)} suites green")
    for result in failed:
        print(f"FAIL {result['suite']}: {result['tail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
