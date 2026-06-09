# dead-code-audit Rubric

| Source | Detects | Severity | Signal |
|---|---|---|---|
| vulture | unused function/class/method/property | by confidence | DELETE |
| ruff F401 | unused import | medium | DELETE |
| ruff F811 | redefinition of unused name | medium | DELETE |
| ruff F841 | unused local variable | medium | DELETE |

Vulture confidence → severity: ≥90 high, ≥70 medium, else low; confidence → schema
`confidence` field: ≥90 high, ≥70 medium, else low.

Non-overlap rule: vulture is parsed only for `function/class/method/property`. Unused
imports, redefinitions, and unused locals come from ruff (F401/F811/F841), the codes
this leaf owns. `--allowlist FILE` passes a vulture whitelist to suppress framework
false positives. Never mutates source.
