#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present in the baseline
(regressions), or baseline entries no longer produced by the audit (stale)."""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import GateSpec, gate_main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    return gate_main(
        argv,
        GateSpec(
            leaf_cmd=[sys.executable, str(ROOT / "scripts" / "self_audit.py")],
            findings_file=str(ROOT / ".self_audit_out" / "code_health_summary.json"),
            snapshot_path=str(ROOT / "scripts" / "self_audit_snapshot.json"),
            baseline_path="scripts/self_audit_baseline.json",
            description="Ratchet the self-audit snapshot against the baseline.",
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
