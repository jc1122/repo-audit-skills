# SP4 Skillset-Completion — Design Spec

Date: 2026-06-10
Status: accepted (orchestrator T0; expanded from `docs/superpowers/SP4-BOOTLOADER.md`)

This spec records the *decisions* behind the SP4 run. The step-by-step task
breakdown lives in `docs/superpowers/plans/2026-06-10-sp4-skillset-completion.md`.
Workers implement the plan tasks verbatim via TDD; this spec is the rationale of
record.

## Context (verified 2026-06-10, post-SP3)

- v0.2.0 committed (23fef02), not pushed. All FIVE gates green:
  `check:vendored`, `check:fixtures`, `check:release`, `check:selfaudit`
  (self-audit 168 == 168), `check:coverage` (5 == 5 across 8 suites).
- 126 / 168 self-audit findings + 3 / 5 coverage-gap entries are **rule-frozen
  only because the three test-audit skills ship no behavior tests** in this
  package. Verified breakdown of the 126 (all under `skills/test-*/`):

  | metric                | count |
  |-----------------------|------:|
  | E501                  |    50 |
  | SIM102                |     4 |
  | SIM108                |     1 |
  | B023                  |    10 |
  | cyclomatic_complexity |    18 |
  | function_nloc         |    20 |
  | parameter_count       |    14 |
  | duplicate_tokens      |     6 |
  | maintainability_index |     3 |
  | **total**             | **126** |

  Per script: `triage_redundancy.py` 84, `audit_test_quality.py` 28,
  `audit_pipeline.py` 14.
- No `.github/workflows/`. Root `pytest --collect-only` fails with 13 collection
  errors. Umbrella `leaf_registry.json` has 5 leaves and lacks coverage-gap-audit.

## Decisions

### D1 — Test-first ordering (output contracts frozen before any edit)
The three test-audit scripts are refactored in Phase 2. Their behavior must be
pinned **before** a single production line changes. Therefore golden/behavior
suites (T3a/b/c) land in Phase 1 with **zero edits** to `skills/test-*/scripts/**`;
they characterize *current* behavior. Every Phase 2 change is then guarded: if a
fix alters observable output, a golden fails and we investigate rather than
regenerate. This is the core safety property of the run.

### D2 — Coverage is measured in-process, not via subprocess CLI
SP3 R1 evidence: subprocess CLI invocations are **not** traced by pytest-cov in
this config (`.coveragerc` `relative_files = True`, suites run as separate
`pytest` subprocesses under `--cov-append`). A test that only shells out to the
script clears exit-code/contract checks but contributes ~0% file coverage.
Therefore the coverage-clearing tests **import the module and exercise its
functions in-process** (the existing leaf `helpers.load_module()` idiom). A thin
subprocess smoke test is kept only for the CLI/exit-code contract.

Consequence for `triage_redundancy.py` (3065 LOC): reaching ≥50% requires running
its `main()` **in-process** against a tiny frozen fixture suite. `main()` spawns
pytest subprocesses for the *target* suite (those child lines are not traced),
but the script's own orchestration/parsing/artifact-writing lines execute in the
traced parent process and count. Pure helpers (`tokenize_normalized`,
`jaccard_sim`, `infer_intent`, `parse_test_metadata`, the `as_*`/`tri_state`
coercers, CSV/coverage parsers, …) are unit-tested directly.

### D3 — Root collection fix: per-directory conftest, no test renames
The 13 collection errors are a **module-name collision**: seven leaf suites each
ship a `helpers.py` imported as top-level `helpers`. When pytest collects from
the repo root in one process, the first `helpers` wins in `sys.modules` and every
later suite imports the wrong one (hence `module 'code_health_pipeline' has no
attribute 'DEFAULT_THRESHOLDS'` inside structure-audit's tests). The script
modules themselves already have unique names (`complexity_audit`,
`structure_audit`, …) — only `helpers` collides. `--import-mode=importlib` does
**not** fix it (it makes it worse — 18 errors — because `import helpers` still
resolves through a shared name).

Fix (validated by throwaway experiment during T0 — 100 tests collected, exit 0):
a per-directory `conftest.py` in every `skills/*/tests/` that inserts its own
directory at the front of `sys.path` and evicts any cached `helpers` so the next
`from helpers import …` re-imports the local one:

```python
import sys
from pathlib import Path
_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.modules.pop("helpers", None)
```

No existing test file is renamed or edited. New T3 suites ship the same conftest.
Acceptance is collect-only-clean from root **and** every suite still green from
its own directory **and** `check:coverage` output unchanged.

### D4 — Artifact-gated umbrella leaf (umbrella v2), additive
`coverage-gap-audit` needs a `coverage.json` artifact to run; the other five
leaves do not. Rather than always-skip or always-fail, `leaf_registry.json`
entries gain an **optional** `"requires"` field (e.g. `{"coverage_json": true}`).
`code_health_pipeline.py`:
- when the required artifact is absent, emits an explicit `"skipped"` record for
  that leaf and continues;
- when `--coverage-json PATH` is passed, satisfies the requirement and runs the
  leaf, threading the path through.

**Additivity is mandatory**: existing no-artifact umbrella output stays
byte-identical (a golden test proves it). The new artifact path gets its own
golden. All five existing entries omit `"requires"` (treated as no requirement),
so their behavior is untouched. Vendored `health_common.py` stays byte-identical
to `shared/health_common.py` in every leaf (the `check:vendored` gate enforces).

### D5 — Rule-freeze retirement under test protection
Once T3 suites exist and are gated (T4), the "Actionability Rule" blanket freeze
for `skills/test-*/` (section A of `scripts/self_audit_frozen.md`, 126 findings)
is **retired**: those findings become actionable and are burned down in Phase 2
under golden protection. Convergence requires **zero blanket/rule freezes
anywhere** — every residual freeze is individual and carries a concrete
per-finding reason (the established idioms: single-file-tool module-MI; cohesive
tool logic for CC/nloc; cross-leaf vendored duplication, forbidden to dedup per
SP3 R2 evidence).

### D6 — Burn-down order and the prefer-fix rule
Phase 2 rounds: R1 mechanical lint (E501 + SIM, ~55) → R2 B023 (10, real
late-binding bug-risk fixes) → R3+ complexity/duplication/MI (~61, decompose
only on net reduction else justified-freeze). **Prefer FIX over FREEZE.** A
B023 fix that changes observable output is investigated and explained, never
papered over by regenerating a golden. Snapshot may only shrink; growth = STOP
and investigate.

### D7 — Coverage baseline lands at exactly 2 justified entries
After T4, `coverage_gap_baseline.json` holds exactly two entries, both already
justified in SP3 R2: `scripts/self_audit.py` and `scripts/check_self_audit.py`
(their `main()` re-runs the full ~30s audit; covered end-to-end by the
`check:selfaudit` gate, not worth re-running inside the unit suite). Zero
rule-frozen coverage entries remain.

## Non-goals / constraints
- No existing tool's output contract may change (goldens enforce; T3 goldens land
  before any `test-*/scripts` edit).
- Never touch `tests/fixtures/**` of other skills.
- Never run two baseline-touching tasks (T4, T5, each Phase 2 merge) concurrently.
- CI cannot be verified before the human pushes — T2 is static validation only.
- Release prep bumps to 0.3.0 and commits; **nothing is pushed**. The human
  reviews, pushes, publishes, verifies CI, and reinstalls.
- Always `.venv/bin/python -m` for pip/pytest (stale venv shims).
