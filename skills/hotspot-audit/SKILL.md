---
name: hotspot-audit
version: 0.5.3
description: >
  Deterministic, advisory git-history hotspot audit. Mines commit history to
  identify churn hotspots (DECOMPOSE), temporally coupled files
  (RESTRUCTURE), and knowledge concentration (RESTRUCTURE) using only
  stdlib and git. Never mutates source.
---

# hotspot-audit

## Overview

A code-health leaf skill reporting churn hotspots, temporal coupling, and
knowledge concentration as advisory findings from `git log --numstat`.

**Standalone status:** not registered in `leaf_registry.json`. `--rev` and
`--max-commits` define a history window that changes with moving `HEAD`, so run
this leaf deliberately and independently from the reproducible umbrella.

## Quick Start

```bash
python3 scripts/hotspot_audit.py \
  --root /path/to/repo \
  --source-prefix src/ \
  --out-dir /tmp/hotspot
```

Add `--rev v1.0.0 --max-commits 200` to pin the history window.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--root` | required | Git repository root. |
| `--source-prefix` | `[]` | Root-relative scope prefix; repeatable. |
| `--out-dir` | required | Directory for output files. |
| `--config` | none | JSON object overriding `DEFAULT_THRESHOLDS`. |
| `--format` | `json` | Output report format: `json` or `md`. |
| `--rev` | `HEAD` | Git revision to analyse from. |
| `--max-commits` | `500` | Maximum commits of history to examine. |

## Exit Codes

- `0` -- clean (no findings).
- `1` -- advisory findings present.
- `2` -- tool/config/input error: git missing, not a git repo, invalid config,
  or no commits reachable from `--rev`.

## Output

- `hotspot_findings.json` -- sorted findings in the shared code-health schema.
- `hotspot_report.md` -- human-readable summary grouped by signal.
- stdout status JSON includes resolved `rev`, `max_commits`,
  `suppressed_solo_author`, `suppressed_own_test_pairs`, and
  `suppression_counts` for config-driven policy suppressions.

## Deterministic Pinned-Window Contract

Every run resolves `--rev` to a concrete SHA and examines at most
`--max-commits` entries. The SHA and max-commits are recorded in every
finding's `evidence_raw` and in stdout (`"rev": "<sha>", "max_commits": <N>`).
Runs with the same root, initial `--rev`, and `--max-commits` are
byte-deterministic.

## Default Thresholds And Policy

```json
{
  "min_churn_commits": 5,
  "min_churn_complexity_product": 1000,
  "min_coupling_ratio": 0.7,
  "min_coupling_changes": 5,
  "max_commit_files": 50,
  "min_author_share": 0.9,
  "min_author_commits": 10,
  "coupling_allow_pairs": [],
  "single_maintainer": false
}
```

Override only selected keys with `--config path/to/thresholds.json`.

`coupling_allow_pairs` is a list of glob pairs such as
`[["SKILL.md", "references/**"]]`. A temporal-coupling finding is suppressed
only when the two files match opposite sides of one declared pair, and the
suppression is counted as `declared_coupling`.

`single_maintainer: true` suppresses otherwise-reportable
author-concentration findings and counts them as `single_maintainer`.
`churn_complexity_product` findings are never suppressible by either policy.

## Finding Groups

### Churn Complexity -- `DECOMPOSE`

For in-scope files still on disk and touched by at least `min_churn_commits`
distinct commits, compute `product = churn * nloc`. Report when
`product >= min_churn_complexity_product`. Metric:
`churn_complexity_product`; severity `high` at >=4x threshold, `medium` at >=2x,
else `low`; confidence `medium`.

### Temporal Coupling -- `RESTRUCTURE`

For commits with `1 < len(files) <= max_commit_files`, report file pairs where
`co-changes >= min_coupling_changes` and
`co / min(churn_a, churn_b) >= min_coupling_ratio`. Source files paired with
their own tests are suppressed after thresholding and counted as
`suppressed_own_test_pairs`. Declared coupling pairs from
`coupling_allow_pairs` are also suppressed after thresholding and counted as
`declared_coupling`. Metric: `temporal_coupling_ratio`; severity `medium`;
confidence `medium`.

### Knowledge Concentration -- `RESTRUCTURE`

For files with `churn >= min_author_commits`, report when the top author's
commit share exceeds `min_author_share`. Single-author repositories skip this
group and report `suppressed_solo_author=true`. Repositories that explicitly
set `single_maintainer: true` suppress otherwise-reportable rows and count them
as `single_maintainer`. Metric: `author_concentration`; severity `low`;
confidence `low`.

## Honest Limits

- Git history only: non-git repos exit 2, not a finding.
- Deleted files are invisible; only files currently present on disk are examined.
- No rename detection: `--no-renames` treats renames as delete + add.
- Huge commits touching more than `max_commit_files` (default 50) are skipped
  for temporal coupling.
- Precision suppressions are counted: solo-author repositories, source-to-own
  test pairs, declared coupling pairs, and explicit single-maintainer
  author-concentration suppressions remain visible in stdout and the Markdown
  report.
- Churn-complexity rows are deliberately not suppressible by
  `coupling_allow_pairs` or `single_maintainer`; reduce the hotspot or record
  the advisory residue in the caller's ledger.
- Author names use `%an`; typos, email changes, or casing differences can dilute
  or concentrate authorship counts.
