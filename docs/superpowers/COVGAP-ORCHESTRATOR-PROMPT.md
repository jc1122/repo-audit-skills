# Orchestrator Prompt — coverage-gap-audit Run (Sub-project 3)

Launch a fresh **Opus** session **inside `/home/jakub/projects/repo-audit-skills`** and paste the
fenced block below. The session is the ORCHESTRATOR: it dispatches **OpenCode DeepSeek v4 Pro
Max** workers (via `opencode-worker-bridge`), verifies every gate itself, then drives the Phase 2
self-refinement loop until the actionable coverage-gap set is empty.

> **The build is mostly a SEQUENTIAL chain** (T1→T2→T3→T4→T5→T7 share files or strict
> dependencies; T1/T5/T7 each touch the self-audit baseline, which must never be edited by two
> workers at once). Only T6 and T8 parallelize. **Phase 2 is the fan-out.**

---

```
GOAL
Add the coverage-gap-audit leaf skill (testedness: coverage.py JSON -> TEST findings) to
repo-audit-skills, gate the repo's own suites + testedness behind a fifth ratcheted check
(check:coverage) that mechanizes the Actionability Rule, run a bounded self-refinement loop that
adds tests for the package's own uncovered production scripts, and prepare release 0.2.0 (no
push). You are the ORCHESTRATOR (Opus): decompose, dispatch workers (own worktree, one task
packet each), verify every gate yourself by reading real output, own all merges and loop
control. Cap concurrency at 4 (mostly moot: the build chain is sequential).

WORKERS (primary + fallback)
- PRIMARY: opencode-worker-bridge -> OpenCode DeepSeek v4 Pro Max. One task packet per worker,
  own git worktree.
- FALLBACK (automatic, one-way, logged): if an OpenCode dispatch fails for infrastructure
  reasons (credits/quota exhausted, auth/billing, bridge unreachable), switch to NATIVE OPUS
  workers for that packet and all later ones: identical packet via your Agent tool (subagent
  model opus, isolated worktree), identical gates, no pause. A credit/dispatch failure switches
  backend; a worker whose CHANGE fails its gates is a normal discard/retry, NOT a switch.

SOURCES OF TRUTH (read first, in full; workers implement plan tasks VERBATIM via TDD)
- Plan:  docs/superpowers/plans/2026-06-10-coverage-gap-audit.md   (authoritative)
- Spec:  docs/superpowers/specs/2026-06-10-coverage-gap-audit-design.md

PRE-FLIGHT (before any dispatch; if any fails, STOP and report)
- git tree clean and in sync; npm run check green (FOUR gates, check:selfaudit 162==162).
- .venv works via `.venv/bin/python -m pytest` (the venv pip/pytest shims have stale shebangs —
  always `python -m ...`); worker-bridge skill loads.
- Env prep for T7: `.venv/bin/python -m pip install coverage==7.14.1 pytest-cov==7.1.0`.

PHASE 1 — BUILD (verify each gate before advancing)
Sequential chain: T1 (TEST signal in shared schema + re-vendor + ratchet) -> T2 (scaffold skill)
  -> T3 (fixtures) -> T4 (leaf via TDD: findings/CLI/relpath/idempotence) -> T5 (register in
  check_release + check_skill_fixtures + installer + README; ratchet) -> T7 (check:coverage
  gate: 8 suites as SEPARATE pytest subprocesses under pytest-cov, combined coverage.json,
  production-scoped leaf run, FREEZE coverage_gap_baseline.json; fifth npm gate).
Parallel lane (disjoint, any time): T6 (self_audit.py argparse + CLI test), T8 (runbook doc).
STANDING RATCHET RULE: every task adding/editing production .py files must leave npm run check
green in the same commit — lint fixed outright, structural findings (module-MI on new
single-file tools is expected) justified-frozen in scripts/self_audit_frozen.md + baseline
ratcheted. T1, T5, T7 (maybe T6) each ratchet — NEVER run two baseline-touching tasks
concurrently.

GATES (you re-run each yourself; a worker's "green" is not evidence):
- After T1: all suites green; check:vendored lists 5 copies byte-identical; selfaudit ratcheted
  (churn = duplication line-range symbols only, no net growth).
- After T4: new skill's suite green (13+ tests) from its own directory.
- After T5: installer --list shows coverage-gap-audit; npm run check green (vendored now lists
  6 copies); selfaudit ratcheted with justified freezes for the new leaf's own findings.
- After T7: npm run check green with FIVE gates; coverage_gap_baseline.json frozen; SANITY: the
  snapshot must NOT contain shared/health_common.py, any code-health leaf script, or the new
  leaf script (they are covered — if present, pytest-cov subprocess tracing is broken: STOP);
  it MUST contain skills/test-*/scripts files (untested by design, rule-frozen).
PHASE 1 EXIT: five green gates; baseline frozen. Do not start Phase 2 until this holds.

PHASE 2 — SELF-REFINEMENT LOOP (you drive; max 4 rounds, cap 4 findings/round)
  1. Run python3 scripts/check_coverage_gap.py; read scripts/coverage_gap_snapshot.json.
  2. ACTIONABLE = entries whose path is NOT under skills/test-*/scripts (those stay rule-frozen
     until Sub-project 4). Expected worklist: scripts/check_release.py,
     scripts/check_skill_fixtures.py, scripts/check_self_audit.py, scripts/self_audit.py,
     possibly scripts/check_coverage_gap.py + scripts/check_vendored_common.py.
  3. One worker per finding (own worktree): EITHER add behavior tests (preferred; root
     tests/test_<name>.py exercising the script's JSON-stdout/exit-code contract, pattern
     tests/test_check_vendored_common.py, until the file clears 50%) OR freeze it (append
     `path :: coverage-gap/file_coverage_percent :: reason` to the Coverage-gap section of
     scripts/self_audit_frozen.md; concrete reason required).
  4. ACCEPT only if, in the worktree: npm run check green (FIVE gates) and the root suite
     passes. Else discard.
  5. Merge accepted; re-run check_coverage_gap.py; ratchet
     (cp scripts/coverage_gap_snapshot.json scripts/coverage_gap_baseline.json); commit
     baseline + frozen log; npm run check green.
  6. Record net change. The snapshot may only SHRINK; growth = STOP and investigate.
STOP: converged (actionable set empty), 4-round bound, or no-progress round.

THEN T9 — RELEASE PREP (LAST): bump package.json + all TEN SKILL.md versions to 0.2.0
atomically; npm run check green (release gate enforces version equality); npm pack --dry-run
includes the new skill, no cache dirs. Commit locally; do NOT push (human reviews, pushes,
publishes, reinstalls).

VALIDATION (you, not workers): after every worker, re-run the relevant gate and read it; never
advance until it passes; if real output diverges from the plan's Expected lines, STOP and
surface.

DEFINITION OF DONE (report with evidence)
1. npm run check green with FIVE gates incl. check:coverage.
2. New skill: suite green, stdlib-only runtime, registered in release/fixtures/installer/README;
   vendored gate lists 6 byte-identical copies; "TEST" in SIGNALS.
3. check:coverage runs all 8 suites (separate processes) under pytest-cov, fails on suite
   failure, ratchets coverage_gap_baseline.json; subprocess tracing verified per the T7 sanity
   check.
4. self_audit.py --help exits 0 fast without side effects (test in root suite).
5. Phase 2 converged or 4-round bound; every freeze concretely justified; baselines ratcheted
   and committed each round.
6. Version 0.2.0 everywhere; pack dry-run clean; NOTHING pushed.
7. Run report: per-task gate evidence, per-round net change, final self-audit + coverage-gap
   baseline counts, all new freeze justifications.

CONSTRAINTS
- Workers implement plan tasks verbatim and own NO merges; you own all merges + loop control.
- No existing tool's output contract may change (golden/idempotence tests enforce it).
- Keep every leaf's scripts/health_common.py byte-identical to shared/health_common.py.
- Never touch tests/fixtures/** of existing skills; never edit skills/test-*/scripts/**.
- The new leaf consumes coverage JSON; it must never run tests itself.
- Prefer ADD-TESTS over FREEZE; every freeze needs a concrete justification.
```

---

## Run at a glance

```
Chain:    T1 schema+TEST -> T2 scaffold -> T3 fixtures -> T4 leaf TDD -> T5 register -> T7 coverage gate (freeze baseline)
Parallel: T6 self_audit argparse | T8 runbook doc
Loop:     Phase 2 (≤4 rounds): gate -> actionable gaps -> add tests | justified freeze -> ratchet -> converge
Last:     T9 release prep 0.2.0 (commit, no push)
```
