#!/usr/bin/env python3
"""Deterministic smoke checks: every leaf script answers --help."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Append one command per skill as later plans land.
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
    ["python3", "skills/dead-code-audit/scripts/dead_code_audit.py", "--help"],
    ["python3", "skills/structure-audit/scripts/structure_audit.py", "--help"],
    ["python3", "skills/quality-audit/scripts/quality_audit.py", "--help"],
    [
        "python3",
        "skills/code-health-audit-pipeline/scripts/code_health_pipeline.py",
        "--help",
    ],
    ["python3", "skills/test-audit-pipeline/scripts/audit_pipeline.py", "--help"],
    [
        "python3",
        "skills/test-quality-assurance/scripts/audit_test_quality.py",
        "--help",
    ],
    ["python3", "skills/test-redundancy-triage/scripts/triage_redundancy.py", "--help"],
]


def main() -> int:
    failures: list[dict[str, str]] = []
    for cmd in HELP_COMMANDS:
        result = subprocess.run(
            cmd, cwd=ROOT, text=True, capture_output=True, check=False
        )
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
    print(
        json.dumps(
            {"status": "pass", "commands": [" ".join(cmd) for cmd in HELP_COMMANDS]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
