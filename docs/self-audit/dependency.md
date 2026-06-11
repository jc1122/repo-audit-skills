# Dependency gate (check:dependency)

`npm run check:dependency` runs `scripts/check_dependency_audit.py`, which invokes
`skills/dependency-audit/scripts/dependency_audit.py` over the production scope (same as
security). This repo has no `pyproject.toml` or `requirements*.txt`, so the leaf reports
`manifest: false` and 0 findings — an empty snapshot that passes by design. The gate is
a tripwire for the day a manifest appears. Snapshot `dependency_snapshot.json` under
`scripts/` (gitignored), baseline `scripts/dependency_baseline.json` (`[]`).

**Ratchet discipline and identity coarseness** are the same as the security gate.

**No frozen log** — the baseline is empty.

**Seeding record (SP8 G4-R1).** Pre-seed 0 findings (`manifest: false` — no
pyproject/requirements). Nothing to fix or freeze. Baseline = [].
