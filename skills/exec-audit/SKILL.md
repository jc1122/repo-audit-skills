---
name: exec-audit
version: 0.7.5
description: >
  Deterministic, advisory execution audit for any repository. Detects duplicate or
  serial runner invocations in npm scripts, parses JUnit XML for slow tests, and
  checks for benchmark entrypoint absence. Language-agnostic (languages: ["*"]).
  Never mutates source.
---

# exec-audit

## Overview

Repo-agnostic, stdlib-only execution audit. It operates on three independent
detectors:

1. **Duplicate/serial execution** — expands `npm run <name>` chains and flags
   runners invoked more than once within an expanded script.
2. **Slow-test detection** — parses optional JUnit XML reports and flags
   testcases whose duration exceeds a configurable threshold.
3. **Benchmark gap** — checks whether the repository defines any benchmark
   entrypoint (pytest-benchmark, npm bench script, benchmark/ directory, etc.).

Advisory only; never mutates the audited repository.

## R2 Admission Statement

- **Signal made visible**: duplicate/serial/slow execution and benchmark absence —
  patterns that no other leaf currently detects. This leaf exposes `PERF`-signal
  findings for execution-level waste that code-health and test-health leaves do
  not surface.
- **No existing leaf** reads execution configs or JUnit XML. The gap in the
  repo-audit coverage matrix is real: existing leaves analyze source code,
  structure, dependencies, tests, and hygiene, but none inspects *how* the repo
  executes its scripts or whether its test suite harbors slow cases.
- **Sunset policy**: if a language-native build-graph analyzer leaf (e.g., a
  Bazel/Pants/Meson-aware leaf) supersedes this leaf, fold the duplicate-execution
  and benchmark-gap detectors there and purge this leaf.

## Limits

- **Makefile / tox.ini / noxfile.py** parsing for benchmark targets is deferred
  to SP13. The benchmark-gap detector reads these files as plain text but does
  not parse structured targets.
- **Workflow YAML extraction** is line-based best-effort. The leaf does not
  build a DAG or resolve `needs`/`uses` relationships.
- Only npm `scripts` expansion is supported for duplicate-execution detection.
  Other script runners (yarn, pnpm, nx, turbo) are out of scope.

## Quick Start

```bash
python3 scripts/exec_audit.py \
  --root /path/to/repo \
  --out-dir /tmp/exec-audit
```

Optionally supply JUnit XML:

```bash
python3 scripts/exec_audit.py \
  --root /path/to/repo \
  --out-dir /tmp/exec-audit \
  --junit-xml junit.xml \
  --junit-xml artifacts/test-results.xml
```

## Flags

| Flag | Required | Description |
|---|---|---|
| `--root PATH` | yes | Repository root to audit. |
| `--out-dir PATH` | yes | Output directory for findings and report. |
| `--junit-xml PATH` | no | Repeatable. Path to a JUnit XML report for slow-test detection. |
| `--config PATH` | no | JSON file overriding default thresholds. |
| `--format {json,md}` | no | Report format (default `json`). |

## Thresholds

```json
{
  "slow_test_threshold_s": 1.0,
  "slow_test_cap_s": 300.0,
  "max_runner_occurrences": 1
}
```

Override with `--config thresholds.json`.

## Detector Details

### Duplicate-execution detection

Expands `npm run <name>` chains recursively, splits on `&&` and `;`, and
counts distinct runner/path invocations. Emits one `PERF` finding per unique
`(runner, count)` pair when count exceeds `max_runner_occurrences`.

| Signal | Severity | Confidence | metric_name |
|---|---|---|---|
| PERF | medium | high | `duplicate_execution` |

### Slow-test detection

Parses JUnit XML supplied via `--junit-xml`. Each testcase whose `time`
attribute exceeds `slow_test_threshold_s` produces a `PERF` finding. Durations
are capped at `slow_test_cap_s` in the metric value.

| Signal | Severity | Confidence | metric_name |
|---|---|---|---|
| PERF | medium | high | `slow_test` |

### Benchmark gap detection

Checks for the presence of any benchmark entrypoint marker across the
repository. Emits at most one low-confidence `info` finding when no marker is
found.

Markers checked: pytest-benchmark dependency, `bench`/`benchmark` npm scripts,
`conftest.py` with benchmark marker registration, directories named
`benchmarks` or `bench`, `@pytest.mark.benchmark` in test files, benchmark mentions in
Makefile/tox.ini/noxfile.py (plain-text scan).

| Signal | Severity | Confidence | metric_name |
|---|---|---|---|
| PERF | info | low | `benchmark_entrypoints_missing` |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Clean — no findings. |
| 1 | Advisory findings present. |
| 2 | Tool/config error (missing required args, unreadable JUnit XML, invalid config). |

## Output

- `exec-audit_findings.json` — sorted findings in the shared schema.
- `exec-audit_report.md` — human-readable summary.

## Standalone Status

This leaf is standalone — not registered in the code-health umbrella
`leaf_registry.json`. It can run against any repository regardless of primary
language, subject to the limits noted above.
