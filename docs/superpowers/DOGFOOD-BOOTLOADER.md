# Dogfooding Bootloader — paste as the orchestrator agent's goal

Set the block below as the goal of a fresh **Opus** session started **inside
`/home/jakub/projects/repo-audit-skills`**. It is self-bootstrapping: it directs the agent to
read the authoritative orchestrator prompt, plan, and spec already committed in this repo, and
carries the goal, the Phase-0 DAG, the Phase-1 loop, and the Definition of Done inline so a
cold-start agent always has a concrete target.

Full detail:
- `docs/superpowers/DOGFOOD-ORCHESTRATOR-PROMPT.md` (orchestration contract + DAG)
- `docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md` (task-by-task + loop protocol)
- `docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md` (design + decisions)

---

```
You are the ORCHESTRATOR (Opus) for the dogfooding self-improvement run of repo-audit-skills,
working in /home/jakub/projects/repo-audit-skills. You coordinate only: you dispatch OpenCode
DeepSeek v4 Pro workers via the opencode-worker-bridge skill (each in its own git worktree, one
task packet), verify every gate yourself by reading real output, own all merges, and drive the
convergence loop. Cap concurrency at 4.

FIRST: read docs/superpowers/DOGFOOD-ORCHESTRATOR-PROMPT.md and the two sources of truth it
names — docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md and
docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md. Workers implement plan
tasks VERBATIM via TDD (failing test -> confirm fail -> code -> pass -> commit). A worker's "it's
green" is NOT evidence — you re-run the gate and read its JSON.

GOAL: make the package deterministic and hardened (Phase 0), then run a bounded loop that
refactors the package's own code against its own audit until it converges to a fixpoint (Phase 1).

PHASE 0 (fixed DAG — build the safety net; verify each gate before advancing):
- Wave A (parallel, disjoint files): Task 1 (pin tool versions + lockfile jscpd + local-binary
  invocation), Task 3 (guard ast.parse in structure-audit), Task 5 (per-tool idempotence tests),
  Task 6 (segregate test-audit timestamps/runtimes into a meta block), Task 8 (advisory doc).
- Wave B (after Task 1 merges — shares duplication_audit.py): Task 2 (subprocess timeouts).
- Wave C (after Tasks 2+3): Task 4 (adversarial corpus + meta-test: every leaf exits in {0,1,2},
  no traceback).
- Wave D (LAST): Task 7 (self_audit.py + check_self_audit.py, wire check:selfaudit into npm run
  check, FREEZE self_audit_baseline.json from the current snapshot).
PHASE 0 EXIT: npm run check green with FOUR gates incl. check:selfaudit; idempotence + adversarial
+ timeout tests pass; baseline committed. Do not start Phase 1 until this holds.

PHASE 1 (you drive the loop; max 6 rounds):
  1. Run python3 scripts/self_audit.py; read ranked findings.
  2. Select up to 4 top-ranked ACTIONABLE findings. ACTIONABLE = file covered by behavior/golden
     tests (code-health leaves, shared/health_common.py, the umbrella, scripts/ qualify; the
     test-audit scripts do NOT -> frozen). This is the Actionability Rule.
  3. Dispatch one worker per finding to fix it STRUCTURALLY without changing any tool's output
     contract.
  4. ACCEPT only if, in the worktree, npm run check is green AND the affected skill's full pytest
     suite (incl. idempotence/golden) passes AND the tool's findings on its fixtures are
     unchanged. Else discard.
  5. Merge accepted fixes; re-run self_audit.py; ratchet baseline DOWN (cp snapshot -> baseline;
     commit); re-run npm run check (green).
  6. Record net reduction.
FIXPOINT/STOP: converged when a round yields zero accepted reductions with gates green +
idempotence + adversarial clean (freeze baseline final); bounded at 6 rounds; stop on
no-progress/oscillation. Every round ends green and committed.

DEFINITION OF DONE (report with pasted evidence):
1. npm run check green with FOUR gates incl. check:selfaudit; adversarial + idempotence + timeout
   tests pass.
2. All tool versions pinned ==; jscpd lockfiled and invoked from node_modules/.bin.
3. Every leaf exits in {0,1,2} with no traceback on the adversarial corpus; all subprocess.run
   calls carry timeout=.
4. Each code-health leaf + umbrella byte-identical across two runs; test-audit canonical artifact
   carries no wall-clock/timing fields.
5. The loop reached a fixpoint (or the 6-round bound) with a green, committed tree each round;
   final self_audit_baseline.json committed; run report with per-round net reductions and a
   one-line justification for each remaining frozen finding.

CONSTRAINTS: workers implement verbatim and own no merges; you own all merges and loop control;
no tool output contract may change (golden tests enforce it); keep each leaf's health_common.py
byte-identical to shared/health_common.py; never refactor the test-audit scripts (frozen by the
Actionability Rule). Concurrency caps at 4.
```
