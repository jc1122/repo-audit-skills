---
name: repo-hygiene-audit
version: 0.3.0
description: >
  Deterministic, advisory tracked-tree hygiene and release hygiene audit for any
  repository. Checks tracked artifacts, gitignore violations, oversized files,
  broken symlinks, conflicting tool configs, version mismatches, missing CI,
  and missing LICENSE. Language-agnostic (languages: ["*"]). Never mutates source.
---

# repo-hygiene-audit

## Overview

A language-agnostic audit leaf that inspects the tracked-tree and release
hygiene of any repository using `git ls-files` and plain filesystem checks.
Eight check groups run deterministically and produce advisory findings in the
shared code-health schema.

This skill is **language-agnostic** by design. Its umbrella registration uses
`languages: ["*"]` (supported after the pipeline wildcard change lands in a
future integration track). On any repo — Python or not — the hygiene checks are
applicable.

## Quick Start

```bash
python3 scripts/repo_hygiene_audit.py \
  --root /path/to/any/repo \
  --source-prefix src/ \
  --out-dir /tmp/repo-hygiene
```

## CLI Flags

| Flag | Required | Description |
|---|---|---|
| `--root PATH` | yes | Repository root to audit. |
| `--source-prefix PREFIX` | no | Repeatable. Path prefix(es) relative to `--root`. When given, EVERY finding (including release-hygiene paths such as `package.json`, `.github`, `LICENSE`) is filtered to those whose path starts with a prefix. |
| `--out-dir PATH` | yes | Output directory for findings and report. |
| `--config PATH` | no | JSON file overriding `DEFAULT_THRESHOLDS`. |
| `--format {json,md}` | no | Output format for the report file (default `json`). |

No extra flags. The leaf CLI contract mirrors the family standard.

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

```
DEFAULT_THRESHOLDS = {"max_tracked_file_bytes": 1048576}
```

Override via `--config` (a JSON file whose keys are merged into the defaults).

## Check Groups

All eight groups produce findings with signal, severity, and confidence as shown.

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

On a non-git root (`git rev-parse --git-dir` fails):

- Git-dependent groups (tracked artifact, tracked-but-gitignored, oversized tracked file, broken symlink) are **skipped**.
- The stdout status line gains `"git": false`.
- Config/release-hygiene groups (conflicting tool configs, version mismatch, missing CI, missing LICENSE) still run.
- Exit codes follow the normal contract.

If the **git binary itself is missing** (`FileNotFoundError` on subprocess call), this is a `ToolError` → exit 2.

## Prefix Rule (Self-Audit Critical)

When `--source-prefix` is provided, **every** finding — including release-hygiene findings whose paths are `package.json`, `.github`, `LICENSE`, etc. — is dropped unless its `path` starts with one of the given prefixes. This ensures the leaf produces zero findings under repo-audit-skills self-audit (where prefixes cover only `shared`, `scripts`, and `skills/*/scripts`).

## Honest Limits

This skill is designed to be **useful on stranger repos** — it checks what any repository should have, regardless of language or toolchain. It does **not** enforce family-contract checks specific to the repo-audit-skills family:

- Version synchronization across multiple `SKILL.md` files in this repo
- Installer list completeness
- Self-audit baseline membership
- Leaf registry membership

Those checks are owned by the per-repo release scripts (`scripts/check_release.py`, `scripts/check_coverage_gap.py`, etc.) and are explicitly NOT part of this skill.
