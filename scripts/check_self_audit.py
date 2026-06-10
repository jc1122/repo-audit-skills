#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present in the
baseline (regressions), or baseline entries no longer produced by
the audit (stale entries)."""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "scripts" / "self_audit_snapshot.json"
BASELINE = ROOT / "scripts" / "self_audit_baseline.json"


def _identities(findings: list[dict]) -> set[tuple]:
    return {tuple(sorted(d.items())) for d in findings}


def _load_snapshot(snapshot: str | None) -> list[dict]:
    if snapshot:
        return json.loads(Path(snapshot).read_text())
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "self_audit.py")],
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    return json.loads(SNAPSHOT.read_text())


def _verdict(current: list[dict], baseline: list[dict]) -> tuple[int, dict]:
    base = _identities(baseline)
    # Regressions first: findings present now but absent from the baseline.
    regressions = [d for d in current if tuple(sorted(d.items())) not in base]
    if regressions:
        return 1, {"status": "fail", "new_findings": regressions}
    # Then stale entries: baseline ids the audit no longer produces.
    stale = [dict(t) for t in sorted(base - _identities(current))]
    if stale:
        return 1, {
            "status": "fail",
            "stale_baseline": stale,
            "message": "baseline entries no longer produced by the audit; "
            "remove them from scripts/self_audit_baseline.json "
            "in the same commit",
        }
    return 0, {"status": "pass", "count": len(current), "baseline": len(baseline)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ratchet the self-audit snapshot against the baseline."
    )
    parser.add_argument("--snapshot", help="Existing snapshot JSON (testing only).")
    parser.add_argument("--baseline", help="Alternate baseline JSON (testing only).")
    args = parser.parse_args(argv)
    current = _load_snapshot(args.snapshot)
    baseline = json.loads(Path(args.baseline or BASELINE).read_text())
    code, payload = _verdict(current, baseline)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
