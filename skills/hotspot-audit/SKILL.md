---
name: hotspot-audit
version: 0.4.0
description: >
  Deterministic, advisory git-history hotspot audit. Mines commit history to
  identify churn hotspots (DECOMPOSE), temporally coupled files
  (RESTRUCTURE), and knowledge concentration (RESTRUCTURE) using only
  stdlib and git. Never mutates source.
---

# hotspot-audit

## Overview

A code-health leaf skill reporting churn hotspots, temporal coupling, and
knowledge concentration as advisory findings.  It mines git history directly
(via `git log --numstat`) and is fully deterministic for a given repo state,
branch tip, and history depth.

**Standalone status:** This skill is NOT registered in the umbrella pipeline
(`leaf_registry.json`).  Its `--rev` and `--max-commits` flags define a
history window that varies with moving `HEAD` -- unpinned runs can produce
different results on every commit.  The self-audit ratchet and umbrella
orchestrator require reproducible runs, so this skill is run deliberately
and independently.

## Quick Start

```bash
python3 scripts/hotspot_audit.py \
  --root /path/to/repo \
  --source-prefix src/ \
  --out-dir /tmp/hotspot
```

With explicit history window:

```bash
python3 scripts/hotspot_audit.py \
  --root /path/to/repo \
  --rev v1.0.0 \
  --max-commits 200 \
  --out-dir /tmp/hotspot
```

## Flags

| Flag | Description | Default |
|---|---|---|
| `--root` | Path to git repository (required). |  --  |
| `--source-prefix` | Path prefix(es) relative to `--root` to scope analysis. Repeatable. | `[]` (entire repo) |
| `--out-dir` | Directory for output files (required). |  --  |
| `--config` | JSON file overriding `DEFAULT_THRESHOLDS`. |  --  |
| `--format` | Output report format: `json` or `md`. | `json` |
| `--rev` | Git revision to analyse from. | `HEAD` |
| `--max-commits` | Maximum commits of history to examine. | `500` |

## Exit Codes

- `0`  --  clean (no findings).
- `1`  --  advisory findings present.
- `2`  --  tool/config/input error (git missing, not a git repo, invalid config,
  no commits reachable from `--rev`).

## Output

- `hotspot_findings.json`  --  sorted findings in the shared code-health schema.
- `hotspot_report.md`  --  human-readable summary grouped by signal.
- stdout status JSON includes resolved `rev`, `max_commits`,
  `suppressed_solo_author`, and `suppressed_own_test_pairs`.

## Deterministic Pinned-Window Contract

Every run resolves `--rev` to a concrete commit SHA and examines at most
`--max-commits` entries of history.  Both the resolved SHA and max-commits
are recorded in every finding's `evidence_raw` and in the stdout status line
(`"rev": "<sha>", "max_commits": <N>`).  Two runs with the same root, same
initial `--rev`, and same `--max-commits` are byte-deterministic.

## Default Thresholds

```json
{
  "min_churn_commits": 5,
  "min_churn_complexity_product": 1000,
  "min_coupling_ratio": 0.7,
  "min_coupling_changes": 5,
  "max_commit_files": 50,
  "min_author_share": 0.9,
  "min_author_commits": 10
}
```

Override with `--config path/to/thresholds.json` containing a JSON object;
only the provided keys are replaced.

## Finding Groups

### Churn Complexity  --  `DECOMPOSE`

Files with high churn x NLOC product.  For every in-scope file that still
exists on disk and has been touched by at least `min_churn_commits` distinct
commits: compute `product = churn * nloc`.  Report when
`product >= min_churn_complexity_product`.

- **Metric:** `churn_complexity_product`
- **Severity:** `high` if >=4x threshold, `medium` if >=2x, else `low`
- **Confidence:** `medium`
- **Suggested action:** split the file along its change axes.

### Temporal Coupling  --  `RESTRUCTURE`

Pairs of files that change together in the same commits.  Considers commits
with `1 < len(files) <= max_commit_files`.  Reports pairs where
`co-changes >= min_coupling_changes` and
`ratio = co / min(churn_a, churn_b) >= min_coupling_ratio`.  Source files
paired with their own tests (for example `foo.py` with a matching test_foo
module under tests) are suppressed after thresholding and counted as
`suppressed_own_test_pairs`.

- **Metric:** `temporal_coupling_ratio`
- **Severity:** `medium`
- **Confidence:** `medium`
- **Suggested action:** move the shared concern into one module or merge the files.

### Knowledge Concentration  --  `RESTRUCTURE`

Files dominated by a single author.  For files with
`churn >= min_author_commits`, report when the top author's share of commits
exceeds `min_author_share`.  Single-author repositories skip this group and
report `suppressed_solo_author=true`.

- **Metric:** `author_concentration`
- **Severity:** `low`
- **Confidence:** `low`
- **Suggested action:** schedule reviews or pairing sessions on this file.

## Honest Limits

- **Git history only.**  This skill relies entirely on `git log --numstat`.
  Non-git repos produce a clean error exit (2), not a finding.
- **Deleted files are invisible.**  Only files currently present on disk are
  examined; a file that churned heavily and was deleted contributes nothing.
- **No rename detection.**  `--no-renames` is passed to `git log`; renamed
  files are treated as delete + add and do not carry churn forward.
- **Huge commits are skipped.**  Commits touching more than `max_commit_files`
  (default 50) are excluded from temporal-coupling analysis to avoid noise
  from mechanical refactors and merge commits.
- **Precision suppressions are counted.**  Solo-author repositories and
  source-to-own-test temporal pairs are filtered as known FP classes, but their
  counters remain visible in stdout and the Markdown report.
- **Author names are heuristic.**  The analysis uses `%an` (author name) from
  git log  --  typos, email changes, or inconsistent casing by the same person
  will artificially dilute or concentrate authorship counts.
