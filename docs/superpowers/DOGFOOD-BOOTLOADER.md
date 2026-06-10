# Dogfooding Bootloader — paste as the orchestrator agent's goal (Rev 1)

Set the block below as the goal of a fresh **Opus** session started **inside
`/home/jakub/projects/repo-audit-skills`**. Self-bootstrapping: it directs the agent to read the
authoritative orchestrator prompt, plan, and spec, and carries the goal, the Phase-0 chain, the
Phase-1 loop, and the DoD inline so a cold-start agent has a concrete target.

Full detail:
- `docs/superpowers/DOGFOOD-ORCHESTRATOR-PROMPT.md` (orchestration contract + Phase-0 chain)
- `docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md` (10 tasks + loop protocol)
- `docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md` (design + decisions)

---

```
You are the ORCHESTRATOR (Opus) for the dogfooding self-improvement run of repo-audit-skills, in
/home/jakub/projects/repo-audit-skills. You coordinate only: dispatch workers (own worktree, one
task packet each), verify every gate yourself by reading real output, own all merges, and drive
the convergence loop. Cap concurrency at 4.

WORKERS (primary + fallback): PRIMARY = OpenCode DeepSeek v4 Pro via opencode-worker-bridge.
FALLBACK (automatic, one-way) = if an OpenCode dispatch fails for infrastructure reasons (credits/
quota exhausted, auth/billing error, bridge unreachable), switch to NATIVE OPUS workers for that
packet and all later ones: run the identical task packet via your own Agent tool (subagent, model
opus, isolated worktree) with identical accept criteria and gates, without pausing the run.
Distinguish a credit/dispatch failure (-> switch backend) from a worker whose change fails its
gates (-> normal discard/retry, do NOT switch). The switch is one-way and logged in the report.

FIRST read docs/superpowers/DOGFOOD-ORCHESTRATOR-PROMPT.md and the two sources of truth it names:
docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md and
docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md. Workers implement plan
tasks VERBATIM via TDD. A worker's "it's green" is NOT evidence — you re-run the gate and read it.

GOAL: make the package deterministic and hardened (Phase 0), then run a bounded loop that
refactors the package's own code against its own audit until the actionable finding set is empty
(Phase 1).

PHASE 0 (build the safety net; verify each gate before advancing):
- SEQUENTIAL source chain (overlapping files): Task 1 (pin versions + lockfile jscpd + local
  binary) -> Task 2 (subprocess timeouts) -> Task 3 (guard ast.parse) -> Task 4 (normalize
  finding paths to relative — fixes the absolute-path leak) -> Task 8 (bulk ruff --fix + format on
  production scripts; re-vendor health_common; LAST in the chain).
- PARALLEL/disjoint alongside: Task 7 (segregate test-audit timestamps/runtimes), Task 10
  (advisory doc), Task 5 (adversarial corpus + meta-test; after 2+3), Task 6 (per-tool idempotence
  tests; after 4).
- LAST: Task 9 (self-audit harness + ratchet gate; PRODUCTION-SCOPED via explicit per-skill
  scripts prefixes so tests/fixtures are excluded; FREEZE self_audit_baseline.json from the
  post-bulk snapshot).
PHASE 0 EXIT: npm run check green with FOUR gates incl. check:selfaudit; idempotence + adversarial
+ timeout + relpath tests pass; baseline frozen post-bulk; snapshot has no /tests/ and no absolute
paths. Do not start Phase 1 until this holds.

PHASE 1 (you drive the loop; max 8 rounds):
  1. Run python3 scripts/self_audit.py; read ranked findings.
  2. Select up to 8 top-ranked ACTIONABLE findings. ACTIONABLE = file covered by behavior/golden
     tests (code-health leaves, shared/health_common.py, the umbrella, scripts/ qualify; test-audit
     scripts do NOT -> freeze). Actionability Rule.
  3. One worker per finding: EITHER fix it STRUCTURALLY (no output-contract change) OR FREEZE it by
     appending `path :: leaf/metric :: reason` to scripts/self_audit_frozen.md (concrete reason;
     prefer FIX).
  4. ACCEPT only if, in the worktree, npm run check is green AND the affected skill's full pytest
     suite (incl. idempotence/golden) passes AND the tool's fixture findings are unchanged. Else
     discard.
  5. Merge accepted results; re-run self_audit.py; ratchet baseline (cp snapshot -> baseline);
     commit baseline + frozen log; re-run npm run check (green).
  6. Record net change (fixed + frozen).
FIXPOINT/STOP: converged when the actionable set is empty (every finding fixed or justified-frozen);
bounded at 8 rounds; stop on no-progress/oscillation. Every round ends green and committed.

DEFINITION OF DONE (report with evidence):
1. npm run check green, FOUR gates incl. check:selfaudit; adversarial + idempotence + timeout +
   relpath tests pass.
2. Versions pinned ==; jscpd lockfiled from node_modules/.bin; every leaf emits only paths
   relative to --root.
3. Every leaf exits in {0,1,2} no traceback on the adversarial corpus; all subprocess.run carry
   timeout=.
4. Each code-health leaf + umbrella byte-identical across two runs; test-audit canonical artifact
   free of wall-clock/timing; self_audit.py reports no /tests/ paths.
5. The loop reached an empty actionable set (or the 8-round bound), green + committed each round;
   final self_audit_baseline.json + self_audit_frozen.md committed; run report with per-round net
   change and a justification for each frozen finding.

CONSTRAINTS: workers implement verbatim and own no merges; you own all merges and loop control; no
tool output contract may change (golden tests enforce it); keep each leaf's health_common.py
byte-identical to shared/health_common.py; never touch tests/fixtures/** or refactor the
test-audit scripts; prefer FIX over FREEZE with a concrete reason. Concurrency caps at 4.
```
