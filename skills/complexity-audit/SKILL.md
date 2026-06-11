---
name: complexity-audit
version: 0.4.0
description: >
  Deterministic, advisory complexity and maintainability audit for Python. Uses
  lizard (per-function cyclomatic complexity, length, parameters) and radon mi
  (per-module maintainability index) to emit SIMPLIFY / DECOMPOSE findings to the
  shared code-health finding schema. Never mutates source.
---

# complexity-audit

## Overview

Reports functions that are too complex or too long and modules with low
maintainability. Advisory only; it does not refactor.

## Quick Start

```bash
python3 scripts/complexity_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/complexity
```

## Output

- `complexity_findings.json` — sorted list of findings (shared schema).
- `complexity_report.md` — human-readable summary grouped by signal.

## Exit Codes

- `0` — clean (no findings).
- `1` — advisory findings present.
- `2` — tool/config error (e.g. lizard or radon not installed).

## Flags and Thresholds

`--source-prefix` is repeatable. Override thresholds with `--config
thresholds.json`; see `skills/complexity-audit/references/rubric.md`.

## Notes

- Findings are deterministic: identical input yields byte-identical
  `complexity_findings.json`.
