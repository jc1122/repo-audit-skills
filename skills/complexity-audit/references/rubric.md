# complexity-audit Rubric

Per-function metrics come from `lizard`; per-module maintainability from `radon mi`.

| Metric | Source | Threshold | Severity | Signal |
|---|---|---|---|---|
| Cyclomatic complexity | lizard | > 10 | medium | DECOMPOSE |
| Cyclomatic complexity | lizard | > 20 | high | DECOMPOSE |
| Function length (NLOC) | lizard | > 50 | medium | DECOMPOSE |
| Parameter count | lizard | > 5 | low | SIMPLIFY |
| Maintainability index | radon mi | < 65 | low | SIMPLIFY |
| Maintainability index | radon mi | < 50 | medium | SIMPLIFY |

All thresholds overridable via `--config` (JSON). Confidence is always `high` (the
metrics are deterministic). The leaf never mutates source.
