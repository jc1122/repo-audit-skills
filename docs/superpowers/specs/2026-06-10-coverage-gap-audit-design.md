# coverage-gap-audit — Design (Sub-project 3)

**Date:** 2026-06-10
**Status:** Approved for implementation.
**Predecessor:** Sub-project 2 (dogfooding self-improvement) — converged at commit `5ade954`;
baseline 162 findings, of which **126 (78%) are frozen solely because the three migrated
test-audit skills ship no tests** (Actionability Rule, applied *manually* by the orchestrator).

## Goal

Add a new leaf skill, **`coverage-gap-audit`**, that reports *testedness*: which production
files have no (or insufficient) test coverage. Wire it into the package's own gates so the
Actionability Rule becomes a **computed property** (a ratcheted `coverage_gap_baseline.json`)
instead of a markdown convention, then run a bounded self-refinement loop that adds tests for
(or justifiably freezes) the package's own uncovered production scripts.

## Why this skill

The existing leaves audit **static source properties** (complexity, duplication, dead code,
structure, lint/types). The convergence review of Sub-project 2 found that every residual gap
was a property of the **verification machinery**: untested files, ungated suites, broken CLI
contracts. The refactor pipeline's core question — "is this finding *safe* to act on?" —
fundamentally means "is this file tested?", and no leaf answers it.

## Decisions

1. **File-level testedness only (v1).** One finding per under-covered file
   (`metric=file_coverage_percent`, `symbol=<file>`). Function-level coverage regions are
   YAGNI for the actionability use-case and vary across coverage.py versions.
2. **The leaf consumes `coverage.py` JSON reports; it never runs tests.** Running test suites
   inside an audit leaf breaks determinism, the 120s leaf-timeout model, and the advisory
   never-mutates contract. Input: one or more `--coverage-json` files (required args).
3. **New `TEST` signal in the shared schema.** `shared/health_common.py` `SIGNALS` gains
   `"TEST"`; the umbrella's `EFFORT` map gains `"TEST": 3`. Additive: no existing leaf emits
   it, so no golden fixture changes. The shared file's bytes change → re-vendor all leaf
   copies; the self-audit duplication finding's line-range symbol churns → ratchet absorbs it
   in the same commit.
4. **NOT registered in the umbrella `leaf_registry.json` (v1).** The umbrella invokes leaves
   with only `--root/--out-dir/--source-prefix` and cannot supply `--coverage-json`;
   "skip-clean when no coverage data" semantics would silently under-report on every target
   repo without coverage artifacts. Umbrella integration is deferred to a v2 design.
5. **Repo gate `check:coverage` mechanizes the Actionability Rule.**
   `scripts/check_coverage_gap.py` runs every suite (8 of them) as **separate pytest
   subprocesses from repo root** (separate processes avoid the known module-name collision)
   under **pytest-cov** (which traces the CLI-test subprocesses too), combines into one
   `coverage.json`, runs the leaf production-scoped (same prefixes as `self_audit.py`),
   normalizes to `{path, metric}` entries, and **ratchets** against
   `scripts/coverage_gap_baseline.json` exactly like `check:selfaudit`. A suite failure fails
   the gate, which also closes the "75 tests are not gated" hole. `npm run check` grows to
   FIVE gates.
6. **Multi-report merge rule:** per file, executed lines = **union** across reports;
   `num_statements` = **max** across reports; `percent = 100 * |executed| / num_statements`
   (files with 0 statements count as 100%); files absent from all reports = 0%.
7. **Thresholds:** `min_file_coverage = 50.0`. `0%` → severity **high**, confidence high
   ("untested"); `0% < pct < 50%` → severity **medium**, confidence medium. At or above
   threshold → no finding.
8. **Pinned tools:** `coverage==7.14.1`, `pytest-cov==7.1.0` (this env; install via
   `.venv/bin/python -m pip` — the venv's `pip` shim has a stale shebang). The leaf itself is
   **stdlib-only** at runtime.
9. **Self-refinement loop (Phase 2), bounded at 4 rounds.** Actionable coverage-gap finding =
   path **not** under `skills/test-*/scripts` (those stay rule-frozen until Sub-project 4
   writes their tests). Workers ADD behavior tests (preferred) or FREEZE with a concrete
   reason in a new "Coverage-gap" section of `scripts/self_audit_frozen.md`. Ratchet the
   coverage baseline down each round. Converged when the actionable coverage-gap set is empty.
10. **Release 0.2.0, not pushed.** Final task bumps `package.json` and all ten `SKILL.md`
    versions to `0.2.0` (the release gate enforces equality), verifies five green gates and
    `npm pack --dry-run`; pushing/publishing/reinstalling remain human steps.

## Out of scope

Umbrella registry integration (decision 4); function-level/branch coverage; mutation testing;
writing tests for the three test-audit skills (that is Sub-project 4, *enabled* by this work);
touching `tests/fixtures/**`; changing any existing tool's output contract.

## Risks

- **Self-audit churn:** every new `scripts/*.py` / leaf script lands inside the self-audit's
  auto-discovered production scope and will add findings (module-MI is certain). Standing
  rule: each task that adds production code must leave `npm run check` green — fix lint
  outright, freeze structural metrics with a justification, and ratchet the self-audit
  baseline in the same commit.
- **Subprocess coverage:** CLI tests spawn `sys.executable <script>`; pytest-cov's subprocess
  hook covers them only if the env is inherited (it is — tests don't override `env`). The
  plan verifies this empirically before freezing the coverage baseline.
- **Gate self-coverage recursion:** the root test for `check_coverage_gap.py` must use its
  `--coverage-json` injection mode (skips suite-running) or it would recurse into itself.
