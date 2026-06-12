---
name: dependency-audit
version: 0.5.5
description: >
  Deterministic, advisory dependency audit for Python. Compiles declared
  dependencies (pyproject.toml [project] or requirements*.txt) against
  AST-collected imports and reports unused declarations, undeclared imports,
  test-only runtime usage, and optional C-8 advisory enrichment. Uses stdlib
  only, requires Python >=3.11, never mutates source, and never makes network
  calls.
---

# dependency-audit

Deterministic, advisory Python dependency audit for repository-level dependency
hygiene.

Requires Python >=3.11 (`tomllib`); no runtime dependencies beyond stdlib.

## Quick Start

```bash
python3 scripts/dependency_audit.py --root /path/to/repo --out-dir /tmp/dependency-audit
```

Use `--source-prefix` to limit scan scope:

```bash
python3 scripts/dependency_audit.py \
  --root /path/to/repo --source-prefix src/ --source-prefix libs/ \
  --out-dir /tmp/dependency-audit
```

Full rule details are documented in the [usage notes](./docs/usage.md).

## CLI

- `--root` (required): repository root.
- `--source-prefix` (optional, repeatable): root-relative include prefixes.
- `--out-dir` (required): output directory.
- `--config`: JSON overriding `DEFAULT_THRESHOLDS`.
- `--format {json,md}`: report format (`json` default).
- `--advisory-report`: external advisory report path (C-8 shape).

## Exit Codes

- `0` (`EXIT_CLEAN`): clean or no-manifest scan.
- `1` (`EXIT_FINDINGS`): findings emitted.
- `2` (`EXIT_ERROR`): missing args/parse/runtime errors.

## Outputs

- `dependency_findings.json`
- `dependency_report.md`
- one-line JSON status on stdout.

## Findings and Signals

Findings follow `health_common.Finding` and use `RESTRUCTURE` for undeclared
imported/runtime/test-scope/advisory cases; unused declared dependencies use
`DELETE`.

## Core contract

- Declared dependencies are read from root `pyproject.toml [project]` and root
  `requirements*.txt` files.
- Imports are gathered from AST over `.py` files.
- No-manifest repositories do not fail: all dependency audits are skipped,
  findings are empty, and exit is `0`.
- No network calls are made.
- `--config` is accepted for parity; `DEFAULT_THRESHOLDS = {}` is a no-op.
- The umbrella registry runs the offline core only; it never passes
  `--advisory-report`.

## Constraints / explicit limitations

- Dynamic imports are not discoverable by AST top-level scan.
- Import-to-distribution mapping is heuristic and imperfect.
- Requirements parsing is intentionally naive (for `requirements*.txt` lines only).
- Editable installs and non-root install metadata are not modeled.

## Advisory report mode

`--advisory-report` can enrich findings from an external C-8 report. Advisory
findings use `RESTRUCTURE` (never `SECURITY`).
