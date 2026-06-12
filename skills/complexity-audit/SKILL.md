---
name: complexity-audit
version: 0.5.16
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
- `complexity_report.md` — human-readable summary grouped by signal, including
  counted precision suppressions such as `entrypoint_mi_relaxed`.
- stdout status JSON — includes `status`, `findings`, `leaf`, and
  `entrypoint_mi_relaxed`.

## Exit Codes

- `0` — clean (no findings).
- `1` — advisory findings present.
- `2` — tool/config error (e.g. lizard or radon not installed).

## Flags and Thresholds

`--source-prefix` is repeatable. Override thresholds with `--config
thresholds.json`; see `skills/complexity-audit/references/rubric.md`.

Default thresholds include `mi_low=65`, `mi_medium=50`, and
`mi_entrypoint_low=20`. Set `"mi_entrypoint_low": null` to disable entrypoint
module-MI relaxation.

## Notes

- Findings are deterministic: identical input yields byte-identical
  `complexity_findings.json`.
- CLI entrypoints with `if __name__ ==` guards suppress module-level
  maintainability-index findings when MI is at least `mi_entrypoint_low` but
  below `mi_low`; each suppression increments `entrypoint_mi_relaxed`.
- The entrypoint relaxation is intentionally narrow: standalone CLI modules can
  have low module MI because they remain self-contained, while function-level
  lizard checks still report actionable complexity. Entrypoint modules below
  the floor still emit `maintainability_index`.
