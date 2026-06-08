---
name: test-quality-assurance
version: 0.1.0
description: >
  Score your test suite against an 8-dimension TDD rubric (contract coverage,
  behavior focus, assertion quality, pyramid balance, coverage/mutation gates,
  and more). Produces automated 0-24 rubric scores, delta reports for tracking
  improvement over time, and prioritized action plans. Supports coverage.json
  integration for Numba, Cython, and standard Python projects.
---

# Test Quality Assurance

## Overview

Use this skill to evaluate test-suite quality, not just test count.
It focuses on TDD discipline, contract coverage, behavior-vs-implementation coupling, and actionable improvement plans.

This skill is intentionally distinct from `$test-redundancy-triage`.
Use `$test-redundancy-triage` for keep/merge/delete redundancy decisions.
Use this skill for broader quality assurance and architecture-level test health.

## Use This Skill When

1. A team asks whether tests follow TDD best practices.
2. You need to assess if tests validate behavior or implementation details.
3. You need a unit/integration/white-box/black-box balance review.
4. You need quality gaps and prioritized next actions, not only coverage numbers.
5. You are defining a test-quality policy or preparing a test strategy refactor.

## Outputs

Produce these artifacts in the response:

1. Best-practice rules: explicit quality rules used for evaluation.
2. Evidence map: concrete file/line references for each rule.
3. Findings: severity-ordered quality gaps with impact.
4. Open questions: unknowns that block high-confidence conclusions.
5. Action plan: short, prioritized changes with expected signal gain.
6. Skill question bank: questions to ask in future audits.

## Workflow

### 1. Confirm Runtime and Tooling Baseline
1. Verify active interpreter/venv and test plugins.
2. Confirm required deps for *this repository's* test collection (from `pyproject.toml`, `requirements*.txt`, test imports, and pytest config).
3. Run collection first before deeper analysis to avoid false conclusions.

Suggested commands:

```bash
# Adapt the Python/pip/pytest invocation to your environment:
#   .venv:  ./.venv/bin/python / ./.venv/bin/pytest
#   uv:     uv run python / uv run pytest
#   Poetry: poetry run python / poetry run pytest
#   global: python / pytest
python -V
pip check
pytest --collect-only -q
```

### 2. Build a Contract Map
Create a concise map of:

1. Public API contracts and error semantics.
2. Core algorithm invariants.
3. Critical non-functional contracts (performance/memory/stability).

This map is the truth source for deciding whether tests are behavior-first.

### 3. Inventory and Classify Tests
For each test (or test cluster), classify as:

1. Unit contract test
2. Integration seam test
3. White-box algorithm guard
4. Black-box behavior test
5. Change-indicator/snapshot sentinel
6. Performance benchmark

Use [`scripts/audit_test_quality.py`](scripts/audit_test_quality.py) for a fast baseline metric pass.

```bash
SKILLS_DIR="${SKILLS_DIR:-$HOME/.codex/skills}"  # or $HOME/.claude/skills
python "$SKILLS_DIR/test-quality-assurance/scripts/audit_test_quality.py" \
  --root /path/to/repo \
  --internal-import-pattern "from\\s+myproj\\.(core|impl)\\s+import" \
  --public-hint "compute(" --public-hint "run_pipeline(" \
  --json-out /tmp/test_quality.json \
  --md-out /tmp/test_quality.md
```

Portability notes:
1. `--internal-import-pattern` and `--public-hint` are repo-specific knobs; pass them explicitly for best signal.
2. If you omit `--public-hint`, the script auto-infers hints from package exports in `__init__.py`.
3. Use `--tests-dir` / `--test-glob` when tests are not in a standard `tests/` layout.

### 4. Score the Suite with the Rubric
Evaluate against [`references/rubric.md`](references/rubric.md):

1. Behavior focus
2. White-box justification
3. Determinism/isolation
4. Assertion/oracle quality
5. Pyramid balance
6. Coverage/mutation adequacy
7. Performance-contract coverage
8. Maintainability and change resilience

### 5. Distinguish Contract Tests from Change Indicators
Label tests explicitly:

1. `contract test`: required behavioral specification
2. `white-box sentinel`: justified internal-logic guard
3. `change indicator`: mainly snapshots topology/shape and flags any drift

Avoid deleting change indicators automatically; decide intentionally whether to keep, rewrite, or demote.

### 6. Produce Findings and Questions
Findings must be severity-ordered and evidence-linked.
Use [`references/question-bank.md`](references/question-bank.md) to expand missing questions.

### 7. Recommend a Minimal Improvement Plan
Provide 3-8 concrete actions with expected impact, for example:

1. Migrate selected private-method tests to public API contract tests.
2. Tighten exception assertions (`type` + message pattern).
3. Split multi-concern tests into single-failure-reason tests.
4. Add/raise mutation and branch gates for critical modules.

## Framework-Specific Caveats

When auditing projects that use compilation, JIT, or native extensions, be aware of
framework-specific blind spots that affect coverage and metric accuracy.

- **Numba**: For Numba projects, JIT-compiled functions are invisible to `coverage.py`. Set `NUMBA_DISABLE_JIT=1` before collecting coverage. Without it, coverage may report ~50-60% when actual coverage is >90%.
- **Cython**: For Cython extensions, use `cython --annotate` for coverage of `.pyx` files.
- **ctypes/CFFI**: C extensions loaded via ctypes/CFFI are not instrumented by `coverage.py`. Test their Python wrappers, not the C code directly.
- **General**: Always verify that framework-specific compilation/JIT does not mask coverage. Run a quick sanity check: disable all compilation, measure coverage, and compare.

## Reporting Format

Use this report order unless the user asks otherwise:

1. Best-practice rules (short list).
2. Conformance results by rule.
3. Findings by severity with file evidence.
4. Open questions/assumptions.
5. Prioritized action plan.

## References

1. [`references/rubric.md`](references/rubric.md): scoring dimensions and thresholds.
2. [`references/question-bank.md`](references/question-bank.md): guided QA questions.
3. [`scripts/audit_test_quality.py`](scripts/audit_test_quality.py): quick automated inventory.
4. [`references/sample-report.md`](references/sample-report.md): example output to calibrate expectations.

## Known Limitations

- The audit script is purely static (AST-based). It cannot detect runtime-only test behaviors like fixture injection patterns or dynamic parametrization.
- Rubric scoring is heuristic-based and may not match expert judgment for edge cases. Use as a conversation starter, not a definitive grade.
- Coverage integration (`--cov-json`) requires a pre-generated `coverage.json` file. The script does not run coverage itself.
- The script does not currently support comparing per-variant coverage of parametrized tests.
