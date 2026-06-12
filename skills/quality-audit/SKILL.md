---
name: quality-audit
version: 0.5.13
description: >
  Deterministic, advisory lint/format/type audit for Python. Uses ruff lint
  (with dead-code and complexity codes excluded), config-gated ruff format
  --check, and a type checker to emit LINT / FORMAT / TYPE findings. Never
  mutates source.
---

# quality-audit

## Overview

A code-health leaf skill reporting lint violations, declared-standard formatting
drift, and type errors as advisory findings. It never runs `ruff --fix` or
reformats.

## Quick Start

```bash
python3 scripts/quality_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/quality
```

## Output

- `quality_findings.json` — sorted findings (shared schema).
- `quality_report.md` — summary grouped by signal plus format-check status.
- stdout status JSON includes `format_check` and `suppressed_format_files`.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Config

`--config` JSON keys: `type_checker` ("mypy"|"ty"), `ruff_select`, `ruff_ignore`. The
default ruff ignore excludes F401/F811/F841/C901 (owned by other leaves). Findings are
deterministic.

## Limits

`ruff format --check` runs only when the audited root declares a formatting
standard via `.ruff.toml`, `ruff.toml`, `[tool.ruff...]`, or `[tool.black...]`
in `pyproject.toml`. Without one, FORMAT findings are skipped and counted as
`suppressed_format_files`; lint and type checks still run.
