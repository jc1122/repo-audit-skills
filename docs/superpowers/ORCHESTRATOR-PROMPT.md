# Orchestrator Prompt — Build code-health-skills via OpenCode workers

Launch a fresh **Opus** session **inside `/home/jakub/projects/code-health-skills`** and
paste the fenced block below. That session acts purely as an orchestrator: it dispatches
**OpenCode DeepSeek v4 Pro** workers to implement plan tasks, running independent work
concurrently and serializing where there are dependencies.

---

```
GOAL
Deliver the standalone `code-health-skills` package: five deterministic, advisory
code-health leaf skills plus the code-health-audit-pipeline umbrella, all green under
`npm run check`, in this repo (/home/jakub/projects/code-health-skills). You are the
ORCHESTRATOR (Opus). You do not write feature code yourself; you decompose the plans,
dispatch workers, verify their output, and integrate it.

WORKERS
Use the `opencode-worker-bridge` skill to launch OpenCode workers running the
DeepSeek v4 Pro model. Each worker gets ONE bounded, file-backed task packet, runs in an
isolated git worktree, and returns a structured status you validate before integrating.
Cap concurrency at 4 workers.

SOURCES OF TRUTH (read first)
- Plans: docs/superpowers/plans/2026-06-10-*.md  (six plans, complete code + TDD steps)
- Spec (context): docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md
- The plans are authoritative and self-contained: exact paths, complete code, exact
  commands, expected output. Workers implement them VERBATIM. No design improvisation.

ENVIRONMENT (do this once before dispatching)
- Ensure the toolchain is installed in the environment workers use:
    python3 -m venv .venv && . .venv/bin/activate
    pip install lizard radon vulture ruff mypy pytest
  Node >= 18 must be available (duplication leaf uses `npx --yes jscpd`; umbrella E2E and
  the release gate need Node). Pre-fetch jscpd once: `npx --yes jscpd --version`.
- Confirm `git log` has the init commit; if empty:
    git add -A && git commit -m "chore: init code-health-skills repo with planning docs"

DEPENDENCY DAG / EXECUTION ORDER
Phase 0 (sequential, blocking) — FOUNDATION:
  Dispatch ONE worker to implement Plan 1 (foundation + complexity-audit), starting at
  Task 2 (Task 1 is already done). Plan 1 establishes shared/health_common.py, the
  installer, and the gate scripts that everything else depends on.
  GATE: `npm run check` must be green and complexity-audit tests pass before Phase 1.

Phase 1 (CONCURRENT, up to 4 workers) — THE FOUR REMAINING LEAVES:
  Plans 2, 3, 4, 5 are mutually independent: each only creates files under its own
  skills/<leaf>/ directory. Dispatch one worker per plan, each in its OWN git worktree
  branched from the post-Phase-0 main.
  IMPORTANT — each leaf worker implements ONLY Tasks 1–4 of its plan (scaffold, fixtures,
  analysis TDD, CLI TDD). It MUST NOT do Task 5 ("Register in package machinery"), because
  Task 5 edits three shared files (bin/install-code-health-skills.js, scripts/check_release.py,
  scripts/check_skill_fixtures.py) that all four plans touch — concurrent edits there
  would collide. The worker commits its leaf per the plan's commit messages and confirms
  `cd skills/<leaf> && python3 -m pytest tests/ -v` passes.

Phase 2 (sequential, you do this) — INTEGRATE LEAVES:
  Merge the four leaf worktree branches into main (paths are disjoint — skills/<leaf>/ —
  so merges are conflict-free). Then YOU centrally apply all four leaves' Task-5
  registrations in one edit each:
   - bin/install-code-health-skills.js: skills[] += the four leaf names
   - scripts/check_release.py: REQUIRED_SKILLS / REQUIRED_SCRIPTS += the four leaves
   - scripts/check_skill_fixtures.py: HELP_COMMANDS += the four leaf --help commands
  (Use the exact lines shown in each plan's Task 5.) Commit, then GATE: `npm run check`
  green with five skills listed.

Phase 3 (sequential, blocking) — UMBRELLA:
  Dispatch ONE worker to implement Plan 6 (code-health-audit-pipeline) in full, including
  its Task 5 registration (by now no other writer is touching the shared files). Merge.
  GATE: `npm run check` green with all six skills; run the Plan 6 Task-5 Step-5 end-to-end
  and confirm exit code 2 (GATE) with the structure cycle.

WORKER PACKET CONTRACT (put this in every packet)
- "Implement <plan path>, Tasks <range>, exactly as written. TDD: for each task write the
  failing test, run it (confirm fail), write the code shown, run it (confirm pass), commit
  with the plan's commit message. Do not alter scope or design."
- "These deviations are INTENTIONAL — implement as the plan says, do not 'fix' them to the
  spec: Plan 2 emits per-pair clone findings; Plan 4 uses stdlib ast+Tarjan not grimp;
  Plan 5 defaults to mypy not ty; Plan 6 derives effort from signal."
- "Advisory-only: never modify a target repo's source. Keep skills/<leaf>/scripts/health_common.py
  byte-identical to shared/health_common.py."
- "Return: tasks completed, the pytest summary lines, and any spot where real tool output
  differed from the plan's Expected lines (stop and report rather than guess)."

VALIDATION BETWEEN PHASES (you, not workers)
- After each worker: read its returned status + run the relevant `pytest` yourself; do not
  trust a worker's claim without seeing green output.
- Never advance a phase until its GATE passes.

DEFINITION OF DONE (report with evidence)
1. All six skills implemented; per-plan pytest suites green (paste summaries).
2. `npm run check` green: vendored-copy + fixtures + release gates pass; check_release
   lists complexity-audit, duplication-audit, dead-code-audit, structure-audit,
   quality-audit, code-health-audit-pipeline.
3. Install round-trip:
     node bin/install-code-health-skills.js --dest /tmp/che-install --force
     python3 /tmp/che-install/code-health-audit-pipeline/scripts/code_health_pipeline.py --help
4. Umbrella end-to-end against skills/structure-audit/tests/fixtures/dirty exits 2 (GATE).
5. Clean linear-ish git history: one focused commit per task; leaf branches merged.

CONSTRAINTS
- Do NOT touch /home/jakub/projects/repo-audit-skills.
- If any worker reports a deviation between a plan's Expected output and real tool output,
  STOP that lane, summarize the discrepancy, and surface it for a plan fix rather than
  papering over it.
```
