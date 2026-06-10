# coverage-gap Bootloader — paste as the orchestrator agent's goal

Set the block below as the goal of a fresh **Opus** session started **inside
`/home/jakub/projects/repo-audit-skills`**. Self-bootstrapping: it directs the agent to read the
authoritative orchestrator prompt, plan, and spec, and carries the goal, the build chain, the
Phase-2 loop, and the DoD inline so a cold-start agent has a concrete target.

Full detail:
- `docs/superpowers/COVGAP-ORCHESTRATOR-PROMPT.md` (orchestration contract + gates)
- `docs/superpowers/plans/2026-06-10-coverage-gap-audit.md` (9 tasks + loop protocol)
- `docs/superpowers/specs/2026-06-10-coverage-gap-audit-design.md` (design + 10 decisions)

---

```
You are the ORCHESTRATOR (Opus) for the coverage-gap-audit run of repo-audit-skills, in
/home/jakub/projects/repo-audit-skills. You coordinate only: dispatch workers (own git worktree,
one task packet each), verify every gate yourself by reading real output, own all merges, drive
the loop. Cap concurrency at 4. Commit locally each task/round; do NOT push (human review).

READ FIRST, then follow as authoritative: docs/superpowers/COVGAP-ORCHESTRATOR-PROMPT.md and the
plan + spec it names (docs/superpowers/plans/2026-06-10-coverage-gap-audit.md,
docs/superpowers/specs/2026-06-10-coverage-gap-audit-design.md). Workers implement plan tasks
VERBATIM via TDD. A worker's "green" is NOT evidence — re-run the gate and read it.

WORKERS: PRIMARY = OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge. FALLBACK (automatic,
one-way, logged) = on infrastructure dispatch failure (credits/quota, auth/billing, bridge
unreachable) switch to NATIVE OPUS workers (Agent tool, model opus, isolated worktree, identical
packet + gates) for that packet and all later ones, without pausing. A gate-failing CHANGE is a
normal discard/retry, NOT a backend switch.

PRE-FLIGHT (before any dispatch; any failure -> STOP and report): git clean + in sync; npm run
check green (FOUR gates, selfaudit 162==162); .venv usable via `.venv/bin/python -m pytest`
(venv pip/pytest shims have stale shebangs — always python -m); worker-bridge skill loads; then
`.venv/bin/python -m pip install coverage==7.14.1 pytest-cov==7.1.0`.

GOAL: add the coverage-gap-audit leaf (testedness: coverage.py JSON -> TEST findings), gate the
repo's suites + testedness behind a fifth ratcheted check (check:coverage) that mechanizes the
Actionability Rule, run a bounded self-refinement loop adding tests for the package's own
uncovered production scripts, prepare release 0.2.0 (no push).

PHASE 1 — BUILD (verify each gate before advancing):
- SEQUENTIAL chain: T1 (add TEST to shared SIGNALS + umbrella EFFORT; re-vendor 5 copies;
  ratchet the duplication symbol churn) -> T2 (scaffold skills/coverage-gap-audit) -> T3
  (frozen fixtures: covered/uncovered trees + handcrafted coverage JSONs) -> T4 (leaf via TDD:
  findings/CLI/relpath/idempotence, stdlib-only, consumes --coverage-json, never runs tests) ->
  T5 (register in check_release + check_skill_fixtures + installer + README; ratchet new leaf's
  own findings with justified freezes) -> T7 (check:coverage gate: run all 8 suites as SEPARATE
  pytest subprocesses from repo root under pytest-cov, combine to one coverage.json, run leaf
  production-scoped, FREEZE scripts/coverage_gap_baseline.json, wire fifth npm gate + release
  required-files; SANITY before freezing: snapshot must NOT contain shared/health_common.py or
  any leaf script (covered) and MUST contain skills/test-*/scripts (untested by design)).
- PARALLEL lane: T6 (self_audit.py argparse so --help stops running a full audit; CLI test),
  T8 (runbook doc).
- STANDING RATCHET RULE: every task adding production .py leaves npm run check green in the
  same commit (lint fixed; structural findings justified-frozen + baseline ratcheted). T1/T5/T7
  each touch the baseline — never two baseline-touching tasks concurrently.
PHASE 1 EXIT: npm run check green with FIVE gates incl. check:coverage; new skill suite green;
installer --list shows it; do not start Phase 2 until so.

PHASE 2 — LOOP (you drive; max 4 rounds, cap 4 findings/round): run
scripts/check_coverage_gap.py; ACTIONABLE = snapshot entries NOT under skills/test-*/scripts
(rule-frozen until Sub-project 4). Per finding a worker EITHER adds behavior tests (preferred;
root tests/test_<name>.py on the script's JSON-stdout/exit-code contract, pattern
tests/test_check_vendored_common.py, to >=50% file coverage) OR freezes it with a concrete
reason in the Coverage-gap section of scripts/self_audit_frozen.md. ACCEPT only if worktree npm
run check is green (FIVE gates) and the root suite passes. Merge; re-run gate; ratchet
(cp snapshot -> baseline); commit. Snapshot may only SHRINK — growth means STOP. CONVERGED when
the actionable set is empty; bounded at 4 rounds; stop on no-progress.

THEN T9 RELEASE PREP (LAST): bump package.json + all TEN SKILL.md to 0.2.0 atomically; npm run
check green; npm pack --dry-run includes the new skill, no cache dirs; commit; do NOT push.

DEFINITION OF DONE (report with evidence): five green gates; new skill registered + suite green
+ stdlib-only; vendored gate lists 6 byte-identical copies; "TEST" in SIGNALS; check:coverage
fails on suite failure and ratchets; subprocess-coverage sanity verified; self_audit --help
fast/clean; loop converged or bounded with every freeze justified; v0.2.0 everywhere; nothing
pushed. Report per-task gate evidence, per-round net change, final baseline counts, freeze list.

CONSTRAINTS: verbatim tasks; you own all merges + loop; no existing tool output contract may
change; keep every leaf's health_common.py byte-identical to shared/health_common.py; never
touch tests/fixtures/** of existing skills; never edit skills/test-*/scripts/**; the leaf never
runs tests; prefer ADD-TESTS over FREEZE.
```
