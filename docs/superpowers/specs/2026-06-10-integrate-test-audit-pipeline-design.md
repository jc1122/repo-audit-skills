# Integrate the test-audit pipeline into one package (`repo-audit-skills`) — Design

**Date:** 2026-06-10
**Status:** Approved (pending spec review)
**Sub-project:** 1 of 2 (Integration). Sub-project 2 = the dogfooding + determinism + hardening harness, specced separately after this lands.

## Goal

Fold the test-audit pipeline into the existing code-health package so a single package
contains both audit families, with all release gates green — **without changing the
migrated skills' behavior** (lift-and-shift). Rename the unified package to
`repo-audit-skills`, take over that name on disk and on GitHub, and decommission the old
placeholder repo.

## Context

Two repos exist today:

- `/home/jakub/projects/code-health-skills` — newer, clean machinery: vendored
  `shared/health_common.py` + `Finding` dataclass, version-lockstep release gate, uniform
  `--root/--source-prefix/--out-dir` CLI, `check_vendored_common`. Six skills (five leaves +
  `code-health-audit-pipeline`). No git remote; branch `master`.
- `/home/jakub/projects/repo-audit-skills` — older placeholder. Remote
  `origin → github.com/jc1122/repo-audit-skills.git`, branch `main`. Contains the
  test-audit pipeline **plus** `perf-benchmark` and `repo-audit-refactor-optimize`.

The code-health package is the cleaner base, so it absorbs the test-audit skills. The
name `repo-audit-skills` is semantically ideal for the merged package; the old repo is a
disposable placeholder we overwrite.

## Decisions (decision log)

1. **Two sub-projects.** Integration first (this spec); dogfooding/determinism/hardening
   second (later spec). The later phase uses a **ratchet/baseline** self-audit gate.
2. **What migrates:** `test-audit-pipeline`, `test-quality-assurance`,
   `test-redundancy-triage`. **Not** `perf-benchmark`, **not** `repo-audit-refactor-optimize`.
3. **Base/home:** the code-health package absorbs the three skills.
4. **Conformance:** lift-and-shift. Keep the migrated CLIs, outputs, references/, agents/.
   No `Finding`-schema conformance, no CLI unification, no timestamp/runtime removal —
   all deferred to Sub-project 2.
5. **Identity:** npm name → `repo-audit-skills`; **directory** renamed
   `code-health-skills` → `repo-audit-skills`; git `origin` → the old repo's GitHub URL,
   force-pushed (normalized to branch `main`), overwriting the placeholder.
6. **Old repo:** decommissioned. `perf-benchmark` + `repo-audit-refactor-optimize` are
   intentionally abandoned (they remain only in the pre-overwrite GitHub history).
7. **Umbrellas:** the two umbrellas (`code-health-audit-pipeline`, `test-audit-pipeline`)
   coexist independently. No unified top orchestrator (YAGNI / deferred).

## Architecture

### What moves

Copy three skill directories from the old repo into `skills/` of the merged package,
preserving their internal layout:

```
skills/test-audit-pipeline/      (umbrella: scripts/audit_pipeline.py, SKILL.md, agents/)
skills/test-quality-assurance/   (scripts/audit_test_quality.py, references/, SKILL.md, agents/)
skills/test-redundancy-triage/   (scripts/triage_redundancy.py, references/, SKILL.md, agents/, LICENSE)
```

Because `audit_pipeline.py` discovers its sibling leaves by relative path
(`SKILLS_DIR/test-quality-assurance/scripts/...`, `SKILLS_DIR/test-redundancy-triage/...`)
and all skills remain under `skills/`, that discovery keeps working unchanged.

The old repo's own machinery (`bin/install-repo-audit-skills.js`, `scripts/check_*.py`)
is **not** taken; the merged package keeps code-health's gates, extended.

### Release-gate reconciliation (verified against current gate code)

All edits are mechanical; nothing in the migrated skills needs reshaping.

- **`package.json`** — `name`: `code-health-skills` → `repo-audit-skills`; update `bin`
  to the renamed installer; version stays `0.1.0`. Confirm pack globs include `skills/**`
  (already do).
- **`bin/install-code-health-skills.js`** → `git mv` to `bin/install-repo-audit-skills.js`.
  Add the 3 dirs to the `skills` array. Update the `usage()` text. `copyDir` is already
  recursive and skips `.git`/`__pycache__`/cache dirs, so nested `references/`+`agents/`
  copy correctly.
- **`scripts/check_release.py`** — add 3 entries each to `REQUIRED_SKILLS` and
  `REQUIRED_SCRIPTS` (`scripts/audit_pipeline.py`, `scripts/audit_test_quality.py`,
  `scripts/triage_redundancy.py`); change the hardcoded
  `name == "code-health-skills"` check to `repo-audit-skills`; change the three
  installer-path references (`bin/install-code-health-skills.js` → new name) and the
  `/tmp/code-health-skills-release-check` dest string.
- **`scripts/check_skill_fixtures.py`** — append 3 `--help` commands. Verified: all three
  scripts already exit 0 on `--help` with no stderr.
- **`scripts/check_vendored_common.py`** — **no change**. It globs
  `skills/*/scripts/health_common.py`; the migrated skills don't vendor that file, so
  they're auto-excluded.
- **Migrated `SKILL.md`** — **no change**. Each already has `name:` matching its dir and
  `version: 0.1.0`, satisfying the lockstep gate.

### Identity / directory / GitHub takeover (final phase, after gates are green)

1. Rename the working directory `code-health-skills` → `repo-audit-skills`.
2. Set `origin` to `https://github.com/jc1122/repo-audit-skills.git`; rename the local
   branch `master` → `main`; force-push, overwriting the placeholder.
3. Remove the old local `/home/jakub/projects/repo-audit-skills` working copy.

These are destructive and explicitly authorized ("the old repo audit skills was just a
placeholder so we could overwrite it on github too"). They run **only after** the merged
package is verified green.

## Out of scope (lift-and-shift boundaries)

- No `Finding`-schema conformance for the migrated skills.
- No CLI unification (`--python/--suite/--env` stay).
- No removal/normalization of timestamps (`datetime.now`) or `runtime_ms` (`time.time`).
- No subprocess-timeout / guarded-parse / version-pinning fixes.
- No unified top orchestrator.
- `perf-benchmark` and `repo-audit-refactor-optimize` are not migrated.

All of the above belong to Sub-project 2.

## Testing & acceptance (Definition of Done)

1. `npm run check` green, listing all **9** skills (6 code-health + 3 migrated test-audit):
   `complexity-audit`,
   `duplication-audit`, `dead-code-audit`, `structure-audit`, `quality-audit`,
   `code-health-audit-pipeline`, `test-audit-pipeline`, `test-quality-assurance`,
   `test-redundancy-triage`.
2. Install round-trip: `node bin/install-repo-audit-skills.js --dest /tmp/ras --force`
   installs all skills; a spot-check `--help` on a migrated script works from the install.
3. Each migrated skill's **existing pytest suite passes** after the move (verification
   only — not wired as a new release gate in this sub-project). Any extra runtime deps the
   suites need (e.g. coverage) are noted but not added to the release gate.
4. Both umbrellas run from their new location (smoke: `audit_pipeline.py --help` and a
   `code_health_pipeline.py` run still exits per contract).
5. After the takeover: directory is `repo-audit-skills`, `origin` points at the GitHub
   repo on `main`, old local repo removed.

## Risks / verifications for the plan

- **Migrated test suites' path/deps assumptions.** Run them post-move; if a suite needs a
  dependency not present, record it for Sub-project 2 rather than expanding this gate.
- **Force-push correctness.** Confirm `origin` URL and that overwriting the placeholder is
  intended before pushing (it is, per decision 6) — this is the one irreversible external
  action.
- **Branch normalization.** Local `master` → `main` before pushing so the remote default
  branch stays `main`.
