# Amendment Proposal NNN — <short title>

> **L-8 protocol.** When the loop hits a *contract-blocked* improvement it writes a
> proposal here, continues other work, and does **NOT** self-apply it — proposals
> are operator-reviewed async. Max 3 proposals per run; over-proposing is itself a
> flagged anti-pattern in the ledger. The `goal-plan-amender` skill is the
> precedent pattern.

- **Proposal ID:** NNN
- **Date:** YYYY-MM-DD
- **Status:** PROPOSED | ACCEPTED | REJECTED | DEFERRED  (operator sets)

## Blocked contract
Which FROZEN contract (L-0..L-10) or rule (R1..R7) blocks the improvement, quoted.

## Measured impossibility (evidence, not opinion)
The concrete, mined evidence that the improvement cannot be made under the current
contract — KPI rows, gate output, run-dir artifacts, ledger references. No prose
assertions; cite artifacts (R5).

## Minimal proposed diff
The smallest change to the contract/plan that unblocks it. Show the exact wording
delta. Keep it minimal — propose the least authority needed.

## Risk
What the amendment could break (convergence guarantee, surface budget, determinism,
freeze integrity). How the risk is bounded.

## Expected gain
The measured improvement expected (e.g. "+X rows/hour", "−Y min gate wall-clock",
"removes a recurring lesson class"), tied to the KPI it moves.

## Operator disposition
(Left blank by the loop; filled by the operator on review.)
