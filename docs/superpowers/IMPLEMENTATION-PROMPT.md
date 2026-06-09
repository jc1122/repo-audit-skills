# Delegation Prompt — Implement code-health-skills (Plans 1–6)

Copy the fenced block below and give it to a fresh Claude Code session launched **inside
`/home/jakub/projects/code-health-skills`**. It drives a subagent through the six plans
in order. You can also delegate one plan at a time by replacing the plan list with a
single path.

---

```
You are implementing an approved, fully-specified plan set in this repository
(/home/jakub/projects/code-health-skills). Build a standalone package of deterministic,
advisory code-health skills: five leaves + an umbrella pipeline.

PLANS (implement strictly in this order — each depends on the previous):
1. docs/superpowers/plans/2026-06-10-code-health-skills-foundation.md   (scaffold + complexity-audit)
2. docs/superpowers/plans/2026-06-10-plan-2-duplication-audit.md
3. docs/superpowers/plans/2026-06-10-plan-3-dead-code-audit.md
4. docs/superpowers/plans/2026-06-10-plan-4-structure-audit.md
5. docs/superpowers/plans/2026-06-10-plan-5-quality-audit.md
6. docs/superpowers/plans/2026-06-10-plan-6-code-health-audit-pipeline.md

SPEC (context only): docs/superpowers/specs/2026-06-09-code-health-audit-pipeline-design.md

HOW TO EXECUTE:
- Use the superpowers:executing-plans skill. Within each plan, do the `- [ ]` steps
  strictly in order: write the failing test, run it and confirm it fails, write the
  minimal code, run it and confirm it passes, commit. One commit per task using the
  message in that task's final step.
- The plans are self-contained: exact file paths, complete code, exact commands, expected
  output. Do NOT improvise designs or add scope. If reality differs from an "Expected:"
  line, STOP and report rather than guessing.
- Finish a plan only when its final `npm run check` is green, then move to the next plan.

ALREADY DONE (do NOT repeat Plan 1, Task 1):
- The repo exists, `git init` has been run, `.gitignore` and the docs are in place.
- If `git log` is empty, make the initial commit first:
  git add -A && git commit -m "chore: init code-health-skills repo with planning docs"
- Start Plan 1 at Task 2.

ENVIRONMENT SETUP:
- Use a venv and install all leaf tools up front:
    python3 -m venv .venv && . .venv/bin/activate
    pip install lizard radon vulture ruff mypy pytest
- Node >= 18 must be available (the duplication leaf uses `npx --yes jscpd`; the umbrella
  end-to-end and the installer/release gate need Node). Network access is needed the first
  time `npx jscpd` runs (or pre-install `npm i -g jscpd`).
- Run leaf tests from inside each skill dir (e.g. `cd skills/duplication-audit &&
  python3 -m pytest tests/ -v`).

KNOWN, INTENTIONAL DEVIATIONS FROM THE SPEC (implement as written in the plans; do not
"correct" them back to the spec):
- Plan 2 (duplication): one finding per jscpd clone PAIR, not N-way clone groups.
- Plan 4 (structure): stdlib `ast` import graph + Tarjan SCC instead of `grimp`.
- Plan 5 (quality): default type checker is `mypy` (ty selectable via --config).
- Plan 6 (umbrella): `effort` for ranking is derived from a finding's `signal` (the leaf
  schema is not extended).

DEFINITION OF DONE (after Plan 6, paste evidence):
1. Every task's tests pass (paste final pytest summaries per plan).
2. `npm run check` is green (vendored-copy + fixtures + release gates), and check_release
   lists all six skills: complexity-audit, duplication-audit, dead-code-audit,
   structure-audit, quality-audit, code-health-audit-pipeline.
3. Install round-trip works:
     node bin/install-code-health-skills.js --dest /tmp/che-install --force
     python3 /tmp/che-install/code-health-audit-pipeline/scripts/code_health_pipeline.py --help
4. End-to-end (Plan 6, Task 5, Step 5): the umbrella run against
   skills/structure-audit/tests/fixtures/dirty exits 2 (GATE) with a structure cycle.
5. `git log --oneline` shows one focused commit per task across all six plans.

CONSTRAINTS:
- Do NOT touch /home/jakub/projects/repo-audit-skills. All work stays in this repo.
- Every leaf is advisory-only: it must never modify a target repo's source.
- `shared/health_common.py` is the source of truth; each leaf's
  scripts/health_common.py must remain a byte-identical vendored copy (the
  check_vendored_common gate enforces this).

When done, report per-plan status, the DoD evidence above, and any place real tool output
(lizard/radon/vulture/jscpd/mypy/ruff) differed from a plan's assumptions, so the plans can
be corrected.
```
