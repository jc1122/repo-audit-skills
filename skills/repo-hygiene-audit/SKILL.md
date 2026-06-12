---
name: repo-hygiene-audit
version: 0.5.9
description: >
  Deterministic, advisory tracked-tree hygiene and release hygiene audit for any
  repository. Checks tracked artifacts, gitignore violations, oversized files,
  broken symlinks, conflicting tool configs, version mismatches, missing CI,
  and missing LICENSE. Language-agnostic (languages: ["*"]). Never mutates source.
---

# repo-hygiene-audit

## Overview

Language-agnostic tracked-tree and release-hygiene audit. It uses `git ls-files`
and filesystem checks, emits shared-schema advisory findings, and is registered
with `languages: ["*"]`.

## Quick Start

```bash
python3 scripts/repo_hygiene_audit.py \
  --root /path/to/any/repo \
  --source-prefix src/ \
  --out-dir /tmp/repo-hygiene
```

## Flags

| Flag | Required | Description |
|---|---|---|
| `--root PATH` | yes | Repository root to audit. |
| `--source-prefix PREFIX` | no | Repeatable. Path prefix(es) relative to `--root`. When given, EVERY finding (including release-hygiene paths such as `package.json`, `.github`, `LICENSE`) is filtered to those whose path starts with a prefix. |
| `--out-dir PATH` | yes | Output directory for findings and report. |
| `--config PATH` | no | JSON file overriding `DEFAULT_THRESHOLDS`. |
| `--format {json,md}` | no | Output format for the report file (default `json`). |

No extra flags; the leaf follows the family CLI contract.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Clean — no findings. |
| 1 | Advisory findings present. |
| 2 | Tool or input error (missing required args, git binary missing, invalid config, etc.). |

## Output

- `repo-hygiene_findings.json` — sorted findings in the shared schema.
- `repo-hygiene_report.md` — human-readable summary.

## Thresholds

`DEFAULT_THRESHOLDS = {"max_tracked_file_bytes": 1048576}`. `--config` JSON
keys are merged into the defaults.

## Check Groups

All eight groups produce deterministic findings:

| Group | Detection | Signal | Severity | Confidence | metric_name |
|---|---|---|---|---|---|
| Tracked artifact | Tracked path containing `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, or name matching `*.pyc`, `*.pyo`, `.coverage`, `.coverage.*`, `.DS_Store`, `*.orig`, `*.rej` | DELETE | medium | high | `tracked_artifact` (value 1.0, thr 0.0) |
| Tracked-but-gitignored | `git ls-files -ci --exclude-standard -z` entry | DELETE | medium | high | `tracked_ignored` (value 1.0, thr 0.0) |
| Oversized tracked file | Tracked file stat size > `max_tracked_file_bytes` | RESTRUCTURE | medium | high | `tracked_file_bytes` (value=size, thr=max) |
| Broken symlink | Tracked `Path.is_symlink()` with unresolvable target | DELETE | low | high | `broken_symlink` (value 1.0, thr 0.0) |
| Conflicting tool configs | >1 pytest config (`pytest.ini`, `setup.cfg [tool:pytest]`, `pyproject.toml [tool.pytest.ini_options]`) or >1 ruff config (`ruff.toml`, `.ruff.toml`, `pyproject.toml [tool.ruff]`) — finding per second-and-later config file | RESTRUCTURE | medium | high | `conflicting_configs` (value=count, thr 1.0) |
| Version mismatch | Collect versions from `pyproject.toml`, `package.json`, `CHANGELOG*.md`, `*/__init__.py`; >1 distinct value → finding per disagreeing source | RESTRUCTURE | medium | high | `version_mismatch` (value=distinct count, thr 1.0) |
| Missing CI | No `.github/workflows/*.yml` or `*.yaml` under root | RESTRUCTURE | low | high | `ci_missing` (value 1.0, thr 0.0) |
| Missing LICENSE | No root `LICENSE*` file | RESTRUCTURE | low | high | `license_missing` (value 1.0, thr 0.0) |

## Non-Git Degradation

If `git rev-parse --git-dir` fails, git-dependent groups are skipped, stdout
adds `"git": false`, release/config groups still run, and normal exit codes
apply. If the git binary is missing, the leaf exits `2`.

## Prefix Rule

When `--source-prefix` is provided, every finding, including release-hygiene
paths such as `package.json`, `.github`, and `LICENSE`, is dropped unless its
path starts with a prefix.

## Honest Limits

This leaf checks generic repository hygiene. It does not enforce
repo-audit-skills-specific release contracts:

- Version synchronization across multiple `SKILL.md` files in this repo
- Installer list completeness
- Self-audit baseline membership
- Leaf registry membership

Those checks are owned by the per-repo release scripts (`scripts/check_release.py`, `scripts/check_coverage_gap.py`, etc.) and are explicitly NOT part of this skill.
