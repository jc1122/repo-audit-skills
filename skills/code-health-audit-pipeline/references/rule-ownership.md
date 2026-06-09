# Rule Ownership (non-overlap contract)

Canonical source of truth. No tool/rule is counted by two leaves. The umbrella's
`(path, line, metric)` dedupe is only a backstop.

| Leaf | Owns | Signals |
|---|---|---|
| dead-code-audit | vulture (function/class/method/property), ruff F401/F811/F841 | DELETE |
| complexity-audit | radon mi, lizard (cc/nloc/params), ruff C901 | SIMPLIFY, DECOMPOSE |
| duplication-audit | jscpd | EXTRACT, MERGE |
| structure-audit | ast import graph (cycles, fan-in/out, layers) | RESTRUCTURE |
| quality-audit | ruff (all EXCEPT F401/F811/F841/C901), ruff format, mypy/ty | LINT, FORMAT, TYPE |
