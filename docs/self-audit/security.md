# Security gate (check:security)

`npm run check:security` runs `scripts/check_security_audit.py`, which invokes
`skills/security-audit/scripts/security_audit.py` (pinned bandit==1.9.4, bandit-only —
no network, no `--advisory-report`) over the production scope (`shared`, `scripts`,
every `skills/<d>/scripts`). It normalises findings to 4-key identities
`{leaf, path, symbol, metric}`, writes the gitignored `security_snapshot.json` under
`scripts/`, and ratchets against `scripts/security_baseline.json`.

A finding = a bandit SECURITY signal in production code.

**Ratchet discipline.** A new finding fails the gate. A stale baseline entry (no longer
produced by the leaf) also fails and must be removed from
`scripts/security_baseline.json` in the same commit.

**Identity coarseness.** Identity is `{leaf, path, symbol, metric}` as a set — two
findings of the same bandit test in one file collapse to one identity.

**Freeze policy.** Residual findings are frozen per-finding with an individual
justification in the security frozen log (no blanket freezes). Individually-justified
freezes are recorded there.

**Seeding record (SP8 G4-R1).** Pre-seed 64 findings (50 low / 1 medium / 13 high).
Fixed 15: 13 hashlib B324 highs (sha1 finding-id hashes given usedforsecurity=False —
fixed once in shared/health_common.py and re-vendored byte-identical), 1 B108 hardcoded
/tmp dest (tempfile.gettempdir()), 1 B112 try/except/continue (narrowed exception).
Residual 49 frozen per-finding (26 B603 subprocess-no-shell, 17 B404 subprocess-import,
4 B607 partial-path, 2 B105 false-positive on the literal 'False') with individual
justifications in the security frozen log. Baseline = 49; zero unjustified entries.

## Advisory mode (out-of-band)

To run advisory checks, generate the upstream report offline on a network-allowed
machine: `pip-audit -f json -o /tmp/pip_audit.json`.

Then run:
`python3 skills/security-audit/scripts/security_audit.py --root . --out-dir <dir> <prefixes> --advisory-report /tmp/pip_audit.json`.

Advisory findings are diagnosis-only and must not be added to the gate baseline.
The npm security gate remains bandit-only and offline, per SP8 rationale.
