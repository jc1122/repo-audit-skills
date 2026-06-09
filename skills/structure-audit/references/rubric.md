# structure-audit Rubric

Import graph built from stdlib `ast`. Cycles via Tarjan strongly-connected components.

| Condition | Default threshold | Severity | Signal |
|---|---|---|---|
| Import cycle (SCC size > 1) | n/a | high | RESTRUCTURE |
| Module fan-out (internal imports) | > 20 | medium | RESTRUCTURE |
| Module fan-in (imported-by count) | > 20 | medium | RESTRUCTURE |
| Layering violation (`--layers`) | n/a | high | RESTRUCTURE |

Overrides via `--config` (keys `max_fan_out`, `max_fan_in`, `layers`). `layers` is an
ordered list of dotted module prefixes, top-to-bottom; a lower-layer module importing a
higher-layer module is a violation. Confidence is `high`. Never mutates source.
