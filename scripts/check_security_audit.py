#!/usr/bin/env python3
"""check:security — ratchet the security-audit snapshot against the baseline.

Security-specific ratchet gate (bandit findings).
"""
# -- gate-id: security-audit                                            --

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import GateSpec, gate_main, production_prefixes  # noqa: E402  # sec

ROOT = Path(__file__).resolve().parents[1]  # -- gate: security-audit
CONFIG = ROOT / "scripts" / "security_audit_config.json"


def _spec() -> GateSpec:
    out = ROOT / ".self_audit_out" / "security"
    leaf = ROOT / "skills" / "security-audit" / "scripts" / "security_audit.py"
    cmd = [
        sys.executable,
        str(leaf),
        "--root",
        str(ROOT),
        "--out-dir",
        str(out),
        "--config",
        str(CONFIG),
    ]
    # production-scoped: every skill scripts dir + shared + scripts/
    for prefix in production_prefixes(ROOT):
        cmd += ["--source-prefix", prefix]
    return GateSpec(
        leaf_cmd=cmd,
        findings_file=str(out / "security_findings.json"),
        snapshot_path=str(ROOT / "scripts" / "security_snapshot.json"),
        baseline_path="scripts/security_baseline.json",
        description="Ratchet the security-audit snapshot against the baseline.",
    )


# -- gate runner (security-audit) ----------------------------------------
def main(argv: list[str] | None = None) -> int:
    return gate_main(argv, _spec())


if __name__ == "__main__":
    sys.exit(main())
