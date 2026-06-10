---
name: quality-audit
version: 0.3.0
description: >
  Deterministic, advisory lint/format/type audit for Python. Uses ruff (lint, with
  dead-code and complexity codes excluded), ruff format --check (formatting drift,
  reported not applied), and a type checker (mypy by default, ty selectable) to emit
  LINT / FORMAT / TYPE findings to the shared code-health finding schema. Never mutates
  source.
---

# quality-audit

## Overview

A code-health leaf skill reporting lint violations, formatting drift, and type errors as
advisory findings. It never runs `ruff --fix` or reformats.

## Quick Start

```bash
python3 scripts/quality_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/quality
```

## Output

- `quality_findings.json` — sorted findings (shared schema).
- `quality_report.md` — summary grouped by signal.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Config

`--config` JSON keys: `type_checker` ("mypy"|"ty"), `ruff_select`, `ruff_ignore`. The
default ruff ignore excludes F401/F811/F841/C901 (owned by other leaves). Findings are
deterministic.
