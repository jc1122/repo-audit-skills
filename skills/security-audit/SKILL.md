---
name: security-audit
version: 0.4.0
description: >
  Deterministic, advisory security audit for Python. Wraps a pinned bandit
  (bandit==1.9.4) static analysis run and emits SECURITY findings (shared
  code-health schema). Optional advisory mode ingests a pip-audit-shaped JSON
  report for dependency vulnerabilities. Never mutates source; never hits the
  network in-band. STANDALONE — not part of the code-health umbrella registry.
---

# security-audit

## Overview

A code-health leaf skill that runs bandit static security analysis over a tree
and reports issues as advisory `SECURITY` findings. It is deliberately
STANDALONE (not registered in the umbrella `leaf_registry.json`): bandit on
subprocess-heavy tooling repositories produces a large, repo-specific baseline
that would bury the umbrella's self-audit signal, and it carries a heavier
dependency. Run it deliberately.

## Requirements

- `bandit==1.9.4` (pinned; verified on Python 3.14). Install with
  `pip install bandit==1.9.4`. The leaf probes for bandit via
  `importlib.util.find_spec` before running and exits with a tool error
  (exit 2) if it is absent.

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
  rule-based and ships an empty threshold dict).
- `--format {json,md}` — default json.
- `--advisory-report PATH` — optional pip-audit-shaped JSON (see Advisory mode).

## Output

- `security_findings.json` — sorted findings (shared schema).
- `security_report.md` — grouped summary.

## bandit to finding mapping

| bandit issue_severity | finding severity | bandit issue_confidence | finding confidence | metric_value |
|---|---|---|---|---|
| HIGH | high | HIGH | high | 3.0 |
| MEDIUM | medium | MEDIUM | medium | 2.0 |
| LOW | low | LOW | low | 1.0 |

Per bandit result: `signal = SECURITY`, `path` = result `filename` made
root-relative (POSIX), `line_start = line_number`, `line_end = max(line_range)`,
`symbol = test_name`, `metric_name = "bandit_<test_id>"`, `metric_threshold = 0.0`,
`evidence.tool = "bandit"`, `evidence.raw = "<issue_text> [<test_id>]"`,
`suggested_action = "Review and remediate <test_id> at <path>:<line>"`.
bandit exits 1 when it finds issues; exit codes outside {0,1} or unparseable
JSON are treated as a tool error.

## Advisory mode

`--advisory-report PATH` ingests a pip-audit-shaped JSON document:

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

Each package with a non-empty `vulns` list emits one `SECURITY` finding:
`path` = `pyproject.toml` if it exists under `--root`, else `<advisory>`;
`symbol` = package name; `metric_name = "dependency_vulnerabilities"`;
`metric_value = len(vulns)`; severity per the C-8 mapping (`critical`/`high`
to high, `medium`/null to medium, `low` to low); confidence `high`;
`evidence.tool = "advisory-report"`. No network access is ever performed
in-band; the report must be produced out of band.

## Exit codes

- `0` — clean (no findings).
- `1` — advisory findings present.
- `2` — tool/config error (bandit missing, bandit failure, unreadable advisory
  report, missing required args).

## Determinism and limits

Findings are sorted by the shared `sort_findings` key and use root-relative
POSIX paths, so output is byte-deterministic across runs for a fixed bandit
version. bandit is a static analyzer: it reports patterns, not proven exploits,
so every finding is advisory and needs human review. The pin (`bandit==1.9.4`)
is load-bearing for golden stability.
