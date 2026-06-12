#!/usr/bin/env python3
"""Gate: run every pytest suite in isolation, in parallel; aggregate results.

Suites are independent by family design (each runs with its own rootdir).
Results are sorted by suite path so the snapshot is byte-identical across
reruns regardless of completion order (R4 / C-5 convergence).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "scripts" / "full_pytest_snapshot.json"
WORKERS = max(2, (os.cpu_count() or 2) - 1)


def suite_dirs() -> list[Path]:
    dirs = [ROOT / "tests"] if (ROOT / "tests").is_dir() else []
    dirs += sorted(path for path in ROOT.glob("skills/*/tests") if path.is_dir())
    return dirs


def run_suite(suite: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(suite), "-q", "--color=no",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=suite.parent, check=False,
    )
    tail = (proc.stdout.strip().splitlines()[-1:]
            or proc.stderr.strip().splitlines()[-1:])
    return {
        "suite": str(suite.relative_to(ROOT)),
        "returncode": proc.returncode,
        "tail": tail,
    }


def sort_results(results: list[dict]) -> list[dict]:
    return sorted(results, key=lambda r: r["suite"])


def main() -> int:
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = sort_results(list(pool.map(run_suite, suite_dirs())))
    SNAPSHOT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failed = [r for r in results if r["returncode"] != 0]
    print(f"full-pytest: {len(results) - len(failed)}/{len(results)} suites green")
    for r in failed:
        print(f"FAIL {r['suite']}: {r['tail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
