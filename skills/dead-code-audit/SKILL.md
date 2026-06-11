---
name: dead-code-audit
version: 0.4.0
description: >
  Deterministic, advisory dead-code audit for Python. Uses vulture (unused
  functions/classes/methods/properties) and ruff F401/F811/F841 (unused imports,
  redefinitions, unused locals) to emit DELETE findings to the shared code-health
  finding schema. Never mutates source.
---

# dead-code-audit

## Overview

A code-health leaf skill reporting unused/dead code as advisory DELETE findings. It
does not delete anything.

## Quick Start

```bash
python3 scripts/dead_code_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/dead-code \
  --allowlist .vulture_whitelist.py
```

## Output

- `dead-code_findings.json` — sorted findings (shared schema).
- `dead-code_report.md` — summary.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Tools

vulture + ruff (F401/F811/F841 only). See `skills/dead-code-audit/references/rubric.md`. `--allowlist FILE`
suppresses vulture false positives. Findings are deterministic.
