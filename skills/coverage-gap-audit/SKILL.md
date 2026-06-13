---
name: coverage-gap-audit
version: 0.6.0
description: >
  Deterministic, advisory testedness audit for Python. Consumes coverage.py JSON
  report(s) and emits TEST findings (shared code-health schema) for production
  files with no or insufficient test coverage. Never runs tests, never mutates
  source. The machine-readable answer to "is this file safe to refactor?".
---

# coverage-gap-audit

## Overview

Reports under-tested files as advisory TEST findings. It consumes existing
coverage data; generate it first, e.g.:

```bash
python -m pytest tests -q --cov --cov-report= && python -m coverage json -o coverage.json
```

## Quick Start

```bash
python3 scripts/coverage_gap_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --coverage-json coverage.json \
  --out-dir /tmp/coverage-gap
```

`--source-prefix` and `--coverage-json` are repeatable. Multiple coverage
reports are merged by union of executed lines and max statement count.

## Output

- `coverage-gap_findings.json` — sorted findings (shared schema).
- `coverage-gap_report.md` — summary.

## Findings

- `file_coverage_percent` 0% → severity high (untested file).
- `0% < pct < min_file_coverage` (default 50%) → severity medium.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error (missing or
  invalid coverage report).

## Limits

- Advisory only — emits TEST findings and never mutates source.
- Never runs tests: it consumes an existing coverage.py JSON report, so its
  accuracy depends entirely on how that report was generated.
- Python only: tuned for coverage.py JSON for Python production files.
- A missing or invalid coverage report is a config error (exit `2`), not a
  finding.
- Line-coverage based: reports under-tested files by executed-line percentage;
  it does not assess assertion quality or branch coverage.
- Deterministic and offline; no network access.
