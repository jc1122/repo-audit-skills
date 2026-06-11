---
name: test-effectiveness-audit
version: 0.5.4
description: >
  Deterministic, advisory mutation-testing audit for Python. Wraps mutmut==3.6.0
  to measure per-module mutation kill rates, emitting TEST findings (shared
  code-health schema) for modules whose kill rate falls below the configured
  threshold. Never mutates source in-place; runs in a sandbox copy. The
  machine-readable answer to "how good are my tests at catching bugs?".
---

# test-effectiveness-audit

## Overview
A code-health leaf skill that runs pinned `mutmut==3.6.0` on scoped Python
source files and reports per-module kill rates as advisory `TEST` findings.

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
This leaf refuses unscoped runs (exit 2); provide all three:

| Flag | Description |
|---|---|
| `--paths FILE` | Newline-separated, root-relative `.py` files or directories to mutate (e.g., the top-N hotspot paths). |
| `--tests-dir REL` | Root-relative test directory to copy into the sandbox. |
| `--max-mutants INT` | Upper bound on estimated mutants; if the scope's AST `FunctionDef`/`AsyncFunctionDef` count × `estimated_mutants_per_def` exceeds this, the run is refused with `ToolError`. |

Missing any required flag prints status-error JSON on stdout and exits 2.

## Standard Leaf Flags
Per the leaf CLI contract: `--root`, `--source-prefix`, `--out-dir`, `--config`,
`--format`. `--source-prefix` is accepted and recorded for determinism, but the
sandbox currently copies only `--paths` entries and `--tests-dir`.

## Output And Exit Codes
- Outputs: `test-effectiveness_findings.json` (sorted shared-schema findings)
  and `test-effectiveness_report.md` (human-readable summary).
- Exit codes: `0` clean, `1` advisory TEST findings present, `2`
  tool/config/scope error such as missing flags/tool, oversized scope, or
  `mutmut` timeout.

## Thresholds (via `--config` or defaults)
| Key | Default | Description |
|---|---|---|
| `min_kill_rate` | `0.8` | Per-module kill rate below this threshold emits a TEST finding. |
| `mutmut_timeout_seconds` | `600` | Hard timeout for `mutmut run` as a subprocess. |
| `estimated_mutants_per_def` | `8` | Multiplier for the AST-based budget estimate. |

## Sandbox Protocol
`mutmut` loads config at import time; even `mutmut --help` crashes unless CWD
contains `setup.cfg` with `[mutmut] source_paths=...`. All mutmut invocations
therefore run inside a disposable sandbox:

Create `work = <out-dir>/.mutmut-work` (wiped at each run), copy each `--paths`
entry and `--tests-dir` to `work/<same relpath>`, write `<work>/setup.cfg` with
`[mutmut] source_paths=<space-separated top-level path entries>`, then run
`mutmut run`, `export-cicd-stats`, `results`, and `show` with `cwd=work`. Never
target the root; the sandbox is isolated and disposable.

## Budget Estimate
`mutmut print-time-estimates` requires an existing `mutants` directory, so the
leaf estimates mutant count from the AST before running:

Estimate:
`sum(len(FunctionDef + AsyncFunctionDef) over --paths files) × estimated_mutants_per_def`.
If `estimate > --max-mutants`, refuse with `ToolError` (exit 2). If the actual
mutant count from generated `.meta` `exit_code_by_key` lengths exceeds
`max_mutants`, complete the run and add `"budget_exceeded": true` to status.

## Kill-Rate Accounting
Per module, `total` is the generated mutant count from `.meta`
`exit_code_by_key`; `problems` are mutants whose `mutmut results` status is
`survived` or `no tests`; `kill_rate = (total - len(problems)) / total`.

`timeout`, `suspicious`, and `skipped` count as killed to avoid flapping on
environment-dependent statuses. Only `survived` and `no tests` are treated as
test-suite weaknesses.

Modules with `kill_rate < min_kill_rate` emit a `TEST` finding with
`metric_name="mutation_kill_rate"`, severity `high` if `< 0.5` else `medium`,
and confidence `high`. Evidence includes up to 10 `key=status` entries plus
`@@ -N` hunk lines from `mutmut show` for the first 3 survivors.

## Registry Semantics
Registered in `leaf_registry.json` with `"requires": {"mutation_scope": true}`.
The `code-health-audit-pipeline` umbrella fail-safe-skips unknown `requires`
keys and lists this as `"requires mutation_scope artifact"` in `skipped`. It
runs standalone until mutation-scope artifact plumbing exists.

## Honest Limits
- Python only: `mutmut` operates on Python source.
- Runtime cost: `mutmut run` spawns a test subprocess per mutant; budget with
  `--max-mutants`.
- Approximate budget: AST estimate uses `estimated_mutants_per_def` (default 8);
  actual mutants may differ.
- Limited survivor detail: only first 3 survivors per module are inspected with
  `mutmut show`; `...(+N more)` in `evidence_raw` means more survivors exist.
- Test suite shape: subprocess integration suites can be incompatible with the
  mutmut sandbox; prefer per-file unit suites as `--tests-dir`.
- No root mutation: the sandbox protocol ensures the target repo is never
  touched.

## Tool Dependency
Install with `pip install mutmut==3.6.0`. The leaf probes
`importlib.util.find_spec("mutmut")` before running; missing mutmut raises
`ToolError` (exit 2).
