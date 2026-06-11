# Repo Audit Skills

Deterministic, advisory repo-audit skills (`0.5.0`). Leaves never mutate the
audited repository and are run with `--root`.

## v0.5.0 highlights

- Docs-consistency supports `--exclude-prefix` and skips generated path
  placeholders such as `docs/audits/<run-id>/run_report.json`.
- Precision suppressions are counted in reports for placeholder docs tokens,
  solo-author hotspot findings, own-test temporal-coupling pairs,
  test-referenced vulture findings, and config-gated format checks.
- Self-audit duplication identities use content hashes instead of line ranges,
  and the coverage gate now detects stale baselines through `gate_common`.
- Test-effectiveness reports mutmut baseline failures as clean tool errors.

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
