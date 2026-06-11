---
name: security-audit
version: 0.5.3
description: >
  Deterministic, advisory security audit for Python. Wraps a pinned bandit
  (bandit==1.9.4) static analysis run and emits SECURITY findings (shared
  code-health schema). Optional advisory mode ingests a pip-audit-shaped JSON
  report for dependency vulnerabilities. Never mutates source; never hits the
  network in-band. STANDALONE — not part of the code-health umbrella registry.
---

# security-audit

## Overview

Runs bandit static analysis and reports advisory `SECURITY` findings. It is
deliberately standalone (not registered in `leaf_registry.json`) because bandit
baselines are repo-specific and dependency-heavy.

## Requirements

- `bandit==1.9.4` (pinned; verified on Python 3.14). Install with
  `pip install bandit==1.9.4`. Missing bandit exits `2`.

## Quick Start

```bash
python3 scripts/security_audit.py \
  --root /path/to/repo \
  --source-prefix src/ \
  --out-dir /tmp/security
```

bandit is invoked as `python -m bandit -r <targets> -f json -q`, where
`<targets>` are the existing `--source-prefix` directories under `--root` (or
`--root` itself when no prefix is given).

## Flags

- `--root` (required) — tree to scan.
- `--source-prefix` (repeatable) — path prefix(es) relative to `--root`; only
  existing prefixes become bandit targets.
- `--out-dir` (required) — output directory.
- `--config` — JSON file overriding thresholds (plumbing; this leaf is
  rule-based and ships a disabled-by-default `trusted_subprocess` policy.
- `--format {json,md}` — default json.
- `--advisory-report PATH` — optional pip-audit-shaped JSON (see Advisory mode).

## Output

- `security_findings.json` — sorted findings (shared schema).
- `security_summary.json` — finding count plus counted suppression records.
- `security_report.md` — grouped summary.

## Trusted subprocess policy

Default behavior suppresses nothing. Repos that intentionally shell out to
trusted internal tools can opt in with:

```json
{
  "trusted_subprocess": {
    "enabled": true,
    "rules": ["B404", "B603", "B607"],
    "path_globs": ["scripts/**", "skills/*/scripts/**", "shared/**"]
  }
}
```

Only matching Bandit rule ids on matching root-relative paths are suppressed.
Every suppressed row is counted in `security_summary.json` under
`suppressed_findings` with class `trusted_subprocess`, and markdown renders the
count. Other rules on the same file still emit normally.

## Mapping

| bandit issue_severity | finding severity | bandit issue_confidence | finding confidence | metric_value |
|---|---|---|---|---|
| HIGH | high | HIGH | high | 3.0 |
| MEDIUM | medium | MEDIUM | medium | 2.0 |
| LOW | low | LOW | low | 1.0 |

Each bandit result maps to `signal = SECURITY`, root-relative POSIX `path`,
`symbol = test_name`, `metric_name = "bandit_<test_id>"`, threshold `0.0`,
`evidence.tool = "bandit"`, and a review/remediate suggested action. bandit
exit `1` means findings; other unexpected exits or bad JSON are tool errors.

## Advisory mode

`--advisory-report PATH` ingests a pip-audit-shaped JSON document generated out
of band:

```json
{
  "source": "pip-audit",
  "generated_utc": "2026-06-10T00:00:00Z",
  "packages": [
    {
      "name": "requests",
      "installed_version": "2.19.0",
      "latest_version": "2.32.3",
      "vulns": [
        {"id": "PYSEC-2018-28", "severity": "high", "fix_versions": ["2.20.0"]}
      ]
    }
  ]
}
```

Each package with `vulns` emits one `SECURITY` finding: path `pyproject.toml`
when present else `<advisory>`, symbol package name, metric
`dependency_vulnerabilities`, value `len(vulns)`, severity mapping
`critical/high -> high`, `medium/null -> medium`, `low -> low`, confidence
`high`, tool `advisory-report`. No in-band network access occurs.

## Exit codes

- `0` — clean (no findings).
- `1` — advisory findings present.
- `2` — tool/config error (bandit missing, bandit failure, unreadable advisory
  report, missing required args).

## Determinism and limits

Findings are sorted by shared `sort_findings` and use root-relative POSIX paths,
so output is byte-deterministic for fixed `bandit==1.9.4`. bandit reports
patterns, not proven exploits; every finding needs human review.

Limits:
- `trusted_subprocess` is for pinned, internal, shell-free subprocess wrappers
  only. It is disabled by default and never hides rows silently: suppressions
  are counted in JSON and markdown output.
