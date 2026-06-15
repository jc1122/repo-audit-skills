---
name: perf-smell-audit
version: 0.7.4
description: >
  Deterministic, advisory algorithmic performance-smell audit for Python. Wraps
  perflint (via pylint) to emit PERF findings for wrong container types, redundant
  casts, and list/comprehension refactors (perflint's high-precision deterministic
  checks) to the shared code-health finding schema. The over-approximating
  loop-invariant heuristics are excluded. Never mutates source.
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

perflint (via pylint, `--load-plugins=perflint`). Only perflint's high-precision
message ids are kept — W8101/W8102 (cast/iterator), W8204 (memoryview), W8301
(tuple-over-list), W8401/W8402/W8403 (comprehension refactors). The heuristic
loop-invariant family (W8201/W8202/W8205, R8203) is excluded; pylint core, syntax,
and import messages are
dropped. A missing `pylint` or `perflint` is a config error (exit `2`), never zero
findings. Findings are deterministic.

## Limits

- Advisory only — emits PERF findings and never mutates or reorders source.
- Python only: backed by `perflint` (via `pylint`).
- Requires `pylint` and `perflint` installed; a missing tool is a config error
  (exit `2`), not a finding.
- Source-level algorithmic smells only — complementary to exec-audit's
  execution-level PERF findings (slow tests, serial runners), not a duplicate.
- High-precision subset: wrong-container, redundant-cast, dict-iterator,
  memoryview, and list/comprehension refactors. The over-approximating
  loop-invariant heuristics (W8201/W8202/W8205, R8203) are excluded.
- Deterministic and offline; no network access.
