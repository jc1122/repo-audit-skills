# SP13 ledger — runtime self-improvement loop (combined SP12 continuation)

Single authority: `docs/superpowers/plans/2026-06-13-sp13-runtime-self-improvement-loop.md`.
Orchestrator: one Claude Opus 4.8 session, unattended, worker-only hands (L-3).
Appended once per phase/iteration per L-10.

## Entry verification (2026-06-13)

Re-verified the continuation entry state (plan "Lineage and entry state"):

| Repo | main @ entry | CI | Open rows (residue, SP12 ledger truth) |
| --- | --- | --- | ---: |
| repo-A `repo-audit-skills` | `492c23c` → fixed to `eafa1c7` | was RED (growth), now GREEN | 260 |
| repo-B `repo-audit-refactor-optimize` | `e3adf81` | GREEN | 13 |
| repo-P `perf-benchmark-skill` | `ac58303` | GREEN | 25 |
| total | | | **298** |

- No live SP12 worker; no `/tmp/sp12` or `/tmp/sp13` worktrees at entry.
- **Entry blocker found + fixed:** repo-A `main` was CI-RED — the growth gate failed
  (count 3) because the SP13 bootstrap docs (SP12 ledger closeout +411, SP13 plan
  +216, SP13 launch prompt +133 = +760 docs) plus 2 new tracked files exceeded the
  stale SP12 allowances (docs 376 / net 368 / no tracked_files entry). Fix (commit
  `eafa1c7`): finalized the operator launch prompt to its condensed form and
  refreshed the release-expiring growth allowances (tracked_files 2, docs 740,
  net 760) with reasoned SP13-bootstrap entries. Full check 9/9 cheap + 2/2 heavy,
  0 failed; pushed; CI GREEN.
- **Bootstrap probe: GREEN** (installed 8-lane wave bootstraps and emits findings
  across code-health/security/hygiene/docs/dependency/hotspot/exec lanes) BUT it
  **TIMED OUT at the 300s budget** before the growth lane — the repo-A 220-test
  triage suite (the wall-clock floor) is the prime suspect. Logged as the first
  self-application target (X1.3 → `test-redundancy-triage`).

## X0 — telemetry + memory keystone (SHIPPED)

Worker route: native Opus subagents in `/tmp/sp13` git worktrees, file-backed L-7
packets, re-verified by the orchestrator (worker green never trusted).

- **X0.1 KPI miner** (repo-B `scripts/mine_iteration_kpis.py` + test): `compute_kpi`
  (rows_closed/rows_per_hour/repair_rate, derived) + `is_regression` (only
  rows_per_hour −20% / repair_rate +50%; ci_wait never trips it — R5) + `main()`
  that DERIVES inputs from git timestamps, baseline JSONs, run-dir repairs, CI API
  (mined, never typed). Re-verified: 2 passed, full repo-B suite 144→ green.
- **X0.2 lessons ledger + injection** (repo-B `scripts/synthesize_packets.py`
  `inject_lessons`+`needs_automation`, + test): scope-matched binding-only capped
  injection; `needs_automation = binding & fires>=3 & !escalated`. Re-verified:
  2 passed, synthesizer 18 passed (no regression).
- Merged both to repo-B `main` `e937a4d`, fresh-clone sim green (146 passed),
  pushed, **CI GREEN**. No release/reinstall — X0 is orchestration tooling, not
  leaf diagnosis behavior (L-6).
- **X0.3 repo-A landing** (commit `e8831ce`, pushed, CI GREEN):
  - `docs/self-audit/lessons.jsonl`: 7 binding SP9–SP12 lessons (L1 npm-ci,
    L2 changelog-date, L3 fresh-clone, L4 grep-JSON-not-exit-codes, L5 line-pinned
    dup rows, L6 vendored byte-identical, L7 --rev anchor). Per-run `fires` start
    at 0 (honest R7 counter); `historical_fires` records provenance.
  - **R7 escalation proven:** L1 → `scripts/worker_worktree_setup.sh` (committed),
    L6 → existing `scripts/check_vendored_common.py`; both marked `escalated:true`.
    Satisfies DoD #2 (≥1 lesson reached automation-escalation).
  - `scripts/iteration_kpis.jsonl`: empty append-only telemetry evidence.
  - Growth allowance refreshed for the pre-allowanced X0 files (tracked_files 5,
    docs 747, net 780; release-expiring).
- **Injection smoke (DoD #2 path):** shipped `inject_lessons` against the seeded
  ledger returns the correct scope-matched lesson per scope
  (worktree-setup→L1, release→L2, duplication→L5, gates→L4) and `needs_automation`
  correctly flags an unescalated fires≥3 lesson.

## X1 / X2 — self-application + adaptive control (IN PROGRESS)

- **X2.1 allocator** (repo-B `scripts/allocate_batches.py` + test): `allocate`
  (guaranteed ≥1/active repo + surplus to best trailing per-repo yield, cap 6) +
  `rationale` (one-line, cites mined yield). Re-verified 5 passed, full 151 passed;
  merged to repo-B `main` `c8d0945` (local, bundling into X3 ship).
- **X2.2 amendment protocol**: `docs/superpowers/amendment-proposals/TEMPLATE.md`
  written (L-8 schema). 0 proposals so far (max 3/run).
- **X1.3 self-application checklist**: `docs/self-audit/self-application-checklist.md`
  written; matrix of {family skill × applied-to-family}; FIRST target
  `test-redundancy-triage` on repo-A's 220-test suite (motivated by the probe
  timeout).
- **X1.1 instruction-lint** (repo-A `scripts/check_instruction_lint.py` gate): DISPATCHED.
  Design deviation logged: implemented as a STANDALONE gate (the plan's explicit
  "OR" option) rather than extending the docs-consistency-audit leaf — avoids a
  leaf-behavior change/reinstall and a baseline-0 collision in the docs lane; carries
  its own baseline so its meta-findings join the frozen universe at X3. Sunset: fold
  into docs-consistency-audit once stable (R2).
- **X1.2 behavioral eval** (repo-B `scripts/run_instruction_eval.py`): DISPATCHED.
  Advisory, pinned-model, drift→candidate lesson + advisory finding (never a gate).
