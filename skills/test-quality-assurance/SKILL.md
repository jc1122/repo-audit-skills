---
name: test-quality-assurance
version: 0.5.15
description: >
  Score your test suite against an 8-dimension TDD rubric, produce 0-24 scores,
  and output quality gaps with prioritized improvement actions.
---

# Test Quality Assurance

## Purpose
Use this skill for test-health quality scoring (contract coverage, behavioral clarity,
maintainability, and risk posture). This is separate from `$test-redundancy-triage`, which
handles redundancy classification.

## Baseline and Tooling
- Verify active interpreter/venv, pytest plugins, and collection dependencies.
- Confirm imports/deps from `pyproject.toml`, `requirements*.txt`, and pytest config.
- Run:

```bash
python -V
pip check
pytest --collect-only -q
```

## Contract Map + Inventory
Create a concise contract map first:
- public API behavior + error contracts,
- invariants for core algorithms,
- non-functional assumptions (perf/memory/stability).

Then classify tests as unit contract, integration seam, white-box guard, black-box behavior,
change-indicator/sentinel, or performance benchmark.

Use:

`skills/test-quality-assurance/scripts/audit_test_quality.py`

```bash
SKILLS_DIR="${SKILLS_DIR:-$HOME/.codex/skills}"
python "$SKILLS_DIR/test-quality-assurance/scripts/audit_test_quality.py" \
  --root /path/to/repo \
  --internal-import-pattern "from\\s+myproj\\.(core|impl)\\s+import" \
  --public-hint "compute(" --public-hint "run_pipeline(" \
  --tests-dir tests \
  --test-glob "test_*.py" \
  --cov-json /tmp/coverage.json \
  --json-out /tmp/test_quality.json \
  --md-out /tmp/test_quality.md
```

If `--public-hint` is omitted, public hints are inferred from package `__init__` exports.

## Rubric (8 dimensions)
Use [`skills/test-quality-assurance/references/rubric.md`](skills/test-quality-assurance/references/rubric.md):
behavior focus; white-box justification; determinism/isolation; assertion/oracle quality;
pyramid balance; mutation/coverage adequacy; performance-contract coverage; maintainability
and change resilience.

## Output Order
1. Best-practice rules.
2. Rule conformance.
3. Severity-ordered findings with file evidence.
4. Open questions/assumptions.
5. Prioritized action plan.

## Findings Guidance
Use [`skills/test-quality-assurance/references/question-bank.md`](skills/test-quality-assurance/references/question-bank.md) to expand evidence gaps.
Tag outputs as `contract test`, `white-box sentinel`, or `change indicator`;
do not auto-delete change indicators.

## Framework Caveats
- **Numba**: set `NUMBA_DISABLE_JIT=1` for meaningful `coverage.py` signal.
- **Cython**: complement with `cython --annotate` for `.pyx` coverage.
- **ctypes/CFFI**: not directly instrumented by `coverage.py`; validate wrappers.
- For compiled/JIT code, compare a normal run with a non-compiled baseline run.

## References
- [`skills/test-quality-assurance/references/rubric.md`](skills/test-quality-assurance/references/rubric.md): dimensions and thresholds.
- [`skills/test-quality-assurance/references/question-bank.md`](skills/test-quality-assurance/references/question-bank.md): common QA questions.
- [`skills/test-quality-assurance/scripts/audit_test_quality.py`](skills/test-quality-assurance/scripts/audit_test_quality.py): baseline metrics.
- [`skills/test-quality-assurance/references/sample-report.md`](skills/test-quality-assurance/references/sample-report.md): output pattern.

## Known Limitations
- AST/static analysis only; runtime-only behavior and dynamic fixture patterns can be missed.
- Heuristic scoring is advisory and should be interpreted by humans.
- `--cov-json` requires a pre-generated `coverage.json` file.
- No per-variant comparison for parametrized tests.
