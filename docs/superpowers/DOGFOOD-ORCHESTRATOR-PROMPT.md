# Orchestrator Prompt — Dogfooding Self-Improvement Run (Sub-project 2, Rev 1)

Launch a fresh **Opus** session **inside `/home/jakub/projects/repo-audit-skills`** and paste the
fenced block below. The session is the ORCHESTRATOR: it dispatches **OpenCode DeepSeek v4 Pro**
workers (via `opencode-worker-bridge`), verifies every gate itself, then drives the Phase 1
convergence loop until the actionable set is empty.

> **Phase 0 is mostly a SEQUENTIAL chain** — the source-editing tasks overlap on the same handful
> of files, so they cannot run concurrently. Only the test-only/disjoint tasks parallelize.
> **Phase 1 is the fan-out** (independent findings in different files).

---

```
GOAL
Make repo-audit-skills deterministic and hardened (Phase 0), then run a bounded loop that
refactors the package's own code against its own audit until the actionable finding set is empty
(Phase 1). You are the ORCHESTRATOR (Opus): decompose, dispatch OpenCode DeepSeek v4 Pro workers
via opencode-worker-bridge (own worktree, one packet each), verify every gate yourself by reading
real output, own all merges and loop control. Cap concurrency at 4.

SOURCES OF TRUTH (read first, in full)
- Plan:  docs/superpowers/plans/2026-06-10-dogfooding-self-improvement.md   (authoritative; Rev 1)
- Spec:  docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md
Workers implement plan tasks VERBATIM (TDD). No scope changes.

ENVIRONMENT (once)
- `. .venv/bin/activate`; node >=18. Pinned versions: lizard 1.23.0, radon 6.0.1, vulture 2.16,
  ruff 0.15.5, mypy 2.1.0, jscpd 5.0.5. Baseline green: `npm run check` -> three "pass".

PHASE 0 — SAFETY NET
Source chain (SEQUENTIAL — these tasks edit overlapping files; one lane, in order):
  Task 1 (pin versions + lockfile jscpd + local binary)
    -> Task 2 (subprocess timeouts; shares duplication_audit.py with T1)
    -> Task 3 (guard ast.parse in structure-audit)
    -> Task 4 (normalize finding paths to relative; shares quality/dead-code with T2)
    -> Task 8 (bulk ruff --fix + format on production scripts; re-vendor health_common; reformats
       the files all earlier tasks touched, so it goes LAST in the chain)
Parallel lane (disjoint; run alongside the chain, merge when their dependency is met):
  Task 7 (segregate test-audit timestamps/runtimes — only touches test-audit-pipeline)
  Task 10 (advisory doc — docs only)
  Task 5 (adversarial corpus + meta-test — needs Tasks 2+3 merged)
  Task 6 (per-tool idempotence tests — needs Task 4 merged; new test files only)
Then LAST:
  Task 9 (self-audit harness + ratchet gate; production-scoped via explicit per-skill scripts
    prefixes; FREEZE scripts/self_audit_baseline.json from the post-bulk snapshot). Must run after
    EVERYTHING above (baseline must reflect the pinned/normalized/hardened/bulk-remediated package).

GATES (you re-run each yourself; a worker's "green" is not evidence):
- After each chain task: that skill's pytest suite + `npm run check` green.
- After Task 4: `quality`/`dead-code` relpath tests pass (no absolute paths).
- After Task 5: tests/test_adversarial_hardening.py green.
- After Task 6: all six idempotence tests green.
- After Task 8: EVERY suite + idempotence/golden green (proves reformat changed no output contract).
- After Task 9: `npm run check` shows FOUR "pass", last check:selfaudit count == baseline, and
  the snapshot has NO /tests/ paths and NO absolute paths.

PHASE 0 EXIT: four green gates; baseline frozen post-bulk. Do not start Phase 1 until this holds.

PHASE 1 — CONVERGENCE LOOP (you drive it; max 8 rounds)
  1. Run `python3 scripts/self_audit.py`; read ranked findings.
  2. Select up to 8 top-ranked ACTIONABLE findings. ACTIONABLE = file covered by behavior/golden
     tests (code-health leaves, shared/health_common.py, the umbrella, scripts/ qualify; the
     test-audit scripts do NOT -> freeze). Actionability Rule.
  3. One worker per finding (own worktree). The worker EITHER fixes it STRUCTURALLY (no
     output-contract change) OR FREEZES it by appending `path :: leaf/metric :: reason` to
     scripts/self_audit_frozen.md (concrete reason required; prefer FIX).
  4. ACCEPT only if, in the worktree: `npm run check` green AND the affected skill's full pytest
     suite (incl. idempotence/golden) passes AND the tool's fixture findings are unchanged. Else
     discard that worker's branch.
  5. Merge accepted results; re-run scripts/self_audit.py; ratchet baseline
     (cp snapshot -> baseline); commit baseline + frozen log; re-run `npm run check` -> green.
  6. Record net change (fixed + frozen).

FIXPOINT / STOP:
- Converged: actionable set empty (every finding fixed or justified-frozen).
- Bounded: at most 8 rounds.
- No-progress / oscillation: a round that neither fixes nor freezes anything, or a repeated
  finding set -> STOP and report.
- Every round ends green and committed.

VALIDATION (you, not workers): after every worker, re-run the relevant gate and read it; never
advance until it passes; if real output diverges from the plan's Expected lines, STOP and surface.

DEFINITION OF DONE (report with evidence)
1. `npm run check` green, FOUR gates incl. check:selfaudit; adversarial + idempotence + timeout +
   relpath tests pass.
2. Versions pinned ==; jscpd lockfiled from node_modules/.bin; every leaf emits only paths
   relative to --root.
3. Every leaf exits in {0,1,2} no traceback on the adversarial corpus; all subprocess.run carry
   timeout=.
4. Each code-health leaf + umbrella byte-identical across two runs; test-audit canonical artifact
   free of wall-clock/timing; self_audit.py reports no /tests/ paths.
5. Loop reached an empty actionable set (or 8-round bound), green + committed each round; final
   self_audit_baseline.json + self_audit_frozen.md committed; run report with per-round net change.

CONSTRAINTS
- Workers implement verbatim and own NO merges; you own all merges and loop control.
- No tool output contract may change (golden tests enforce it) — structure-only refactors.
- Keep each leaf's scripts/health_common.py byte-identical to shared/health_common.py.
- Never touch tests/fixtures/** (deliberately dirty). Never refactor the test-audit scripts.
- Prefer FIX over FREEZE; every freeze needs a concrete justification in self_audit_frozen.md.
```

---

## Phase 0 at a glance

```
SEQUENTIAL chain:  T1 pin -> T2 timeouts -> T3 guard -> T4 relpaths -> T8 bulk ruff fix/format
Parallel/disjoint: T7 test-audit meta-segregate | T10 advisory | T5 adversarial(after 2,3) | T6 idempotence(after 4)
LAST:              T9 self-audit harness + FREEZE baseline (production-scoped)
```
Then Phase 1 loops: self-audit -> top-8 actionable -> per finding FIX or justified-FREEZE ->
gate-green accept -> ratchet baseline -> until the actionable set is empty (≤8 rounds).
