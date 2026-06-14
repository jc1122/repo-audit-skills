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
# Portable acceptance policy; the report-stage `finding` entries ARE the baseline.
BASELINE_PATH = ".repo-audit/accept.json"
BASELINE = ROOT / BASELINE_PATH
_FINDING_KEYS = ("leaf", "metric", "path", "symbol")


def _report_finding(entry: object, index: int, src: Path) -> dict | None:
    """Return a report-stage `finding` row, or None if the entry is another kind.

    Fail-closed: raises ValueError on a malformed entry/match object.
    """
    if not isinstance(entry, dict):
        raise ValueError(f"{src}: accept[{index}] must be an object")
    match = entry.get("match")
    if not isinstance(match, dict):
        raise ValueError(f"{src}: accept[{index}].match must be an object")
    if match.get("kind") != "finding":
        return None
    if "report" not in (entry.get("applies") or []):
        return None
    return {k: match.get(k, "") for k in _FINDING_KEYS}


def _baseline_rows(accept_path: Path) -> list[dict]:
    """Load the report-stage `finding` rows from a `.repo-audit/accept.json`.

    Returns each as a flat ``{leaf, metric, path, symbol}`` dict (the legacy
    baseline shape). Fail-closed: a malformed policy raises rather than
    silently accepting nothing.
    """
    payload = json.loads(accept_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError(f"{accept_path}: malformed accept policy (version must be 1)")
    accept = payload.get("accept")
    if not isinstance(accept, list):
        raise ValueError(f"{accept_path}: 'accept' must be an array")
    rows = (_report_finding(e, i, accept_path) for i, e in enumerate(accept))
    return [r for r in rows if r is not None]


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
    baseline = (
        json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        if args.baseline
        else _baseline_rows(BASELINE)
    )
    code, payload = verdict(current, baseline, baseline_path=BASELINE_PATH)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
