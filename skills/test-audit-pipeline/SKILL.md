---
name: test-audit-pipeline
version: 0.4.0
description: >
  One-command test health check that orchestrates coverage collection,
  TDD quality scoring, and redundancy triage into a unified pipeline.
  Runs independent stages in parallel for ~40% faster execution.
  Produces a single merged report with rubric scores, triage decisions,
  and actionable next steps.
---

# Test Audit Pipeline

## Overview

This skill orchestrates the `test-quality-assurance` and `test-redundancy-triage` skills into a single unified workflow. Instead of running 6+ separate tool calls, invoke the pipeline script once to get a complete audit report.

## Prerequisites

- Both sibling skills must be installed:
  - `test-quality-assurance` (provides `audit_test_quality.py`)
  - `test-redundancy-triage` (provides `triage_redundancy.py`)
- Python 3.10+
- `pytest`, `coverage` (optional for coverage integration)

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

## Parallelism Model

The pipeline stages have the following dependency graph:

```
Stage 1: Collect coverage (pytest --cov → coverage.json)
    ↓
Stage 2a: TQA audit (uses coverage.json)     ← PARALLEL
Stage 2b: Redundancy triage                  ← PARALLEL
    ↓
Stage 3: Unified report (merges TQA + triage results)
```

**Concurrent stages**: Stage 2a and 2b are fully independent and run in parallel using `concurrent.futures.ThreadPoolExecutor`. This cuts wall-clock time by ~40%.

**Sequential stages**: Stage 1 (coverage) must complete before Stage 2a (TQA needs coverage.json). Stage 3 depends on both 2a and 2b completing.

For agent orchestrators with subagent capabilities:
- Stage 2a can be delegated to a `test-quality-assurance` subagent
- Stage 2b can be delegated to a `test-redundancy-triage` subagent
- Both subagents can run concurrently

## Workflow

### 1. Single-Command Full Audit
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

### 2. With Baseline Comparison
```bash
python scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --suite tests/ \
  --out-dir /tmp/audit \
  --tqa-baseline /tmp/previous_audit/tqa_report.json \
  --env NUMBA_DISABLE_JIT=1
```

### 3. Coverage-Only Mode (skip triage)
```bash
python scripts/audit_pipeline.py \
  --root /path/to/repo \
  --python .venv/bin/python \
  --out-dir /tmp/audit \
  --skip-triage \
  --env NUMBA_DISABLE_JIT=1
```

## Output Structure

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

## Framework-Specific Notes

- **Numba**: Pass `--env NUMBA_DISABLE_JIT=1` to get truthful coverage
- **Django**: Pass `--env DJANGO_SETTINGS_MODULE=myproject.settings`
- **General**: Any env var needed by the test suite should be passed via `--env`

## Known Limitations

- The pipeline script discovers sibling skills by relative path (`../test-quality-assurance/`, `../test-redundancy-triage/`). If skills are installed in non-standard locations, use `--tqa-script` and `--triage-script` overrides.
- Coverage collection runs all matched tests; filter with `--test-marker` to exclude slow/benchmark tests.
- The unified report is additive — it does not replace the individual skill reports, which are also written to the output directory.
