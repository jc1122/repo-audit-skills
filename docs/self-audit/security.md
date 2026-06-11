# Security gate (check:security)

`npm run check:security` runs `scripts/check_security_audit.py`, which invokes
`skills/security-audit/scripts/security_audit.py` (pinned bandit==1.9.4, bandit-only —
no network, no `--advisory-report`) over the production scope (`shared`, `scripts`,
every `skills/<d>/scripts`). It normalises findings to 4-key identities
`{leaf, path, symbol, metric}`, writes `scripts/security_snapshot.json` (gitignored),
and ratchets against `scripts/security_baseline.json`.

A finding = a bandit SECURITY signal in production code.

**Ratchet discipline.** A new finding fails the gate. A stale baseline entry (no longer
produced by the leaf) also fails and must be removed from
`scripts/security_baseline.json` in the same commit.

**Identity coarseness.** Identity is `{leaf, path, symbol, metric}` as a set — two
findings of the same bandit test in one file collapse to one identity.

**Freeze policy.** Residual findings are frozen per-finding with an individual
justification in the security frozen log (no blanket freezes). Individually-justified
freezes are recorded there.

<!-- filled at G4-R1: baseline count + fixes (13 hashlib + tmp) + freeze count -->
