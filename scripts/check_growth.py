#!/usr/bin/env python3
"""check:growth — run growth-audit leaf and gate on unsuppressed findings.

The gate invokes the growth-audit leaf, then parses its findings JSON.
It never trusts the leaf exit code alone:

* Leaf exit 1 — parse ``growth-audit_findings.json``; fail only if the file
  contains non-empty findings.
* Leaf exit 2 — hard gate error.
* Missing / invalid findings JSON — hard gate error.

Output is a compact one-line JSON summary with ``status``, ``count``, and
``baseline``.
"""
# -- gate-id: growth-audit                                                --

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # -- gate: growth-audit
LEAF = "growth-audit"
_OUT_DIR = ROOT / ".self_audit_out" / "growth"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def baseline_rev() -> str:
    """Return the most recent annotated tag (``git describe --tags --abbrev=0``).

    Exits the process with code 2 when no tags exist.
    """
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"git describe failed: {proc.stderr.strip()}",
                }
            )
        )
        raise SystemExit(2)
    return proc.stdout.strip()


def decide_from_findings_file(findings_path: Path) -> tuple[int, dict]:
    """Parse a growth-audit findings JSON and produce ``(exit_code, payload)``.

    Returns
    -------
    (0, payload)
        Pass — findings list is empty.
    (1, payload)
        Unsuppressed findings exist.
    (2, payload)
        Hard error — JSON missing, unreadable, or not a list.
    """
    try:
        text = findings_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        return 2, {
            "status": "error",
            "message": f"findings JSON missing or invalid: {exc}",
        }
    if not isinstance(data, list):
        return 2, {
            "status": "error",
            "message": "findings JSON is not a list",
        }

    count = len(data)
    if count == 0:
        return 0, {"status": "pass", "count": 0}
    return 1, {"status": "fail", "count": count}


# ---------------------------------------------------------------------------
# gate runner
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the growth gate.

    Invokes ``skills/growth-audit/scripts/growth_audit.py``, then gates on the
    findings JSON.  Returns 0 on pass, 1 on unsuppressed findings, 2 on hard
    error.
    """
    base = baseline_rev()

    leaf_script = ROOT / "skills" / LEAF / "scripts" / "growth_audit.py"
    config = ROOT / "scripts" / "growth_allowances.json"

    cmd = [
        sys.executable,
        str(leaf_script),
        "--root",
        str(ROOT),
        "--out-dir",
        str(_OUT_DIR),
        "--baseline-rev",
        base,
        "--config",
        str(config),
    ]

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600, check=False
    )

    if proc.returncode == 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"leaf audit failed (exit 2): {proc.stderr.strip()}",
                }
            )
        )
        return 2

    findings_path = _OUT_DIR / f"{LEAF}_findings.json"
    exit_code, payload = decide_from_findings_file(findings_path)

    # Annotate with the baseline revision used
    payload["baseline"] = base
    print(json.dumps(payload))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
