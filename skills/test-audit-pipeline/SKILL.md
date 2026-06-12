---
name: test-audit-pipeline
version: 0.5.20
description: >
  One-command test health check that orchestrates coverage collection,
  TDD quality scoring, and redundancy triage into a unified pipeline.
  Runs independent stages in parallel for ~40% faster execution.
  Produces a single merged report with rubric scores, triage decisions,
  and actionable next steps.
---

# Test Audit Pipeline

## Overview

Orchestrates `test-quality-assurance` and `test-redundancy-triage` into one
workflow with shared coverage collection and a unified report.

## Prerequisites

- Sibling skills installed: `test-quality-assurance` (`audit_test_quality.py`)
  and `test-redundancy-triage` (`triage_redundancy.py`).
- Python 3.10+; `pytest`; `coverage` is optional for coverage integration.

## Quick Start

```bash
python ~/.agents/skills/test-audit-pipeline/scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --suite tests/test_api.py \
  --suite tests/test_core.py \
  --source-prefix src/mypackage/ \
  --internal-import-pattern "from\s+mypackage\.(core|impl)\s+import" \
  --public-hint "compute(" \
  --out-dir /tmp/full_audit \
  --env NUMBA_DISABLE_JIT=1
```

## Parallelism

The pipeline stages have the following dependency graph:

```
Stage 1: Collect coverage (pytest --cov → coverage.json)
    ↓
Stage 2a: TQA audit (uses coverage.json)     ← PARALLEL
Stage 2b: Redundancy triage                  ← PARALLEL
    ↓
Stage 3: Unified report (merges TQA + triage results)
```

Stage 2a and 2b run concurrently with `ThreadPoolExecutor`; coverage must finish
before TQA, and the report waits for both. Agent orchestrators may delegate TQA
and triage to separate subagents.

## Common Runs

Full audit:
```bash
python scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --suite tests/test_api.py \
  --comparator-suite tests/test_integration.py \
  --source-prefix src/pkg/ \
  --out-dir /tmp/audit \
  --env NUMBA_DISABLE_JIT=1
```

Baseline comparison:
```bash
python scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --suite tests/ \
  --out-dir /tmp/audit \
  --tqa-baseline /tmp/previous_audit/tqa_report.json \
  --env NUMBA_DISABLE_JIT=1
```

Coverage-only mode:
```bash
python scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --out-dir /tmp/audit \
  --skip-triage \
  --env NUMBA_DISABLE_JIT=1
```

## Outputs

```
out-dir/
├── pipeline_report.md          # Unified human-readable report
├── pipeline_summary.json       # Machine-readable merged results
├── coverage.json               # Raw coverage data (when collected)
├── tqa_report.json             # TQA JSON output
├── tqa_report.md               # TQA markdown output
└── triage/                     # Triage sub-directory
    ├── candidate_validation.md
    ├── candidate_validation.csv
    ├── confidence_gate_matrix.csv
    └── ... (all triage outputs)
```

## Framework Notes

- **Numba**: Pass `--env NUMBA_DISABLE_JIT=1` to get truthful coverage
- **Django**: Pass `--env DJANGO_SETTINGS_MODULE=myproject.settings`
- **General**: Any env var needed by the test suite should be passed via `--env`

## Known Limitations

- Sibling skill discovery is relative to the `test-quality-assurance` and
  `test-redundancy-triage` install directories; use `--tqa-script` and
  `--triage-script` for non-standard layouts.
- Coverage collection runs all matched tests; use `--test-marker` for filtering.
- The unified report is additive; individual reports are still written.
