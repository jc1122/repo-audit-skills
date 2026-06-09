# Delegation Prompt — Implement Plan 1 (code-health-skills foundation)

Copy everything in the fenced block below and give it to a fresh Claude Code session
launched **inside `/home/jakub/projects/code-health-skills`**. It will drive a subagent
through the plan task-by-task.

---

```
You are implementing an approved, fully-specified plan in this repository
(/home/jakub/projects/code-health-skills).

PLAN: docs/superpowers/plans/2026-06-10-code-health-skills-foundation.md
SPEC (context only): docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md

This is Plan 1 of 6: it scaffolds the standalone `code-health-skills` package (its own
release machinery + a shared finding contract) and builds the first leaf skill,
`complexity-audit`, end-to-end.

HOW TO EXECUTE:
- Use the superpowers:executing-plans skill (batch execution with checkpoints) to work
  through the plan. The plan's steps use `- [ ]` checkboxes; do them strictly in order.
- The plan is self-contained: every step has the exact file path, complete code, exact
  command, and expected output. Do not improvise designs or add scope. If reality differs
  from an "Expected:" line, STOP and report rather than guessing.
- TDD is mandatory and already encoded: write the failing test, run it and confirm it
  fails, write the minimal code, run it and confirm it passes, then commit. One commit per
  task, using the commit message given in that task's final step.

ALREADY DONE (do NOT repeat Task 1):
- The repo exists and `git init` has been run.
- `.gitignore` is in place.
- `docs/superpowers/specs/...` and `docs/superpowers/plans/...` are in place.
- An initial commit may or may not exist yet; if `git log` is empty, make the Task 1
  "init" commit first: `git add -A && git commit -m "chore: init code-health-skills repo with planning docs"`.
- START AT TASK 2.

ENVIRONMENT SETUP (before Task 9, which needs the analysis tools):
- Create and use a venv, then install tools:
    python3 -m venv .venv
    . .venv/bin/activate
    pip install lizard radon pytest ruff
- Run leaf tests from inside the skill dir as the plan shows
  (`cd skills/complexity-audit && python3 -m pytest tests/ -v`).
- Node >= 18 must be available for the installer/release gate.

DEFINITION OF DONE (all must hold, with evidence pasted back):
1. Every task's tests pass (paste the final `pytest` summary lines).
2. `python3 scripts/check_vendored_common.py` → status "pass".
3. `python3 scripts/check_skill_fixtures.py` → status "pass".
4. `python3 scripts/check_release.py` → status "pass", skills lists "complexity-audit".
5. `npm run check` → all three checks pass.
6. Install round-trip works:
     node bin/install-code-health-skills.js --dest /tmp/che-install --force
     python3 /tmp/che-install/complexity-audit/scripts/complexity_audit.py --help
7. `git log --oneline` shows one focused commit per task.

CONSTRAINTS:
- Do NOT touch /home/jakub/projects/repo-audit-skills. All work stays in this repo.
- The leaf is advisory-only: it must never modify a target repo's source.
- `shared/health_common.py` is the source of truth; the leaf's
  `scripts/health_common.py` must stay a byte-identical vendored copy (the
  check_vendored_common gate enforces this).

When done, report: tasks completed, the DoD evidence above, and anything in the real tool
output (lizard/radon) that differed from the plan's assumptions so it can be folded into
Plans 2-6.
```
