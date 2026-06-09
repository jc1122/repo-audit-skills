# Integration Bootloader — paste as the orchestrator agent's goal

Set the block below as the goal of a fresh **Opus** session started **inside
`/home/jakub/projects/code-health-skills`**. It is self-bootstrapping: it tells the agent to
read the authoritative orchestrator prompt, plan, and spec already committed in this repo, then
carries the goal, the four-phase DAG, and the Definition of Done inline so a cold-start agent
always has a concrete target to verify against.

Full detail lives in:
- `docs/superpowers/INTEGRATION-ORCHESTRATOR-PROMPT.md` (the orchestration contract)
- `docs/superpowers/plans/2026-06-10-integrate-test-audit-pipeline.md` (task-by-task plan)
- `docs/superpowers/specs/2026-06-10-integrate-test-audit-pipeline-design.md` (design + decisions)

---

```
You are the ORCHESTRATOR (Opus) for integrating the test-audit pipeline into the
repo-audit-skills package, working in /home/jakub/projects/code-health-skills. You
coordinate only: you dispatch OpenCode DeepSeek v4 Pro workers via the
opencode-worker-bridge skill, verify every gate yourself by reading real output, merge
their branches, and personally perform the one irreversible phase with human confirmation.

FIRST: read docs/superpowers/INTEGRATION-ORCHESTRATOR-PROMPT.md and the two sources of
truth it names — docs/superpowers/plans/2026-06-10-integrate-test-audit-pipeline.md and
docs/superpowers/specs/2026-06-10-integrate-test-audit-pipeline-design.md. They are
authoritative and self-contained (exact paths, edits, commands, expected output). Workers
implement plan tasks VERBATIM, lift-and-shift: never modify the migrated skills' internals,
shared/health_common.py, or any existing code-health leaf; never add tests or pyproject.

GOAL: fold three skills (test-audit-pipeline, test-quality-assurance, test-redundancy-triage)
from /home/jakub/projects/repo-audit-skills/skills into this package, rename the package to
repo-audit-skills, register the new skills in the machinery, then take over the directory and
GitHub identity — ending green at NINE skills.

EXECUTE IN PHASES (verify each gate before advancing; a worker's "it's green" is NOT evidence
— run the gate and read its JSON):
- Phase 1 (2 concurrent workers, separate worktrees, disjoint files): Worker A = Task 1 (copy
  the 3 skill dirs); Worker B = Task 2 (rename package identity to repo-audit-skills). Each
  runs its own task verification and commit.
- Phase 2 (you): merge A and B (must be conflict-free; any conflict = a worker strayed — STOP).
  GATE: npm run check green, name asserted repo-audit-skills, still SIX skills listed, 3 new
  dirs present.
- Phase 3 (1 worker): Task 3 (register the 3 skills in installer + check_release +
  check_skill_fixtures + README). Merge. GATE (you re-run): npm run check green listing NINE
  skills; install round-trip installs nine; sibling-discovery smoke prints "SIBLING DISCOVERY OK".
- Phase 4 (you, IRREVERSIBLE, NOT delegated): Task 4 — branch master->main, point origin at
  github.com/jc1122/repo-audit-skills, force-push over the placeholder, rm the old local repo,
  mv code-health-skills -> repo-audit-skills. PAUSE for an explicit human "go" before each of
  the force-push, the rm, and the mv. Use absolute paths from /home/jakub/projects so a reset
  cwd can't sit inside a directory being moved. Then run the plan's final verification.

DEFINITION OF DONE (report with pasted evidence):
1. npm run check green from /home/jakub/projects/repo-audit-skills; check:release lists nine:
   complexity-audit, duplication-audit, dead-code-audit, structure-audit, quality-audit,
   code-health-audit-pipeline, test-audit-pipeline, test-quality-assurance, test-redundancy-triage.
2. node bin/install-repo-audit-skills.js --dest /tmp/ras-install --force installs nine; a
   migrated script answers --help from the install.
3. audit_pipeline.py's DEFAULT_TQA_SCRIPT and DEFAULT_TRIAGE_SCRIPT resolve to existing files
   in the new layout (the SIBLING DISCOVERY OK smoke).
4. origin -> github.com/jc1122/repo-audit-skills on main, force-pushed; working directory is
   /home/jakub/projects/repo-audit-skills; old local repo removed.
5. Git history shows three focused commits (Tasks 1-3); Phase 4 is config/filesystem only.

CONSTRAINTS: workers implement verbatim and own no merges; you own all merges and all of
Phase 4; the force-push/rm/mv are authorized but require a fresh human go at execution time —
never run them on your own initiative. Concurrency caps at 2 workers — this is a dependency
chain, not a fan-out; do not invent further parallelism on the shared machinery files.
```
