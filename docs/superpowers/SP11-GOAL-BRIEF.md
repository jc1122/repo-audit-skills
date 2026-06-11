# SP11 Goal Brief — unattended dogfood loop until all baselines are zero

Use this brief as the source input for goal-preflight. The authoritative plan
(scope, contracts, tasks, kernels) is
`docs/superpowers/plans/2026-06-11-sp11-unattended-dogfood-loop.md` in repo-A;
preflight should digest the plan and keep this brief's boundaries verbatim.

## Goal statement

Run the steady-state dogfood loop unattended and iteratively across the three
family repos until every ratcheted baseline is zero — each finding fixed at
source or config-gated with counted suppressions — with machine ship gates
replacing human ship authorization.

## Repos and entry state (2026-06-11)

- repo-A `/home/jakub/projects/repo-audit-skills` — main `56834cd`, v0.5.1; selfaudit baseline 92, security baseline 49, others empty.
- repo-B `/home/jakub/projects/repo-audit-refactor-optimize` — main `7c23276`, v0.4.1; wave baseline 9.
- repo-P `/home/jakub/projects/perf-benchmark-skill` — main `ac89675`, v0.3.0; wave baseline 55.

## Autonomy and harness profile

- Main and branch orchestrators: Codex gpt-5.5, approvals DISABLED (unattended).
  The human has explicitly authorized (2026-06-11): no human approval for any
  step, including push/tag/release/reinstall once the plan's C-6 machine ship
  gate passes, and the stale-skill purge under plan task B5.1 constraints.
- Workers: delegate through opencode-worker-bridge with file-backed packets per
  plan contract C-7. Worker green is never evidence; orchestrators re-run gates.
- Before preflight, verify/create the goal config with goal-config
  (`create_goal_config.py` / `check_goal_config.py --for-preflight`) selecting
  the gpt-5.5 unattended profile and opencode worker routes; run the fail-closed
  smoke test. Fail closed if no route is green.

## Branch groups (rolling schedule)

1. Group 1 (serial): B0 enablement (full-pytest gate, bridge smoke, mutation
   census) → B1 precision round (security trusted-subprocess policy, hotspot
   family policy, repo-A security baseline 49→0, ship v0.5.2 + reinstall).
2. Group 2 (parallel after B1 readback): B2 repo-A structural loop (selfaudit
   92→0, mutation-gated), B3 repo-B lane (wave 9→0), B4 repo-P lane (wave
   55→0 incl. actions bump and B105/B324 source fixes).
3. Group 3 (serial, last): B5 stale-skill purge (allowlist-driven), final
   reinstall + readback, final report.

## Definition of Done (falsifiable; copy into main prompt)

1. repo-A `npm run check` green with 10 gates; selfaudit and security baselines `[]`; fresh-clone sim green; CI green; release tagged.
2. repo-B wave baseline `[]`; suite green; CI green; release tagged if source shipped.
3. repo-P wave baseline `[]`; suite green; CI completes with zero deprecation annotations; release tagged if source shipped.
4. Every suppression class counted in leaf reports, regression-tested both directions, documented in SKILL.md Limits.
5. Installed family sets exactly match source manifests post-purge, at final versions; bootstrap probe exit 0.
6. Ledger `docs/self-audit/2026-06-sp11-unattended-loop.md` complete with per-iteration baseline trajectory, discarded attempts, and ship evidence.

## Hard constraints (from the plan; FROZEN)

- C-1 precision discipline; C-2 version policy; C-3 mutation-gated structural
  batches (≤2 per repo per iteration, throwaway worktrees, kill rate ≥ 80%);
  C-4 shrink-only ratchets; C-5 convergence ×2; C-6 machine ship gate order
  (local gates → convergence → fresh-clone sim → push → CI watch → tag/release
  → reinstall → readback); C-7 file-backed opencode worker packets ≤8k tokens;
  C-8 STOP conditions (two zero-shrink iterations, unfixable growth, second CI
  red, or any gate impossible without violating contracts); C-9 ledger.
- Merge policy: direct to main per family norm; nothing merges with a red gate.
- Out of scope: multi-language leaves, second perf-benchmark target, opencode
  bridge changes, goal-skill changes.

## Telemetry

Default telemetry mode; record packet telemetry per branch; ledger is the
human-readable evidence trail.

## Bundle location

Write the preflight bundle OUTSIDE the three repos (they self-audit docs for
path tokens), e.g. `/home/jakub/projects/goal-bundles/sp11-unattended-dogfood/`.

## Launch sequence

1. goal-config: verify/create + smoke-test the unattended gpt-5.5 + opencode profile.
2. goal-preflight with this brief → bundle → lint → readiness → bootloader text.
3. Launch /goal with the rendered bootloader (goal-main-orchestrator consumes the bundle).
