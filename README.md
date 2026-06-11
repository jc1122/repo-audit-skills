# Repo Audit Skills

Standalone package of deterministic, advisory repo-audit skills — a code-health family and a test-audit family.

Leaf skills (each independently runnable, never mutate source):

- `complexity-audit` — radon + lizard → SIMPLIFY / DECOMPOSE
- `duplication-audit` — jscpd / symilar → EXTRACT / MERGE
- `dead-code-audit` — vulture + ruff F-codes → DELETE
- `structure-audit` — grimp import graph → RESTRUCTURE
- `quality-audit` — ruff + ruff format + ty → LINT / FORMAT / TYPE
- `coverage-gap-audit` — coverage.py JSON → TEST (untested / under-tested files)

Umbrellas:

- `code-health-audit-pipeline` — runs the code-health leaves in parallel, merges and
  ranks findings, and emits a supervisor decision with exit codes 0/1/2.
- `test-audit-pipeline` — orchestrates coverage collection, test-quality scoring, and
  redundancy triage into a unified test-health report.

Test-audit family:

- `test-quality-assurance` — scores a suite against an 8-dimension TDD rubric.
- `test-redundancy-triage` — classifies tests DELETE / MERGE / KEEP with confidence tiers.

SP7 leaves (v0.4.0):

- `hotspot-audit` — git-history mining (churn × complexity, temporal coupling, knowledge concentration) → DECOMPOSE / RESTRUCTURE. Standalone (history window unpinnable by the umbrella).
- `dependency-audit` — declared vs imported deps (tomllib + ast; optional vuln advisory) → DELETE / RESTRUCTURE.
- `repo-hygiene-audit` — tracked-tree artifacts + release hygiene (`languages: ["*"]`) → DELETE / RESTRUCTURE.
- `docs-consistency-audit` — docs vs reality (command introspection; docstring group opt-in) → RESTRUCTURE.
- `security-audit` — bandit → SECURITY. Standalone (deliberate-run tool).
- `test-effectiveness-audit` — mutmut mutation testing → TEST. Registered with `requires: {mutation_scope}` (pipeline plumbing is future work).

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


