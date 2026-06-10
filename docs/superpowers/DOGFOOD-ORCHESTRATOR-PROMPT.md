# Orchestrator Prompt — Dogfooding Self-Improvement Run (Sub-project 2)

Launch a fresh **Opus** session **inside `/home/jakub/projects/repo-audit-skills`** and paste the
fenced block below. The session is the ORCHESTRATOR: it dispatches **OpenCode DeepSeek v4 Pro**
workers (via `opencode-worker-bridge`), runs Phase 0's independent tasks concurrently, verifies
every gate itself, then drives the Phase 1 convergence loop until it reaches a fixpoint.

> **Two parts.** Phase 0 is a fixed task DAG (build the safety net). Phase 1 is a *loop* whose
> work is decided each round by the self-audit output. Phase 0 must be fully green and committed
> before Phase 1 starts.

---

```
GOAL
Make repo-audit-skills deterministic and hardened, then run a bounded convergence loop that
refactors the package's own code against its own audit until it reaches a fixpoint. You are the
ORCHESTRATOR (Opus). You decompose, dispatch OpenCode DeepSeek v4 Pro workers via the
opencode-worker-bridge skill (each in its own git worktree, ONE task packet), verify every gate
yourself by reading real output, and own all merges and the loop control. Cap concurrency at 4.

SOURCES OF TRUTH (read first, in full)
- Plan:  docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md   (authoritative)
- Spec:  docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md
Workers implement plan tasks VERBATIM (TDD: failing test -> confirm fail -> code -> pass ->
commit). No scope changes. The Phase 1 protocol is in the plan's "PHASE 1" section.

ENVIRONMENT (once, before dispatching)
- `. .venv/bin/activate`; node >=18. The pinned tool versions are lizard 1.23.0, radon 6.0.1,
  vulture 2.16, ruff 0.15.5, mypy 2.1.0, jscpd 5.0.5.
- Baseline green: `npm run check` -> three "pass" blocks (selfaudit gate doesn't exist yet).

PHASE 0 — SAFETY NET (fixed DAG; verify each gate before advancing)
File-overlap and dependency facts that set the order:
- Task 1 (pin versions + lockfile jscpd + local-binary invocation) and Task 2 (subprocess
  timeouts) BOTH edit skills/duplication-audit/scripts/duplication_audit.py -> they must NOT run
  concurrently; Task 2 branches off main AFTER Task 1 merges.
- Task 4 (adversarial meta-test) depends on Tasks 2 AND 3 being merged (it asserts no leaf
  tracebacks / clean exit codes, which the timeouts+guards provide).
- Task 7 (self-audit harness + freeze baseline) MUST be last, so the baseline reflects the
  pinned/hardened/deterministic package.

  Wave A (CONCURRENT, up to 4 workers, disjoint files): Task 1, Task 3 (guard ast.parse),
    Task 5 (idempotence tests), Task 6 (test-audit metadata segregation), Task 8 (advisory doc).
    Merge each as it lands (paths disjoint). GATE after the wave: `npm run check` green; each
    touched skill's pytest suite green.
  Wave B (after Wave A merged): Task 2 (timeouts) — branch off the updated main so it includes
    Task 1's duplication edit. Merge. GATE: all five code-health suites + umbrella green;
    `npm run check` green.
  Wave C (after Tasks 2+3 merged): Task 4 (adversarial corpus + meta-test). Merge.
    GATE: `python3 -m pytest tests/test_adversarial_hardening.py -q` green.
  Wave D (LAST): Task 7. The worker writes scripts/self_audit.py + check_self_audit.py, wires
    check:selfaudit into npm run check, and FREEZES scripts/self_audit_baseline.json from the
    current snapshot. Merge. GATE: `npm run check` shows FOUR "pass" blocks, the last
    check:selfaudit with count == baseline.

PHASE 0 EXIT: `npm run check` green with four gates; idempotence + adversarial + timeout tests
pass; baseline committed. Do not start Phase 1 until this holds.

PHASE 1 — CONVERGENCE LOOP (you drive it; see the plan's PHASE 1 protocol)
Repeat bounded rounds (max 6):
  1. Run `python3 scripts/self_audit.py`; read ranked findings from the umbrella summary.
  2. Select up to 4 top-ranked ACTIONABLE findings. ACTIONABLE = the finding's file is covered
     by behavior/golden tests (every code-health leaf, shared/health_common.py, the umbrella,
     and scripts/ qualify; the test-audit scripts do NOT -> those findings are FROZEN, never
     worked). This is the Actionability Rule.
  3. Dispatch one worker per finding (own worktree) to fix it STRUCTURALLY (reduce the flagged
     complexity/duplication/dead-code) WITHOUT changing any tool's output contract.
  4. ACCEPT a worker's change only if, in its worktree: `npm run check` is green AND the affected
     skill's full pytest suite (incl. idempotence/golden) passes AND the tool's findings on its
     fixtures are unchanged. Otherwise discard that worker's branch.
  5. Merge accepted fixes (disjoint files). Re-run scripts/self_audit.py; ratchet the baseline
     DOWN (cp snapshot -> baseline; commit). Re-run `npm run check` -> must be green.
  6. Record the round's net reduction.

FIXPOINT / STOP:
- Converged: a round yields ZERO accepted reductions while gates green + idempotence holds +
  adversarial corpus clean. Freeze the baseline as final.
- Bounded: at most 6 rounds.
- No-progress / oscillation: zero net reduction or a repeated finding set -> STOP and report.
- Every round ends green and committed; the run is safe to stop at any round.

VALIDATION BETWEEN PHASES/ROUNDS (you, not workers)
- After every worker: read its status AND re-run the relevant gate yourself. A worker's "green"
  claim is not evidence.
- Never advance until the gate passes with output you have read.
- If a worker reports real output diverging from the plan's Expected lines, STOP that lane and
  surface it rather than guessing.

DEFINITION OF DONE (report with pasted evidence)
1. `npm run check` green with FOUR gates incl. check:selfaudit; adversarial + idempotence +
   timeout tests pass.
2. All tool versions pinned ==; jscpd lockfiled and invoked from node_modules/.bin.
3. Every leaf exits in {0,1,2} with no traceback on the adversarial corpus; all subprocess.run
   calls carry timeout=.
4. Each code-health leaf + umbrella byte-identical across two runs; test-audit canonical
   artifact carries no wall-clock/timing fields.
5. The loop reached a fixpoint (or the 6-round bound) with a green, committed tree each round;
   final self_audit_baseline.json committed; a run report with per-round net reductions and a
   one-line justification for each remaining frozen finding.

CONSTRAINTS
- Workers implement tasks/fixes verbatim and own NO merges; you own all merges and loop control.
- No tool's output contract may change (golden tests enforce this) — structure-only refactors.
- Keep each code-health leaf's scripts/health_common.py byte-identical to shared/health_common.py
  (the check_vendored_common gate enforces it).
- Do not refactor test-audit scripts (no behavior tests -> frozen by the Actionability Rule).
```

---

## Phase 0 DAG at a glance

```
Wave A (parallel): T1 pin   T3 guard   T5 idempotence   T6 segregate   T8 advisory
                      |
Wave B:            T2 timeouts   (after T1; shares duplication_audit.py)
                      |
Wave C:            T4 adversarial meta-test   (needs T2 + T3)
                      |
Wave D:            T7 self-audit harness + FREEZE baseline   (last)
```

Then Phase 1 loops: self-audit → fix top-4 actionable → gate-green accept → ratchet baseline →
until fixpoint (≤6 rounds).
