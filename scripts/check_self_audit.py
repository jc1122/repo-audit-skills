#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present in the baseline
(regressions), or baseline entries no longer produced by the audit (stale)."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import verdict  # noqa: E402
from self_audit import run as run_self_audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "scripts" / "self_audit_snapshot.json"
BASELINE_PATH = "scripts/self_audit_baseline.json"
BASELINE = ROOT / BASELINE_PATH


def _run_self_audit() -> list[dict] | None:
    try:
        current = run_self_audit(ROOT / ".self_audit_out")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"self-audit failed: {exc}",
                },
                indent=2,
            )
        )
        return None
    SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    return current


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ratchet the self-audit snapshot against the baseline."
    )
    parser.add_argument(
        "--snapshot",
        help="Existing snapshot JSON (testing only — skips the self-audit).",
    )
    parser.add_argument("--baseline", help="Alternate baseline JSON (testing only).")
    args = parser.parse_args(argv)

    current = (
        json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        if args.snapshot
        else _run_self_audit()
    )
    if current is None:
        return 1
    baseline = json.loads(Path(args.baseline or BASELINE).read_text(encoding="utf-8"))
    code, payload = verdict(current, baseline, baseline_path=BASELINE_PATH)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
