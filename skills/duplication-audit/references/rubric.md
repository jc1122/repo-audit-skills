# duplication-audit Rubric

Clone detection via `jscpd` (token-based). One finding per clone pair.

| Condition | Threshold | Severity | Signal |
|---|---|---|---|
| Clone across two files | tokens > min | medium | EXTRACT |
| Clone within one file | tokens > min | medium | MERGE |
| Large clone | tokens > 3× min | high | EXTRACT/MERGE |

Defaults: `min_tokens=50`, `min_lines=5` (override via `--config`). Confidence is
`high` (deterministic). The leaf never mutates source.
