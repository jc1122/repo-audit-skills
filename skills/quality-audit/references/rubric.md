# quality-audit Rubric

| Source | Detects | Severity | Signal |
|---|---|---|---|
| ruff check | lint rule violations | medium | LINT |
| ruff format --check | formatting drift | low | FORMAT |
| mypy / ty | type errors | high | TYPE |

ruff selection: `E,W,F,B,SIM,UP` with `--ignore F401,F811,F841,C901` (the codes owned by
dead-code-audit and complexity-audit), guaranteeing non-overlap. Type checker defaults to
`mypy`; set `--config {"type_checker": "ty"}` to use `ty`. Override the ruff selection via
`--config` keys `ruff_select` / `ruff_ignore`. Advisory only — never applies fixes or
reformats.
