---
name: test-redundancy-triage
version: 0.5.7
description: >
  Identify redundant tests with empirical deselection, branch-equivalence, assertion
  dominance, and coverage/mutation signals. Produces conservative DELETE/KEEP/MERGE
  guidance with strict gates and confidence tiers.
---

# Test Redundancy Triage

## Scope and Semantics
Evaluate redundant tests conservatively. Default posture is `MERGE_RECOMMENDED` unless
delete candidates are explicitly high-confidence.

## Core Heuristics
- empirical deselection: `pytest --deselect=<nodeid>` suite-pass check,
- assertion dominance: peer assertions are superset or equal,
- token/source Jaccard similarity + name similarity,
- assert-count and intent-aware tie-breakers,
- branch-equivalence evidence via exact match + token overlap + deltas,
- coverage/mutation signal when available; live coverage fallback when ranked data is missing.

Parametrized tests are emitted as `KEEP_FOR_SIGNAL` unless evaluated manually.

## Baseline run
Use `skills/test-redundancy-triage/scripts/triage_redundancy.py`.

```bash
python scripts/triage_redundancy.py \
  --root /path/to/repo \
  --python /path/to/python \
  --suite tests/test_api.py \
  --comparator-suite tests/test_integration.py \
  --source-prefix src/mypackage/ \
  --out-dir artifacts/redundancy \
  --max-workers 4 \
  --env NUMBA_DISABLE_JIT=1
```

Required/important flags:
- `--root` repo path.
- `--python` interpreter path or `python3` lookup.
- `--suite` (repeatable, required) candidate files.
- `--comparator-suite` cross-suite overlap only.
- `--source-prefix` optional source filter.
- `--out-dir` output root.
- `--max-workers` for parallel checks.
- `--env` environment forwarding, e.g. `KEY=val`.
- `--suite` and `--strict-post-suite` values must be under `--root`.
- `--strict-delete-gate`, `--strict-repeats`, `--strict-batch-size`,
  `--strict-mutation-probes`, `--strict-mutation-max-drop`, `--strict-post-suite`.
- `--mutation-probes-config` JSON file + optional `--allow-numba-stub`.

Strict pattern:

```bash
python scripts/triage_redundancy.py \
  --root /path/to/repo \
  --python python3 \
  --suite tests/test_api.py \
  --comparator-suite tests/test_integration.py \
  --source-prefix src/mypackage/ \
  --out-dir artifacts/redundancy \
  --max-workers 4 \
  --strict-delete-gate \
  --strict-post-suite tests \
  --strict-repeats 3 \
  --strict-batch-size 8 \
  --strict-mutation-probes 3 \
  --strict-mutation-max-drop 0 \
  --mutation-probes-config path/to/probes.json \
  --allow-numba-stub
```

## Mutation Probes
`--mutation-probes-config` supplies JSON entries with `probe_id`, `file` (relative to
`--root`), `old`, and `new`. Each probe must be a **single exact-string replacement**.
The script errors if `old` is missing or appears >1 time. `--strict-mutation-probes`
selects how many probes are used from the file (default 3). Without a config, mutation
gating is skipped. In strict mode, repeated deselection runs, staged batch simulation,
post-suite checks, and mutation-probe deltas are required before delete-safe decisions.

## Decision Policy
- `DELETE_SAFE_HIGH`: delete allowed after all active gates pass.
- `MERGE_RECOMMENDED`: high similarity with distinct signal; merge into stronger parametrized test.
- `KEEP_FOR_SIGNAL`: useful unique signal.
- `KEEP_FOR_CONTRACT`: would leave a contract-empty `(file, intent)` cluster.
- `KEEP_FOR_STABILITY`: deselection causes failures.

## Confidence Tiers (in `confidence_gate_matrix.csv`)
- `GOLD_DELETE_CANDIDATE`
- `SILVER_DELETE_CANDIDATE`
- `BRONZE_DELETE_REVIEW`
- `MERGE_CANDIDATE`
- `KEEP_CANDIDATE`

`STRICT` mode downgrades non-passing candidates to keep decisions with explicit strict failure notes.

## Output Artifacts (`--out-dir`)
`inventory.csv`, `coverage_matrix.csv`, `coverage_summary.json`,
`mutation_matrix.csv`, `mutation_summary.json`, `branch_equiv_report.csv`,
`branch_equiv_summary.json`, `branch_equiv_report.md`,
`confidence_gate_matrix.csv`, `candidate_validation.csv`, `candidate_validation.md`,
`candidate_validation_summary.json`, `strict_gate.csv`, `strict_gate_summary.json`
(last two only with `--strict-delete-gate`).

`mutation_matrix.csv`, `coverage_matrix.csv`, `branch_equiv_report.csv`, and
`confidence_gate_matrix.csv` are always produced, with `<something>_signal_available=False`
and `status_note` when bootstrap/provisioning is unavailable.
Use `candidate_validation.csv` as the automation source of truth.

## Known Limitations
- Mock-heavy/ctypes-mocked tests can be mis-ranked when branches are hard to observe.
- Keyword-based intent inference may misclassify atypical test names.
- No per-variant analysis for parametrized tests; all variants treated as one unit.
- Environment-sensitive suites need explicit `--env` values (for example JIT toggles like
`NUMBA_DISABLE_JIT=1`).
