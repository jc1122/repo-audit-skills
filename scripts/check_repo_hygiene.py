#!/usr/bin/env python3
"""check:hygiene — ratchet the repo-hygiene snapshot against the baseline.

Full-repo hygiene ratchet (no source-prefix scoping).
"""
# -- gate-id: repo-hygiene-audit                                       --

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import GateSpec, gate_main  # noqa: E402  # hygiene-audit

ROOT = Path(__file__).resolve().parents[1]  # -- gate: repo-hygiene-audit


def _spec() -> GateSpec:
    out = ROOT / ".self_audit_out" / "hygiene"
    leaf = ROOT / "skills" / "repo-hygiene-audit" / "scripts" / "repo_hygiene_audit.py"
    cmd = [sys.executable, str(leaf), "--root", str(ROOT), "--out-dir", str(out)]
    return GateSpec(
        leaf_cmd=cmd,
        findings_file=str(out / "repo-hygiene_findings.json"),
        snapshot_path=str(ROOT / "scripts" / "repo_hygiene_snapshot.json"),
        baseline_path="scripts/repo_hygiene_baseline.json",
        description="Ratchet the repo-hygiene snapshot against the baseline.",
    )


# -- gate runner (repo-hygiene-audit) ------------------------------------
def main(argv: list[str] | None = None) -> int:
    return gate_main(argv, _spec())


if __name__ == "__main__":
    sys.exit(main())
