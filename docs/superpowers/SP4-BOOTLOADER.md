# SP4 Bootloader — Skillset-Completion Run — paste as the orchestrator agent's goal

Set the block below as the goal of a fresh **Opus** session started **inside
`/home/jakub/projects/repo-audit-skills`**. Self-contained: unlike SP3 there is no pre-written
plan/spec — T0 directs the orchestrator to derive and commit them from this goal before any
dispatch, so workers still implement plan tasks verbatim.

This is the **final completion run**: after it converges, every skill in the package is tested,
every gate is mechanized, no finding class is rule-frozen, and future dogfooding runs are pure
maintenance burn-down.

Context (verified by the 2026-06-10 post-SP3 audit):
- v0.2.0 committed (23fef02), NOT pushed; all FIVE gates green (selfaudit 168==168, coverage 5==5, 8 suites).
- 126/168 self-audit findings + 3/5 coverage entries are rule-frozen ONLY because the three
  test-audit skills ship no tests: `triage_redundancy.py` (84), `audit_test_quality.py` (28),
  `audit_pipeline.py` (14). Mix: 65 lint (E501 50, B023 10, SIM 5), 52 complexity
  (nloc 20, CC 18, params 14), 6 duplication, 3 module-MI.
- No `.github/workflows/`; root `pytest --collect-only` has 13 module-name-collision errors;
  umbrella `leaf_registry.json` lacks coverage-gap-audit (spec SP3 decision 4, deferred to v2).

---

```
You are the ORCHESTRATOR (Opus) for the SP4 skillset-completion run of repo-audit-skills, in
/home/jakub/projects/repo-audit-skills. You coordinate only: dispatch workers (own git worktree,
one task packet each), verify every gate yourself by reading real output, own all merges, drive
the loop. Cap concurrency at 4. Commit locally each task/round; do NOT push (human review).

WORKERS: PRIMARY = OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge. FALLBACK (automatic,
one-way, logged) = on infrastructure dispatch failure (credits/quota, auth/billing, bridge
unreachable) switch to NATIVE OPUS workers (Agent tool, model opus, isolated worktree, identical
packet + gates) for that packet and all later ones, without pausing. A gate-failing CHANGE is a
normal discard/retry, NOT a backend switch.

PRE-FLIGHT (any failure -> STOP and report): git clean + tree at v0.2.0 (23fef02 or later); npm
run check green (FIVE gates: selfaudit 168==168, coverage 5==5 across 8 suites); .venv usable
via `.venv/bin/python -m pytest` (venv pip/pytest shims have stale shebangs — ALWAYS python -m);
worker-bridge skill loads.

GOAL: make the skillset self-covering and unfreeze everything that is frozen for missing tests.
Concretely: (1) behavior/golden tests for the three test-audit skills, written BEFORE any edit
to their scripts, so their output contracts are frozen first; (2) gate those suites under
check:coverage; (3) burn down the 126 rule-frozen self-audit findings under test protection
until zero rule-frozen entries remain (every residual freeze individually justified); (4) CI
workflow running npm run check; (5) root pytest collection fixed; (6) umbrella v2: register
coverage-gap-audit as an artifact-gated leaf. Release prep 0.3.0 (commit, no push).

T0 — PLAN FIRST (you, no worker): expand this goal into
docs/superpowers/plans/<date>-sp4-skillset-completion.md (one section per task below, with
files, steps, Expected gate output) and a short spec recording the decisions (test-first
ordering; artifact-gated umbrella leaf; rule-freeze retirement). Commit both before any
dispatch. Workers implement plan tasks VERBATIM via TDD. A worker's "green" is NOT evidence —
re-run the gate and read it.

PHASE 1 — BUILD (verify each gate before advancing):
- T1 root collection fix: make `.venv/bin/python -m pytest --collect-only -q` exit clean from
  repo root (per-directory conftest.py or rootdir/ini config; do NOT rename existing test
  files of other skills). All existing suites still pass from their own directories;
  check:coverage output unchanged.
- T2 CI workflow: .github/workflows/check.yml — checkout, setup Node + Python, install pinned
  test deps (coverage==7.14.1 pytest-cov==7.1.0 + the pinned audit tools the gates invoke),
  npm ci or install, npm run check. Static validation only (actionlint/yamllint if available,
  else careful read): CI cannot run before the human pushes — record that explicitly in the
  run report. Do NOT weaken any gate to make it CI-friendly.
- T3a/T3b/T3c (parallel, disjoint dirs, no baseline ratchet): behavior/golden test suites for
  test-quality-assurance, test-redundancy-triage, test-audit-pipeline (extend its meta test).
  TESTS ONLY — zero edits to skills/test-*/scripts/** in Phase 1; tests characterize CURRENT
  behavior. Pattern = existing leaf suites: frozen fixtures under the skill's tests/fixtures/,
  golden findings JSON, CLI/exit-code contract, relpath, idempotence (byte-identical across
  runs). PITFALL (SP3 R1 evidence): subprocess CLI tests are NOT traced by pytest-cov in this
  config — coverage-clearing tests must import the module and exercise it in-process; keep at
  most a thin smoke test via subprocess. Target >=50% file coverage per script. Gate: each new
  suite green from its own directory.
- T4 gate the new suites (baseline-touching): add the three suites to check_coverage_gap.py's
  suite list (8 -> 11, still SEPARATE pytest subprocesses), re-run, verify the three
  skills/test-*/scripts entries CLEAR from the snapshot (if any stays <50%, return it to T3 as
  a discard/retry — do not freeze it), ratchet coverage_gap_baseline.json (expect 5 -> 2),
  update the runbook doc. npm run check green.
- T5 umbrella v2 (baseline-touching if self-audit churns): leaf_registry.json entries gain an
  optional "requires" field (e.g. {"coverage_json": true}); register coverage-gap-audit;
  code_health_pipeline.py skips requires-unsatisfied leaves with an explicit "skipped" record
  and runs them when --coverage-json is passed through. ADDITIVE: existing no-artifact umbrella
  output stays byte-identical (golden test proves it); new behavior gets its own golden test.
  Keep every leaf's scripts/health_common.py byte-identical to shared/health_common.py.
- STANDING RATCHET RULE (unchanged from SP3): every task adding/editing production .py leaves
  npm run check green in the same commit; lint fixed outright; structural findings
  justified-frozen in scripts/self_audit_frozen.md + baseline ratcheted. NEVER run two
  baseline-touching tasks (T4, T5, every Phase 2 merge) concurrently.
PHASE 1 EXIT: npm run check green; check:coverage = 11 suites, baseline 2 (only the two
justified scripts/ freezes); root collection clean; CI workflow committed; do not start
Phase 2 until so.

PHASE 2 — UNFREEZE + BURN-DOWN (you drive; max 6 rounds; snapshot may only SHRINK):
  0. Retire the rule-freeze: delete the Actionability-Rule blanket entry for skills/test-*/
     from scripts/self_audit_frozen.md. The 126 findings are now ACTIONABLE, protected by the
     T3 suites.
  1. Round order (one worker per file-batch, own worktree):
     R1 mechanical lint — E501 + SIM102/SIM108 in bulk per file (~55 findings).
     R2 B023 — function-defined-in-loop late-binding (10): these are REAL bug-risk fixes;
        if a fix changes observable output, the golden test catches it — investigate, never
        regenerate a golden to make a fix pass without explaining the behavior change.
     R3+ complexity/duplication/MI (~61): decompose ONLY where it nets a real reduction
        without churning clone detection; otherwise justified-freeze per the established
        idioms (single-file-tool module-MI; cohesive tool logic; cross-leaf dedup forbidden
        per R2 evidence). Prefer FIX over FREEZE; every freeze needs a concrete per-finding
        reason.
  2. ACCEPT a worker only if, in its worktree: npm run check green (all gates) and the three
     test-* suites pass. Else discard/retry.
  3. Merge; re-run self_audit; ratchet baseline; commit baseline + frozen log each round.
  4. Growth = STOP and investigate. CONVERGED when the actionable set is empty and ZERO
     rule-frozen (blanket) entries remain anywhere — every residual freeze is individual and
     justified. Bounded at 6 rounds; stop on a no-progress round.

THEN T-LAST RELEASE PREP: bump package.json + all TEN SKILL.md to 0.3.0 atomically; npm run
check green; npm pack --dry-run includes .github/workflows nowhere (it is repo CI, not package
content) and no cache dirs; commit; do NOT push.

DEFINITION OF DONE (report with evidence):
1. npm run check green; check:coverage runs 11 suites; root pytest --collect-only exits clean.
2. All three test-audit skills ship green behavior/golden suites; their scripts >=50% covered;
   coverage baseline = 2 justified entries, zero rule-frozen.
3. Self-audit baseline strictly below 168 with ZERO blanket/rule freezes — report the final
   count, per-round net change, and every new freeze justification (expect final well under
   100: ~65 lint fixed, B023 fixed, complexity split fix/freeze).
4. CI workflow committed and statically validated; report states post-push verification is on
   the human.
5. Umbrella v2: coverage-gap-audit registered artifact-gated; no-artifact output byte-identical
   (golden); artifact path has its own golden.
6. v0.3.0 everywhere; pack dry-run clean; NOTHING pushed (human reviews, pushes, publishes,
   verifies CI, reinstalls).
7. Run report: per-task gate evidence, per-round burn-down table, final baseline counts.

CONSTRAINTS: T0 plan tasks are verbatim for workers; you own all merges + loop control; no
existing tool's output contract may change (goldens enforce; T3 goldens land BEFORE any
test-*/scripts edit); never touch tests/fixtures/** of OTHER skills; keep vendored
health_common byte-identical everywhere; prefer FIX over FREEZE; never two baseline-touching
merges concurrently; ALWAYS .venv/bin/python -m for pip/pytest.
```

---

## Run at a glance

```
T0:       orchestrator writes + commits plan/spec from this goal
Phase 1:  T1 collection fix | T2 CI workflow | T3a/b/c golden tests for test-* (parallel, tests only)
          -> T4 gate 11 suites + ratchet coverage (5->2) -> T5 umbrella v2 (artifact-gated leaf)
Phase 2:  retire rule-freeze -> R1 bulk lint -> R2 B023 -> R3+ decompose-or-justify
          (<=6 rounds, ratchet each, zero blanket freezes at exit)
Last:     release prep 0.3.0 (commit, no push)
After:    skillset complete — all 10 skills tested, 6 gates incl. CI, loop self-covering
```
