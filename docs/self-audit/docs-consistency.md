# Docs-consistency gate (check:docs)

`npm run check:docs` runs `scripts/check_docs_consistency.py`, which invokes
`skills/docs-consistency-audit/scripts/docs_consistency_audit.py` over a living-docs
scope: static `README.md`, `AGENTS.md`, `docs/self-audit`, `shared`, `scripts`, `bin`,
plus each `skills/<d>/SKILL.md` and its `scripts`/`docs` dirs. Excluded by omission:
`docs/superpowers/**` and `docs/audits/**` (immutable point-in-time records),
`skills/*/tests/**` (deliberately dirty fixtures owned by check:fixtures), `tests/`,
the `node_modules` dependency tree. Docstring coverage stays off (default).

A finding = a `doc_path_missing` (dead path reference), `doc_flag_unknown` (stale CLI
flag), or stale version pin in living docs.

**Ratchet discipline and identity coarseness** are the same as the security gate.
Snapshot `docs_consistency_snapshot.json` under `scripts/` (gitignored), baseline
`scripts/docs_consistency_baseline.json`.

**Freeze policy.** Deliberately-illustrative references (documenting a file the user's
repo would have, not this one) may be frozen per-finding; everything else is fixed.

**Seeding record (SP8 G4-R1).** Pre-seed 18 `doc_path_missing`. All 18 fixed
mechanically (16 relative SKILL.md refs rewritten repo-root-relative; one runtime
placeholder rewritten `<work>/setup.cfg`; one illustrative historical dead path
un-backticked). 0 frozen. Baseline = []; no frozen log.
