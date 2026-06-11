# Repo Audit Skills

Deterministic, advisory repo-audit skills (`0.5.2`). Leaves never mutate the
audited repository and are run with `--root`.

## v0.5.2 highlights

- Full-pytest aggregation now runs all 17 skill/root suites in isolated import
  contexts as part of `npm run check`.
- Security-audit supports counted `trusted_subprocess` suppressions, and the
  repo security baseline is ratcheted from 49 findings to 0.
- Hotspot-audit supports counted family policy suppressions for declared
  coupling pairs and explicit single-maintainer repositories while keeping
  churn-complexity findings unsuppressible.

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
