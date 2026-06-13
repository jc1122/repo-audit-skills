---
name: structure-audit
version: 0.5.21
description: >
  Deterministic, advisory import-structure audit for Python. Builds the internal
  import graph (stdlib ast), enumerates import cycles (Tarjan SCC), and flags
  god-modules by fan-in/fan-out, emitting RESTRUCTURE findings to the shared
  code-health finding schema. Never mutates source.
---

# structure-audit

## Overview

Reports import cycles, god-modules, and optional layering violations as advisory
RESTRUCTURE findings.

## Quick Start

```bash
python3 scripts/structure_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/structure
```

## Output

- `structure_findings.json` — sorted findings (shared schema).
- `structure_report.md` — summary.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` config error.

## Config

`--source-prefix` is repeatable. `--config` JSON keys: `max_fan_out`,
`max_fan_in`, `layers` (ordered top-to-bottom prefix list). See
`skills/structure-audit/references/rubric.md`. Findings are deterministic.

## Limits

- Advisory only — emits RESTRUCTURE findings and never moves code or mutates
  source.
- Python only: the import graph is built from Python source via the stdlib
  `ast` module.
- Static top-level imports only: dynamic imports (`importlib`, `__import__`,
  conditional imports) are not modeled.
- Internal imports only: only modules under the given `--source-prefix` form
  the graph; third-party and stdlib edges are out of scope.
- God-module flags are threshold-based on fan-in/fan-out and need human
  judgment.
- Deterministic and offline; no network access.
