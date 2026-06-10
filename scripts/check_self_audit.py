#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present
in the baseline (regressions)."""

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "self_audit.py")],
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    current = json.loads((ROOT / "scripts" / "self_audit_snapshot.json").read_text())
    baseline = json.loads((ROOT / "scripts" / "self_audit_baseline.json").read_text())
    base = {tuple(sorted(d.items())) for d in baseline}
    new = [d for d in current if tuple(sorted(d.items())) not in base]
    if new:
        print(json.dumps({"status": "fail", "new_findings": new}, indent=2))
        return 1
    print(
        json.dumps(
            {"status": "pass", "count": len(current), "baseline": len(baseline)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
