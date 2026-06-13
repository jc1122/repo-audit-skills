# SP14 candidates — write down, do NOT start (L-1 overflow)

After the SP13 X3 freeze the finding universe is CLOSED. Any new finding
class / lane / metric / eval case / cross-repo capability discovered during the
SP13 burn-down is recorded HERE and deferred to SP14 — never added to the frozen
universe mid-run (L-1 convergence guarantee).

## Inherited from the SP13 plan "Out of scope"
- Multi-language code-health leaves (the family is Python-deterministic; new
  language leaves are a program, not a finding).
- Auto-applying patches without a worker verify step.
- Cross-repo lesson sharing beyond the family.
- ML-ranked backlog prioritization.
- Any new finding class/lane after the X3 freeze.
- Running the harness against foreign repos at scale (one R1 validation pass
  against a foreign repo is allowed as a self-application checklist item, not a
  work package).

## Surfaced during SP13 (candidates, deferred)
- **Instruction-eval coverage > 1 skill.** X1.2 shipped one advisory eval case
  (complexity-audit; recorded drift 1 vs 2 — the SKILL.md under-specifies the
  module-MI finding). A real eval *suite* across high-traffic skills is SP14
  (the candidate lesson `instruction-eval/complexity-audit` stays in
  lessons.jsonl as the seed). Sunset of X1.2: fold into that suite.
- **Fold instruction-lint into docs-consistency-audit.** X1.1 shipped instruction
  -lint as a standalone gate (the plan's "OR" option) to avoid a leaf-behavior
  change + docs-lane baseline collision mid-run. Its R2 sunset is to fold the
  command-existence + required-section checks into the docs-consistency-audit
  leaf once stable — an SP14 leaf change (changes diagnosis behavior → reinstall).
- **Wave wall-clock floor / per-lane time budget.** The installed 8-lane wave on
  repo-A exceeds 300s; the 220-test triage suite is the wall-clock floor. SP13
  attacks it via the test-redundancy-triage self-application (DELETE speed
  batches). A first-class per-lane wave time budget + parallel lane execution in
  the runner (beyond SP12's gate parallelization) is an SP14 control candidate.
- **repo-A wave-baseline gate.** repo-A has no `check_wave_baseline.py` gate; its
  installed-wave residue (hotspot-dominated) is ledger-tracked only. A repo-A
  wave-baseline gate (parity with repo-B/repo-P) would make its convergence
  machine-enforced rather than ledger-enforced — SP14.
