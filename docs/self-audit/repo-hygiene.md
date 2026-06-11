# Repo-hygiene gate (check:hygiene)

`npm run check:hygiene` runs `scripts/check_repo_hygiene.py`, which invokes
`skills/repo-hygiene-audit/scripts/repo_hygiene_audit.py` over the full repo with NO
`--source-prefix`. The leaf applies source-prefix filtering post-hoc over all findings,
so prefixing would silently drop root-level release-hygiene findings; the gate must keep
the release-hygiene group on. Snapshot scripts/repo_hygiene_snapshot.json (gitignored),
baseline `scripts/repo_hygiene_baseline.json`.

Current state: 0 findings (`"git": true`); baseline is `[]` (empty) — and stays a
tripwire.

**Ratchet discipline and identity coarseness** are the same as the security gate.

**No frozen log** — the baseline is empty, nothing to freeze.

**Seeding record (SP8 G4-R1).** Pre-seed 0 findings (`"git": true`). Nothing to fix,
nothing to freeze. Baseline = [] (empty tripwire).
