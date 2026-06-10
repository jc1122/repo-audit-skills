# Repo Audit Skills

Standalone package of deterministic, advisory repo-audit skills — a code-health family and a test-audit family.

Leaf skills (each independently runnable, never mutate source):

- `complexity-audit` — radon + lizard → SIMPLIFY / DECOMPOSE
- `duplication-audit` — jscpd / symilar → EXTRACT / MERGE
- `dead-code-audit` — vulture + ruff F-codes → DELETE
- `structure-audit` — grimp import graph → RESTRUCTURE
- `quality-audit` — ruff + ruff format + ty → LINT / FORMAT / TYPE

Umbrellas:

- `code-health-audit-pipeline` — runs the code-health leaves in parallel, merges and
  ranks findings, and emits a supervisor decision with exit codes 0/1/2.
- `test-audit-pipeline` — orchestrates coverage collection, test-quality scoring, and
  redundancy triage into a unified test-health report.

Test-audit family:

- `test-quality-assurance` — scores a suite against an 8-dimension TDD rubric.
- `test-redundancy-triage` — classifies tests DELETE / MERGE / KEEP with confidence tiers.

The code-health leaves emit findings to one shared schema; the test-audit skills keep
their own report formats. Skills are developed and released here, installed once to a
skills root, then run against any target repo via `--root`.

## Install

```bash
node bin/install-repo-audit-skills.js --dest /absolute/path/to/skills --force
```

Default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise
`~/.codex/skills`.

## Validation

```bash
npm run check
```


