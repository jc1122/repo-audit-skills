#!/usr/bin/env python3
"""Deterministic smoke checks for bundled skill script entrypoints."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELP_COMMANDS = [
    ["python3", "skills/repo-audit-refactor-optimize/scripts/check_skill_requirements.py", "--help"],
    ["python3", "skills/test-audit-pipeline/scripts/audit_pipeline.py", "--help"],
    ["python3", "skills/test-quality-assurance/scripts/audit_test_quality.py", "--help"],
    ["python3", "skills/test-redundancy-triage/scripts/triage_redundancy.py", "--help"],
    ["python3", "skills/perf-benchmark/scripts/perf_benchmark_pipeline.py", "--help"],
]


def main() -> int:
    failures: list[dict[str, str]] = []
    for cmd in HELP_COMMANDS:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            failures.append(
                {
                    "command": " ".join(cmd),
                    "stdout": result.stdout[-1000:],
                    "stderr": result.stderr[-1000:],
                }
            )
    if failures:
        print(json.dumps({"status": "fail", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "commands": [" ".join(cmd) for cmd in HELP_COMMANDS]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
