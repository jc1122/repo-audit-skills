# Orchestrator Prompt — Integrate the test-audit pipeline into `repo-audit-skills`

Launch a fresh **Opus** session **inside `/home/jakub/projects/code-health-skills`** and paste
the fenced block below. That session is the ORCHESTRATOR: it dispatches **OpenCode DeepSeek v4
Pro** workers (via the `opencode-worker-bridge` skill) to implement plan tasks, runs the two
independent tasks concurrently, verifies every gate itself, and personally handles the one
irreversible phase with a human in the loop.

> **Reality check on concurrency.** This is a migration, not a feature fan-out. The dependency
> graph is mostly a chain: only **Task 1 (copy)** and **Task 2 (rename)** are independent and
> run in parallel; **Task 3 (register)** depends on both; **Task 4 (takeover)** is irreversible
> and is NOT delegated. Do not invent further parallelism — the remaining tasks edit the same
> shared files (`package.json`, `bin/install-*.js`, `scripts/check_release.py`,
> `scripts/check_skill_fixtures.py`, `README.md`) and concurrent edits there would collide.

---

```
GOAL
Integrate the three test-audit skills into this package, rename the package to
`repo-audit-skills`, and take over its directory + GitHub identity, ending with
`npm run check` green at NINE skills. You are the ORCHESTRATOR (Opus). You decompose the
plan into worker packets, dispatch workers, verify their output against real gate output,
integrate their branches, and personally perform the irreversible final phase with explicit
human confirmation. You do not hand-wave a gate as "probably green" — you run it and read it.

SOURCES OF TRUTH (read first, in full)
- Plan:  docs/superpowers/plans/2026-06-10-integrate-test-audit-pipeline.md
- Spec:  docs/superpowers/specs/2026-06-10-integrate-test-audit-pipeline-design.md
The plan is authoritative and self-contained: exact file paths, exact edits, exact commands,
expected output. Workers implement tasks VERBATIM. No design improvisation, no scope changes.

WORKERS
Use the `opencode-worker-bridge` skill to launch OpenCode workers running DeepSeek v4 Pro.
Each worker gets ONE bounded, file-backed task packet, works in an isolated git worktree
branched from the current `main`/`master` tip, and returns a structured status you validate
before merging. This plan needs at most 2 concurrent workers.

ENVIRONMENT (verify once before dispatching)
- Node >= 18 on PATH (installer, release gate). Python 3 on PATH (gate scripts, --help smokes).
- The three migrated skills need NO extra Python deps for this work (only `--help` + a path
  resolution are exercised; the full pipeline is out of scope). Do NOT add pyproject/deps.
- The source skills live at:
    /home/jakub/projects/repo-audit-skills/skills/{test-audit-pipeline,
      test-quality-assurance,test-redundancy-triage}
  Confirm that path exists and is readable before Phase 1.
- Confirm the package is green at baseline: `npm run check` -> three "pass" blocks, six skills.

DEPENDENCY DAG / EXECUTION ORDER

  Phase 1 (CONCURRENT, 2 workers) ─────────────────────────────────────────────
    Worker A  = Plan Task 1  "Copy the three test-audit skill directories in"
    Worker B  = Plan Task 2  "Rename the package identity to repo-audit-skills"
    These touch DISJOINT files (A creates skills/<3 dirs>/**; B edits package.json,
    git-mv's the installer, edits check_release.py + README.md), so they run in parallel
    in separate worktrees off the same base commit.
    Each worker performs ALL steps of its task, including the task's own `npm run check`
    verification and the per-task commit message in the plan.

  Phase 2 (SEQUENTIAL, you) ───────────────────────────────────────────────────
    Merge Worker A's branch and Worker B's branch into main. Paths are disjoint so the
    merge is conflict-free; if git reports ANY conflict, STOP and inspect — it means a
    worker strayed outside its task's file set.
    GATE: run `npm run check`. Expect three "pass" blocks, name asserted as
    `repo-audit-skills`, and `check:release` still listing the SIX original skills (the
    copied dirs are present but not yet registered). Also confirm the three new skill dirs
    exist on disk. Do not advance until this gate is green.

  Phase 3 (SEQUENTIAL, 1 worker) ──────────────────────────────────────────────
    Worker C = Plan Task 3  "Register the three migrated skills in the gates".
    It edits the renamed installer's skills[], check_release.py REQUIRED_SKILLS/SCRIPTS,
    check_skill_fixtures.py HELP_COMMANDS, and README.md, then runs the Step 5 gate and the
    Step 6 functional smoke (install round-trip + sibling-discovery), and commits.
    Merge its branch.
    GATE (you re-run, do not trust the worker): `npm run check` green with NINE skills
    listed; `node bin/install-repo-audit-skills.js --dest /tmp/ras-install --force` installs
    nine; the sibling-discovery snippet prints "SIBLING DISCOVERY OK".

  Phase 4 (SEQUENTIAL, YOU — IRREVERSIBLE, HUMAN-CONFIRMED) ────────────────────
    DO NOT delegate this to a worker. Execute Plan Task 4 yourself, and PAUSE for explicit
    user confirmation before each irreversible action (Steps 5, 7, 8 of the plan):
      - force-push over github.com/jc1122/repo-audit-skills (overwrites the placeholder,
        abandons perf-benchmark + repo-audit-refactor-optimize),
      - rm -rf the old local /home/jakub/projects/repo-audit-skills,
      - mv code-health-skills -> repo-audit-skills.
    Run everything with absolute paths from /home/jakub/projects so a reset shell cwd cannot
    point inside a directory being moved/removed. Then run the plan's Step 9 final
    verification from the renamed directory.

WORKER PACKET CONTRACT (put this in every packet)
- "Implement <plan path>, Task <N>, exactly as written. Do each `- [ ]` step in order; run
  the verification commands shown and confirm the Expected output; commit with the task's
  commit message. Do not alter scope, rename anything not named in the task, or edit files
  outside this task's file set."
- "LIFT-AND-SHIFT: never modify the internals of the migrated skills (their scripts,
  SKILL.md, references, agents). They move byte-for-byte. Do not add tests or pyproject."
- "Do NOT touch shared/health_common.py or any existing code-health leaf. Do NOT run any
  git push, remote, branch -m, rm -rf, or directory move — those are Phase 4 and belong to
  the orchestrator."
- "Return: the task number, the exact `npm run check` summary you saw, the `find`/`--help`
  outputs the task asks for, and any spot where real output differed from the plan's
  Expected lines (STOP and report rather than guessing)."

VALIDATION BETWEEN PHASES (you, not workers)
- After every worker: read its returned status AND re-run the relevant gate yourself. A
  worker's "it's green" claim is not evidence; the gate's JSON output is.
- Never advance a phase until its GATE passes with output you have read.
- If a worker reports a discrepancy between the plan's Expected output and reality, STOP that
  lane and surface it for a plan fix rather than papering over it.

DEFINITION OF DONE (report with evidence)
1. `npm run check` green from /home/jakub/projects/repo-audit-skills; check:release lists the
   nine skills: complexity-audit, duplication-audit, dead-code-audit, structure-audit,
   quality-audit, code-health-audit-pipeline, test-audit-pipeline, test-quality-assurance,
   test-redundancy-triage. (paste the JSON)
2. Install round-trip: node bin/install-repo-audit-skills.js --dest /tmp/ras-install --force
   installs nine; a migrated script answers --help from the install.
3. audit_pipeline.py's DEFAULT_TQA_SCRIPT and DEFAULT_TRIAGE_SCRIPT resolve to existing files
   in the new layout (the "SIBLING DISCOVERY OK" smoke).
4. origin -> github.com/jc1122/repo-audit-skills on `main`, force-pushed; working directory is
   /home/jakub/projects/repo-audit-skills; old local repo removed.
5. Git history: three focused commits (Tasks 1-3); Phase 4 is config/filesystem only.

CONSTRAINTS
- Workers implement tasks verbatim; the orchestrator owns all merges and all of Phase 4.
- The migrated skills are lift-and-shift; their behavior/output is unchanged in this
  sub-project (Finding-schema/determinism/hardening conformance is Sub-project 2).
- Phase 4's force-push + rm + mv are irreversible and explicitly authorized, but require a
  fresh human "go" at the moment of execution. Never run them on your own initiative.
```

---

## Why this isn't a big parallel fan-out (and what is)

The earlier package build parallelized **four independent leaf skills**. This integration is a
**chain on shared package-machinery files**, so only the copy and the rename are independent.
If you want the heavily-parallel worker pattern again, that fits **Sub-project 2** (dogfooding +
determinism + hardening): there, per-skill fixes (timeouts, guarded parsing, version pinning,
Finding-schema conformance, adversarial corpora) are largely independent and fan out cleanly
across workers/worktrees. That sub-project gets its own spec, plan, and orchestrator prompt
after this integration lands.
