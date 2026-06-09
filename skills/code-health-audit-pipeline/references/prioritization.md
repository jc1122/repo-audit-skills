# Prioritization

Each finding is scored `severity_weight × confidence_weight ÷ effort`, ranked descending.

- severity_weight: info 0, low 1, medium 2, high 4
- confidence_weight: low 1, medium 2, high 3
- effort (by signal): DELETE/LINT/FORMAT 1, TYPE/SIMPLIFY/MERGE 2, EXTRACT/DECOMPOSE 3,
  RESTRUCTURE 4

Ties break by `(path, line_start, signal, metric)` for determinism.

## Supervisor decision and exit codes

- `0` PASS — no findings above `info`, no gate breached.
- `1` ADVISE — advisory findings present, no gate breached.
- `2` GATE — a configured hard gate breached: any leaf errored, an import cycle is present,
  type errors exceed `max_type_errors`, or high-severity findings exceed
  `max_high_severity`. Defaults gate on leaf error and import cycle only.
