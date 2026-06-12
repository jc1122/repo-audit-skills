---
name: code-health-audit-pipeline
version: 0.5.10
description: >
  Umbrella that runs the code-health leaf skills (complexity, duplication, dead-code,
  structure, quality) in parallel, merges and ranks their findings into one report, and
  emits a supervisor decision with exit codes 0/1/2. Reads a leaf registry so new
  language leaves plug in without changing the orchestrator. Advisory only.
---

# code-health-audit-pipeline

## Overview

Runs registered code-health leaves once, merges their findings, and emits a
ranked backlog plus a machine-readable supervisor decision.

## Quick Start

```bash
python3 scripts/code_health_pipeline.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/code-health
```

## Outputs

```
out-dir/
├─ code_health_report.md       # ranked backlog grouped by signal
├─ code_health_summary.json    # supervisor decision + exit_code + per-leaf rollup + findings
├─ complexity/complexity_findings.json
├─ duplication/duplication_findings.json
├─ dead-code/dead-code_findings.json
├─ structure/structure_findings.json
└─ quality/quality_findings.json
```

## Exit Codes

- `0` PASS, `1` ADVISE (findings present), `2` GATE (hard gate breached, including any
  leaf erroring).

## Flags

- `--languages python` (default) — filters which leaves run via the registry.
- `--registry PATH` — override the leaf registry.
- `--leaf-script name=PATH` — override a single leaf's script path (repeatable).
- `--config PATH` — JSON gate overrides (`max_type_errors`, `max_high_severity`,
  `gate_on_import_cycle`, `gate_on_leaf_error`).

See `skills/code-health-audit-pipeline/references/prioritization.md`, `skills/code-health-audit-pipeline/references/rule-ownership.md`,
`skills/code-health-audit-pipeline/references/finding-schema.json`.
