# Code Health Skills

Standalone package of deterministic, advisory code-health skills.

Leaf skills (each independently runnable, never mutate source):

- `complexity-audit` — radon + lizard → SIMPLIFY / DECOMPOSE
- `duplication-audit` — jscpd / symilar → EXTRACT / MERGE
- `dead-code-audit` — vulture + ruff F-codes → DELETE
- `structure-audit` — grimp import graph → RESTRUCTURE
- `quality-audit` — ruff + ruff format + ty → LINT / FORMAT / TYPE

Umbrella:

- `code-health-audit-pipeline` — runs the leaves in parallel, merges and ranks
  findings, and emits a supervisor decision with exit codes 0/1/2.

Each skill emits findings to one shared schema. Skills are developed and released
here, installed once to a skills root, then run against any target repo via `--root`.

## Install

```bash
node bin/install-code-health-skills.js --dest /absolute/path/to/skills --force
```

Default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise
`~/.codex/skills`.

## Validation

```bash
npm run check
```

## Coexistence

This package installs alongside `repo-audit-skills` into the same skills root. Skill
names are disjoint and each package's installer touches only its own skills, so the
two never collide.
