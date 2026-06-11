#!/usr/bin/env python3
"""check:dependency — ratchet the dependency-audit snapshot against the baseline.

Dependency ratchet gate (production source scope).
"""
# -- gate-id: dependency-audit                                         --

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import GateSpec, production_prefixes, gate_main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]  # -- gate: dependency-audit


def _spec() -> GateSpec:
    out = ROOT / ".self_audit_out" / "dependency"
    leaf = ROOT / "skills" / "dependency-audit" / "scripts" / "dependency_audit.py"
    cmd = [sys.executable, str(leaf), "--root", str(ROOT), "--out-dir", str(out)]
    for prefix in production_prefixes(ROOT):
        cmd += ["--source-prefix", prefix]
    return GateSpec(
        leaf_cmd=cmd,
        findings_file=str(out / "dependency_findings.json"),
        snapshot_path=str(ROOT / "scripts" / "dependency_snapshot.json"),
        baseline_path="scripts/dependency_baseline.json",
        description="Ratchet the dependency-audit snapshot against the baseline.",
    )


# -- gate runner (dependency-audit) --------------------------------------
def main(argv: list[str] | None = None) -> int:
    return gate_main(argv, _spec())


if __name__ == "__main__":
    sys.exit(main())
