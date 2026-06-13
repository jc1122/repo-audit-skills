---
name: growth-audit
version: 0.5.21
description: >
  Deterministic, advisory surface-growth audit between git revisions.
  Computes tracked-files, net-LOC, docs-LOC, dependency-declaration,
  and CLI-flag growth from `git diff --numstat` and reports positive
  deltas beyond configured allowances. Language-agnostic
  (languages: ["*"]).  Never mutates source.
---

# growth-audit

## Overview

A code-health leaf skill that detects *surface* growth between two git
revisions — tracked files, net lines of code (additions minus deletions),
documentation lines, dependency declarations, and CLI flag additions.  All
metrics are language-blind and derived from `git diff`.

**Standalone status:** not registered in `leaf_registry.json`.  Growth is a
moving-target signal that depends on the baseline revision the caller chooses;
it is deliberately run outside the reproducible umbrella.

## R2 Admission

- **Signal made visible:** unjustified surface growth.  Surface metrics
  (files, LOC, dependencies, flags) can grow silently without any audit
  signal in the umbrella leaves.  `growth-audit` fills that gap.
- **hotspot-audit mines history for risk concentration, not surface
  growth, and its decision classes differ.**  Hotspot reports churn
  hotspots (`DECOMPOSE`), temporal coupling (`RESTRUCTURE`), and knowledge
  concentration (`RESTRUCTURE`) — all derived from the shape and authors of
  commit history.  Growth-audit reports `RESTRUCTURE` for positive deltas
  between two pinned revisions.  The two leaves share the `RESTRUCTURE`
  signal but operate on different inputs and answer different questions.
- **Sunset:** if `hotspot-audit` grows a trend engine that can compare
  revision-pair surface deltas with the same configurability, merge
  the metric collectors into hotspot and purge this leaf.

## Quick Start

```bash
python3 scripts/growth_audit.py \
  --root /path/to/repo \
  --baseline-rev v1.0.0 \
  --out-dir /tmp/growth
```

Optionally add `--rev v2.0.0` to compare against a different target
(default: `HEAD`).

## Flags

| Flag | Default | Description |
|---|---|---|
| `--root` | required | Git repository root. |
| `--out-dir` | required | Directory for output files. |
| `--baseline-rev` | required | Baseline git revision to compare against. |
| `--rev` | `HEAD` | Target revision to compare to. |
| `--format` | `json` | Output report format: `json` or `md`. |
| `--config` | none | JSON object with `allow_growth` array for suppressions. |

## Exit Codes

- `0` — clean (no findings, all growth within allowances or zero).
- `1` — advisory findings present.
- `2` — tool/config/input error: git missing, not a git repo, invalid
  config JSON, or unresolvable revisions.

## Output

- `growth-audit_findings.json` — sorted findings in the shared code-health
  schema.
- `growth-audit_summary.json` — raw metric deltas, suppression counts,
  overflow counts, and resolved SHAs.
- `growth-audit_report.md` — human-readable summary (when `--format md`).

## Metrics

| Metric | Source |
|---|---|
| `tracked_files_growth` | `git diff --name-only --diff-filter=A` |
| `net_loc_growth` | `git diff --numstat` (additions − deletions) |
| `docs_loc_growth` | `git diff --numstat` filtered to doc globs |
| `dependency_growth` | new dependency lines across known manifests (requirements.txt, pyproject.toml, package.json, Cargo.toml, go.mod, Gemfile, Pipfile) |
| `cli_flag_growth` | new CLI-flag / option declarations in changed source files |

## Configurable Allowances

```json
{
  "allow_growth": [
    {"metric": "tracked_files_growth", "max_delta": 5, "reason": "planned"},
    {"metric": "net_loc_growth",      "max_delta": 500, "reason": "sprint"}
  ]
}
```

Growth within `max_delta` is suppressed and counted in the summary.
Growth beyond `max_delta` emits a finding with the overflow recorded.
Metrics not mentioned in any allowance rule emit a finding for any
positive delta.

## Finding Groups

### Surface Growth — `RESTRUCTURE`

All growth findings use the `RESTRUCTURE` signal.  Severity is derived
from the delta magnitude per metric:

| Metric | low | medium | high |
|---|---|---|---|
| `tracked_files_growth` | ≤10 | 11–20 | >20 |
| `dependency_growth` | ≤10 | 11–20 | >20 |
| `net_loc_growth` | ≤500 | 501–2000 | >2000 |
| `docs_loc_growth` | ≤500 | 501–2000 | >2000 |
| `cli_flag_growth` | ≤5 | 6–15 | >15 |

Confidence is `high` for overflow-from-allowance findings and `medium`
for un-allowanced metrics.

## Honest Limits

- **Git history only:** non-git repos exit 2, not a finding.
- **Surface growth only:** this leaf does not detect dead flags, dead
  imports, or unused dependencies.  Dead-flag detection is deferred to
  SP13.  Use `dead-code-audit` for unused symbols and `dependency-audit`
  for unused dependencies.
- **`cli_flag_growth` is Python-grep best-effort and reads 0 elsewhere.**
  The regex patterns match Python argparse/click/typer and a handful of
  Rust/Golang conventions.  Flags added in other languages or through
  indirect frameworks will not be detected.
- Deleted files are invisible to `tracked_files_growth`.
- `git diff --no-renames` is not applied; renames may count as delete+add
  pairs, inflating net-LOC deltas.
- Dependency detection is heuristic and does not parse TOML/JSON/Go-mod
  into structured dependency trees.  Commented-out lines are skipped, but
  inactive dependency blocks may still match.
