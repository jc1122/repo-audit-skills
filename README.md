# Repo Audit Skills

Deterministic, advisory repo-audit skills (`0.4.0`). Leaves never mutate the
audited repository and are run with `--root`.

## Skill families

- **Code health**: `code-health-audit-pipeline` plus `complexity-audit`,
  `duplication-audit`, `dead-code-audit`, `structure-audit`, `quality-audit`,
  `coverage-gap-audit`, `dependency-audit`, `repo-hygiene-audit`, and
  `docs-consistency-audit`.
- **Test health**: `test-audit-pipeline`, `test-quality-assurance`,
  `test-redundancy-triage`, and `test-effectiveness-audit`.
- **Standalone deliberate-run leaves**: `hotspot-audit`, `security-audit`.

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
