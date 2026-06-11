---
name: test-effectiveness-audit
version: 0.4.0
description: >
  Deterministic, advisory mutation-testing audit for Python. Wraps mutmut==3.6.0
  to measure per-module mutation kill rates, emitting TEST findings (shared
  code-health schema) for modules whose kill rate falls below the configured
  threshold. Never mutates source in-place; runs in a sandbox copy. The
  machine-readable answer to "how good are my tests at catching bugs?".
---

# test-effectiveness-audit

## Overview

A code-health leaf skill that uses mutation testing to evaluate test suite
effectiveness. It runs `mutmut` on scoped Python source files and reports
per-module kill rates as advisory TEST findings.

**Key tool:** `mutmut==3.6.0` (pinned; verified on Python 3.14).

## Quick Start

```bash
python3 scripts/test_effectiveness_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --paths scoped_paths.txt \
  --tests-dir tests \
  --max-mutants 200 \
  --out-dir /tmp/test-effectiveness
```

## Required Flags

This leaf **refuses unscoped runs** (exit 2). Mutation testing an entire
repository without bounds can take hours and produce noisy results. You must
provide:

| Flag | Description |
|---|---|
| `--paths FILE` | Newline-separated, root-relative `.py` files or directories to mutate (e.g., the top-N hotspot paths). |
| `--tests-dir REL` | Root-relative test directory to copy into the sandbox. |
| `--max-mutants INT` | Upper bound on estimated mutants; if the scope's AST `FunctionDef`/`AsyncFunctionDef` count × `estimated_mutants_per_def` exceeds this, the run is refused with `ToolError`. |

Missing any of these three → status-error JSON on stdout + exit 2 with an
explanation of why scoping is required.

## Standard Leaf Flags

Per the leaf CLI contract (`--root`, `--source-prefix`, `--out-dir`, `--config`,
`--format`) — see the leaf CLI contract for full descriptions. `--source-prefix`
is accepted and stored but the sandbox currently copies only `--paths` entries
and `--tests-dir`; it is recorded in the status line for determinism.

## Output

- `test-effectiveness_findings.json` — sorted findings (shared schema).
- `test-effectiveness_report.md` — human-readable summary.

## Exit Codes

- `0` — clean (no modules below kill-rate threshold).
- `1` — advisory TEST findings present.
- `2` — tool/config/scope error (missing required flags, tool not installed,
  scope too large, `mutmut` timeout, etc.).

## Thresholds (via `--config` or defaults)

| Key | Default | Description |
|---|---|---|
| `min_kill_rate` | `0.8` | Per-module kill rate below this threshold emits a TEST finding. |
| `mutmut_timeout_seconds` | `600` | Hard timeout for `mutmut run` as a subprocess. |
| `estimated_mutants_per_def` | `8` | Multiplier for the AST-based budget estimate. |

## Sandbox Protocol

**mutmut loads its config at import time** — even `mutmut --help` crashes
unless the CWD contains a `setup.cfg` with `[mutmut] source_paths=...`.
To avoid littering the target repo and to satisfy this quirk, all mutmut
invocations run inside a sandbox:

1. Create `work = <out-dir>/.mutmut-work` (wiped at the start of each run).
2. Copy each `--paths` entry to `work/<same relpath>`.
3. Copy `--tests-dir` to `work/<same relpath>`.
4. Write `work/setup.cfg`:
   ```
   [mutmut]
   source_paths=<space-separated top-level path entries>
   ```
5. Run every mutmut command (`run`, `export-cicd-stats`, `results`, `show`) with
   `cwd=work`.

**Never target the root — the sandbox is isolated and disposable.**

## Budget Estimate

`mutmut print-time-estimates` requires an existing `mutants/` directory and
cannot serve as a pre-run budget counter. Instead, the leaf estimates the mutant
count from the AST:

```
estimate = sum(len(FunctionDef + AsyncFunctionDef) over --paths files)
           × estimated_mutants_per_def
```

If `estimate > --max-mutants`, the run is refused with `ToolError` (exit 2).
If the *actual* mutant count (sum of all `exit_code_by_key` lengths from the
generated `.meta` files after the run) exceeds `max_mutants`, the run completes
but the status line gains `"budget_exceeded": true` — this is an honest
disclosure, not a crash.

## Kill-Rate Accounting

Per module:

- `total` = number of mutants generated (from `.meta`'s `exit_code_by_key` keys).
- `problems` = mutants whose `mutmut results` status is `survived` or `no tests`.
- `kill_rate = (total - len(problems)) / total`

`timeout`, `suspicious`, and `skipped` mutants count as **killed** — these are
environment-dependent statuses that must not flap findings between runs. Only
`survived` and `no tests` are treated as test-suite weaknesses.

Modules with `kill_rate < min_kill_rate` emit a `TEST` finding with
`metric_name="mutation_kill_rate"`, severity `high` if `< 0.5` else `medium`,
confidence `high`. Evidence includes up to 10 `key=status` entries from the
results text plus the `@@ -N` hunk line numbers from `mutmut show` on the
first 3 survivors (one subprocess call per survivor).

## Registry Semantics

This leaf is registered in `leaf_registry.json` with
`"requires": {"mutation_scope": true}`. The `code-health-audit-pipeline`
umbrella fail-safe-skips any leaf with an unknown `requires` key, listing it
as `"requires mutation_scope artifact"` in `skipped`. The leaf will not gate
in umbrella runs until pipeline plumbing for the mutation-scope artifact is
added (future work). Meanwhile, it runs standalone.

## Honest Limits

- **Python only.** `mutmut` operates on Python source.
- **Runtime cost.** Mutation testing is expensive — `mutmut run` spawns a test
  subprocess per mutant. Budget with `--max-mutants`.
- **Approximate budget.** The AST-based estimate uses `estimated_mutants_per_def`
  (default 8) and is a heuristic; actual mutants may differ.
- **Limited survivor detail.** Only the first 3 surviving mutants per module are
  inspected with `mutmut show` to bound subprocess overhead. A `…(+N more)`
  suffix in evidence_raw indicates there are additional uninspected survivors.
- **No root mutation.** The sandbox protocol ensures the target repo is never
  touched.

## Tool Dependency

```bash
pip install mutmut==3.6.0
```

The leaf probes `importlib.util.find_spec("mutmut")` before running. If mutmut
is not found, a `ToolError` is raised (exit 2).
