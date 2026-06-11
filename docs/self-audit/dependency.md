# Dependency gate (check:dependency)

`npm run check:dependency` runs `scripts/check_dependency_audit.py`, which invokes
`skills/dependency-audit/scripts/dependency_audit.py` over the production scope (same as
security). This repo has no `pyproject.toml` or `requirements*.txt`, so the leaf reports
`manifest: false` and 0 findings — an empty snapshot that passes by design. The gate is
a tripwire for the day a manifest appears. Snapshot `scripts/dependency_snapshot.json`
(gitignored), baseline `scripts/dependency_baseline.json` (`[]`).

**Ratchet discipline and identity coarseness** are the same as the security gate.

**No frozen log** — the baseline is empty.

<!-- filled at G4-R1: baseline [] (manifest:false) -->
