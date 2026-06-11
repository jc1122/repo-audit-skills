#!/usr/bin/env python3
"""check:docs — ratchet the docs-consistency snapshot against the baseline.

Docs consistency ratchet gate (living-docs source scope).
"""
# -- gate-id: docs-consistency-audit                                   --

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import GateSpec, gate_main  # noqa: E402  # docs-audit

ROOT = Path(__file__).resolve().parents[1]  # -- gate: docs-consistency-audit


def _living_docs_prefixes() -> list[str]:
    pres = ["README.md", "AGENTS.md", "docs/self-audit", "shared", "scripts", "bin"]
    for d in sorted((ROOT / "skills").iterdir()):
        if not d.is_dir():
            continue
        pres.append(f"skills/{d.name}/SKILL.md")
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
        if (d / "docs").is_dir():
            pres.append(f"skills/{d.name}/docs")
    return pres


def _spec() -> GateSpec:
    out = ROOT / ".self_audit_out" / "docs"
    leaf = (
        ROOT
        / "skills"
        / "docs-consistency-audit"
        / "scripts"
        / "docs_consistency_audit.py"
    )
    cmd = [sys.executable, str(leaf), "--root", str(ROOT), "--out-dir", str(out)]
    for prefix in _living_docs_prefixes():
        cmd += ["--source-prefix", prefix]
    return GateSpec(
        leaf_cmd=cmd,
        findings_file=str(out / "docs-consistency_findings.json"),
        snapshot_path=str(ROOT / "scripts" / "docs_consistency_snapshot.json"),
        baseline_path="scripts/docs_consistency_baseline.json",
        description="Ratchet the docs-consistency snapshot against the baseline.",
    )


# -- gate runner (docs-consistency-audit) ---------------------------------
def main(argv: list[str] | None = None) -> int:
    return gate_main(argv, _spec())


if __name__ == "__main__":
    sys.exit(main())
