---
name: perf-smell-audit
version: 0.7.0
description: >
  Deterministic, advisory algorithmic performance-smell audit for Python. Wraps
  perflint (via pylint) to emit PERF findings (loop-invariant computation, wrong
  container types, and related anti-patterns) to the shared code-health finding
  schema. Never mutates source.
---

# perf-smell-audit

## Overview

A code-health leaf skill reporting source-level algorithmic performance smells as
advisory PERF findings. It does not modify anything.

## Quick Start

```bash
python3 scripts/perf_smell_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/perf-smell
```

## Output

- `perf-smell_findings.json` — sorted findings (shared schema).
- `perf-smell_report.md` — summary.
- stdout status JSON.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Tools

perflint (via pylint, `--load-plugins=perflint`). Only perflint's own message ids
(the `W8*` / `R8*` range) are kept; pylint core, syntax, and import messages are
dropped. A missing `pylint` or `perflint` is a config error (exit `2`), never zero
findings. Findings are deterministic.

## Limits

- Advisory only — emits PERF findings and never mutates or reorders source.
- Python only: backed by `perflint` (via `pylint`).
- Requires `pylint` and `perflint` installed; a missing tool is a config error
  (exit `2`), not a finding.
- Source-level algorithmic smells only — complementary to exec-audit's
  execution-level PERF findings (slow tests, serial runners), not a duplicate.
- High-precision subset: wrong-container, loop-invariant, and related patterns.
- Deterministic and offline; no network access.
