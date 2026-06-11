---
name: duplication-audit
version: 0.4.0
description: >
  Deterministic, advisory copy-paste clone audit for Python. Uses jscpd to detect
  duplicated token sequences and emits EXTRACT (cross-file) / MERGE (same-file)
  findings to the shared code-health finding schema. Never mutates source.
---

# duplication-audit

## Overview

A code-health leaf skill. It reports duplicated code blocks as advisory findings; it
does not refactor anything.

## Quick Start

```bash
python3 scripts/duplication_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/duplication
```

## Output

- `duplication_findings.json` — sorted findings (shared schema).
- `duplication_report.md` — summary grouped by signal.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error (e.g. jscpd/node missing).

## Tools and Thresholds

`jscpd` via `npx`. See `references/rubric.md`. Override with `--config thresholds.json`
(keys `min_tokens`, `min_lines`).

## Notes

- `--source-prefix` filters to product code (repeatable).
- Findings are deterministic: identical input yields byte-identical
  `duplication_findings.json`.
- One finding per clone pair (cross-file → EXTRACT, same-file → MERGE).
