# SP4 Skillset-Completion — Implementation Plan

Date: 2026-06-10
Spec: `docs/superpowers/specs/2026-06-10-sp4-skillset-completion-design.md`
Bootloader: `docs/superpowers/SP4-BOOTLOADER.md`

Workers implement these tasks **verbatim via TDD**. A worker's "green" is not
evidence — the orchestrator re-runs every gate and reads real output. Always use
`.venv/bin/python -m` for pytest/pip/coverage (stale venv shims). All commands
run from the repo root `/home/jakub/projects/repo-audit-skills` unless noted.

Gate vocabulary:
- `npm run check` = `check:vendored && check:fixtures && check:release &&
  check:selfaudit && check:coverage`.
- "self-audit gate" = `check:selfaudit` (prints `{"status":"pass","count":N,"baseline":N}`).
- "coverage gate" = `check:coverage` (prints `{"status":"pass","suites":S,"count":C,"baseline":B}`).

Pre-flight verified at T0: clean tree at 438234c (after v0.2.0 23fef02);
`npm run check` green (selfaudit 168==168, coverage 5==5 / 8 suites); venv usable;
worker-bridge skill loads.

---

## Phase 1 — Build

### T1 — Fix root pytest collection

**Problem.** `.venv/bin/python -m pytest --collect-only -q` from the repo root
fails with 13 collection errors. Root cause (see spec D3): seven leaf suites each
ship `tests/helpers.py` imported as top-level `helpers`; in a single root
collection the first one wins in `sys.modules` and later suites get the wrong
module. Script module names (`complexity_audit`, …) are already unique; only
`helpers` collides. `--import-mode=importlib` does not fix it.

**Files (new only — do not rename/edit existing test files):**
- `skills/complexity-audit/tests/conftest.py`
- `skills/duplication-audit/tests/conftest.py`
- `skills/dead-code-audit/tests/conftest.py`
- `skills/structure-audit/tests/conftest.py`
- `skills/quality-audit/tests/conftest.py`
- `skills/code-health-audit-pipeline/tests/conftest.py`
- `skills/coverage-gap-audit/tests/conftest.py`
- (plus, created by T3, the same file in each new `skills/test-*/tests/`)

**Each conftest.py content (identical):**
```python
import sys
from pathlib import Path

_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.modules.pop("helpers", None)
```

**TDD step.** Add a root-level test `tests/test_root_collection.py` that asserts
clean collection from root:
```python
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_root_collect_only_is_clean():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "errors during collection" not in (proc.stdout + proc.stderr)
```
Watch it FAIL (13 errors), add the conftests, watch it PASS.

**Expected gate output:**
- `.venv/bin/python -m pytest --collect-only -q` from root: exit 0, `N tests
  collected` (≈100 pre-T3), **0 errors**.
- Each suite still green from its own directory:
  `cd skills/<leaf>/tests && .venv/bin/python -m pytest -q` → all pass.
- `npm run check` green; **`check:coverage` output unchanged** (still `suites: 8,
  count: 5, baseline: 5`) — conftest only affects root collection, not the
  per-suite subprocesses the coverage gate spawns.

**Constraints.** New files only. Do not edit existing test bodies. Do not add a
root `pytest.ini`/`pyproject.toml` ini that changes import mode globally (it
breaks the per-suite runs the coverage gate depends on).

---

### T2 — CI workflow

**File (new):** `.github/workflows/check.yml`.

**Requirements.**
- Triggers: `push` and `pull_request` (at least on default branch).
- `runs-on: ubuntu-latest`.
- Steps: `actions/checkout@v4`; `actions/setup-node@v4` (Node 20);
  `actions/setup-python@v5` (Python 3.14 to match the dev venv — if unavailable
  on the runner, pin the highest 3.x the action offers and note it); install
  pinned test deps **`coverage==7.14.1 pytest-cov==7.1.0`** plus the audit tools
  the gates actually invoke (`lizard`, `radon`, `vulture`, `ruff`, `jscpd` is a
  node tool — install via the repo's existing mechanism if the gates shell to it;
  `mypy`/`ty` as quality-audit requires). Read each gate script's subprocess
  calls and `bin/` to enumerate the exact tool set; pin every version. `npm
  install` (or `npm ci` if a lockfile resolves); then `npm run check`.
- Do **not** weaken any gate to make CI pass.

**Validation (static only — CI cannot run pre-push):**
- If `actionlint` and/or `yamllint` are available, run them and paste output.
- Else careful read: valid YAML, every gate's tool present in the install step,
  versions pinned, `npm run check` is the final step.

**Expected report line (mandatory):** "CI workflow committed and statically
validated; it has NOT executed — post-push verification is the human's
responsibility."

**Constraint.** `.github/workflows/` is repo CI, not package content — T-LAST's
`npm pack --dry-run` must NOT include it.

---

### T3a / T3b / T3c — Golden/behavior suites for the test-audit skills

Parallel, **disjoint directories, no baseline ratchet, TESTS ONLY** — zero edits
to `skills/test-*/scripts/**`. Tests characterize *current* behavior. Mirror the
existing leaf suites (`skills/complexity-audit/tests/`): `helpers.py`
(`load_module()` in-process import + `run_cli()` subprocess + `read_*` reader),
`conftest.py` (the T1 file), frozen fixtures under `tests/fixtures/`, golden
findings JSON, CLI/exit-code contract, idempotence (byte-identical across runs).

**Coverage rule (spec D2):** the coverage-clearing tests import the module and
call its functions **in-process**. Subprocess CLI tests do not count toward
coverage — keep at most a thin smoke test via subprocess. **Target ≥50% file
coverage per script.** Measure locally with:
```
cd skills/<skill>/tests
.venv/bin/python -m coverage run -m pytest -q
.venv/bin/python -m coverage report --include='*/scripts/<script>.py'
```

#### T3a — `test-redundancy-triage` (`scripts/triage_redundancy.py`, 3065 LOC)
New dir `skills/test-redundancy-triage/tests/` with `helpers.py`, `conftest.py`,
`fixtures/`, and test modules. Hardest coverage target.
- **Pure-function unit tests (in-process, the bulk of coverage):** exercise
  `tokenize_normalized`, `jaccard_sim`, `dotted_name`, `extract_calls`,
  `infer_assertion_types`, `count_assertions`, `detect_parametrized`,
  `infer_entrypoint`, `infer_intent`, `parse_test_metadata`,
  `read_csv_rows`/`write_csv`, `parse_ranked_by_nodeid`,
  `parse_inventory_assertions`, `parse_coverage_json`,
  `normalize_source_path_for_coverage`, the coercers (`as_bool`, `as_int`,
  `as_float`, `as_bool_any`, `tri_state`, `bool_low_signal`), `chunked`,
  `unique_preserve`, `build_default_mutation_probes`,
  `load_mutation_probes_from_config`, `apply_mutation_probe`.
- **In-process `main()` run against a tiny frozen fixture suite** (a 2–3 file
  mini test package with deliberately redundant tests) to cover the
  orchestration/artifact-writing paths (`run_suite*`, `collect_*`, `write_*`,
  `run_strict_delete_gate` where feasible). `main()` spawns pytest subprocesses
  for the fixture suite (child lines untraced) but its own lines are traced.
- **Golden:** freeze the advisory CSV/JSON artifacts for the fixture suite.
- **CLI smoke:** `--help` exit 0; a dirty-fixture run produces the expected
  artifacts and exit code.

#### T3b — `test-quality-assurance` (`scripts/audit_test_quality.py`, 945 LOC)
New dir `skills/test-quality-assurance/tests/`. This script is pure static
analysis (no subprocess) — easiest to cover in-process.
- Fixtures: a `clean` test dir (behavior-focused, public-API tests) and a
  `dirty` test dir (implementation-coupled imports, exact-eq assertions, missing
  marks) so `classify_file`, `analyze_file`, `summarize`, `score_rubric`,
  `infer_public_hints`, `parse_coverage_json`, `compute_delta`,
  `render_markdown` all fire.
- Golden: freeze `--json-out` and `--md-out` for both fixtures.
- CLI smoke + idempotence (byte-identical JSON across two runs).

#### T3c — `test-audit-pipeline` (`scripts/audit_pipeline.py`, 775 LOC)
Extend the existing `skills/test-audit-pipeline/tests/test_audit_pipeline_meta.py`
into a full suite (add `helpers.py`, `conftest.py`, `fixtures/`). The pipeline
orchestrates the other two via subprocess.
- In-process: `build_summary`, `_extract_coverage_summary`,
  `_extract_triage_summary`, `_read_json`, `_build_env`, `parse_args`,
  `stage_report` rendering on synthetic stage inputs (no real subprocess needed
  to cover the summary/report logic).
- Keep the existing wallclock/timing determinism assertion.
- Golden: freeze the canonical summary/report for a synthetic stage-input set.
- One subprocess smoke (`--help`).

**Gate per suite:** from its own directory, `.venv/bin/python -m pytest -q` →
all pass; coverage report shows the script ≥50%. **No `npm run check` change yet**
(the new suites are not in the coverage gate's SUITES until T4).

---

### T4 — Gate the three new suites (baseline-touching)

**File:** `scripts/check_coverage_gap.py` — extend `SUITES` from 8 to 11
(SEPARATE pytest subprocesses, same `--cov-append` pattern):
```python
SUITES = [
    "tests",
    "skills/complexity-audit/tests",
    "skills/duplication-audit/tests",
    "skills/dead-code-audit/tests",
    "skills/structure-audit/tests",
    "skills/quality-audit/tests",
    "skills/code-health-audit-pipeline/tests",
    "skills/coverage-gap-audit/tests",
    "skills/test-audit-pipeline/tests",
    "skills/test-quality-assurance/tests",
    "skills/test-redundancy-triage/tests",
]
```

**Steps.**
1. Run `npm run check:coverage`. Read the regenerated
   `scripts/coverage_gap_snapshot.json`. The three `skills/test-*/scripts/*`
   entries **must disappear** (each now ≥50% covered by the T3 suites). If any
   stays, the corresponding T3 suite is insufficient → return it to T3 as a
   discard/retry; **do not freeze it.**
2. Ratchet `scripts/coverage_gap_baseline.json` from 5 entries to exactly **2**:
   `scripts/self_audit.py` and `scripts/check_self_audit.py` (the two SP3-R2
   justified freezes). Remove the three `skills/test-*` entries.
3. Update the runbook prose in `scripts/self_audit_frozen.md` (the
   "Coverage-gap baseline" section): record that the three test-* entries cleared
   via the T3 in-process suites, baseline 5 → 2, suites 8 → 11.

**Expected gate output:** `check:coverage` →
`{"status":"pass","suites":11,"count":2,"baseline":2}`. `npm run check` green.
Self-audit gate unchanged unless adding the SUITES list churns self-audit (it
should not — `check_coverage_gap.py` gains only list entries); if it does, ratchet
per the standing rule in the same commit.

---

### T5 — Umbrella v2: artifact-gated leaf (baseline-touching if self-audit churns)

**Files:**
- `skills/code-health-audit-pipeline/scripts/leaf_registry.json` — add optional
  `"requires"` to the schema; register the coverage-gap leaf:
  ```json
  {"name": "coverage-gap", "skill": "coverage-gap-audit",
   "script": "coverage-gap-audit/scripts/coverage_gap_audit.py",
   "languages": ["python"], "findings_file": "coverage-gap_findings.json",
   "requires": {"coverage_json": true}}
  ```
  The five existing entries gain no `"requires"` (absent ⇒ no requirement).
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`:
  - `select_leaves`/`run_leaves`: when a leaf declares
    `requires.coverage_json` and no `--coverage-json` was passed, emit an explicit
    `"skipped"` record (leaf name + reason `"requires coverage_json artifact"`)
    and do not run it.
  - add a `--coverage-json PATH` arg; when present, satisfy the requirement, run
    the coverage-gap leaf, and thread the path into its invocation (and the
    `--source-prefix` set the leaf needs, mirroring `check_coverage_gap.py`).
  - keep the leaf's vendored `scripts/health_common.py` byte-identical to
    `shared/health_common.py` (the coverage-gap leaf already has it; do not touch).

**Additivity (mandatory) + goldens (TDD):**
- **No-artifact golden:** umbrella run with no `--coverage-json` over a fixture
  tree produces output **byte-identical** to current behavior, plus a `"skipped"`
  record for coverage-gap. Capture the current no-artifact output FIRST (before
  editing the pipeline) as the golden, then prove the post-edit output matches the
  pre-existing-leaves portion byte-for-byte. Existing pipeline tests
  (`test_pipeline_*.py`) must stay green.
- **Artifact golden:** umbrella run *with* `--coverage-json <fixture coverage>`
  runs the coverage-gap leaf and merges its findings; freeze that output.

**Expected gate output:** `npm run check` green. If introducing the leaf into the
umbrella's own self-audit scope churns findings (new module-MI / cross-leaf
clones, as SP3-T4 saw), justified-freeze per the established standalone-vendored
idioms in `self_audit_frozen.md` and ratchet `self_audit_baseline.json` in the
**same commit**. Never run T5 concurrently with T4 or any Phase 2 merge.

---

### Phase 1 EXIT (orchestrator verifies before Phase 2)
- `npm run check` green.
- `check:coverage` → `suites: 11, count: 2, baseline: 2`.
- Root `.venv/bin/python -m pytest --collect-only -q` exits clean (0 errors).
- `.github/workflows/check.yml` committed + statically validated.
- Umbrella v2 additive (both goldens green).

---

## Phase 2 — Unfreeze + burn-down

Orchestrator drives. Max 6 rounds. Snapshot may only **SHRINK**; growth = STOP and
investigate. One worker per file-batch, own worktree. **ACCEPT only if, in the
worktree: `npm run check` green (all gates) AND the three test-* suites pass.**
Otherwise discard/retry. After accept: merge, re-run self-audit, ratchet
`self_audit_baseline.json`, commit baseline + `self_audit_frozen.md` each round.
Never two baseline-touching merges concurrently (Phase 2 merges are serial).

**Step 0 — retire the rule-freeze.** Delete section A ("Non-actionable: untested
test-audit scripts (126)", the Actionability-Rule blanket) from
`scripts/self_audit_frozen.md`. Those 126 findings are now ACTIONABLE, protected
by the T3 suites.

**Round order (126 findings, all under `skills/test-*/scripts/`):**
- **R1 — mechanical lint (~55):** E501 (50) + SIM102 (4) + SIM108 (1), in bulk
  per file. Pure formatting/idiom; goldens must stay byte-identical (these do not
  change behavior). Files: `triage_redundancy.py`, `audit_test_quality.py`,
  `audit_pipeline.py`.
- **R2 — B023 (10):** function-defined-in-loop late-binding. **Real bug-risk
  fixes.** If a fix changes observable output, a golden fails — investigate and
  explain the behavior change; **never** regenerate a golden to make a fix pass
  silently.
- **R3+ — complexity/duplication/MI (~61):** cyclomatic_complexity (18),
  function_nloc (20), parameter_count (14), duplicate_tokens (6),
  maintainability_index (3). **Prefer FIX over FREEZE.** Decompose only where it
  nets a real reduction without churning clone detection. Otherwise
  justified-freeze per the established idioms (single-file-tool module-MI;
  cohesive tool logic for CC/nloc; cross-leaf vendored duplication forbidden to
  dedup per SP3 R2). Every freeze gets a concrete per-finding reason in
  `self_audit_frozen.md`.

**CONVERGED** when the actionable set is empty **and ZERO blanket/rule-frozen
entries remain anywhere** — every residual freeze is individual and justified.
Bounded at 6 rounds; stop on a no-progress round. Report per-round burn-down
table (round, fixed, frozen, net, baseline) and the final baseline count
(expected well under 100).

---

## T-LAST — Release prep 0.3.0

- Bump `package.json` `version` to `0.3.0` and all **TEN** `skills/*/SKILL.md`
  `version:` frontmatter to `0.3.0` **atomically** (the `check:release` gate
  asserts every SKILL.md version == package.json version).
- `npm run check` green.
- `npm pack --dry-run` (`npm run pack:dry-run`): inspect the file list — must NOT
  include `.github/workflows` (repo CI, not package content) and no cache dirs
  (`.pytest_cache`, `.ruff_cache`, `__pycache__`, `.self_audit_out`, `.venv`).
- Commit. **Do NOT push.**

## Definition of Done (report with evidence)
1. `npm run check` green; `check:coverage` runs 11 suites; root
   `pytest --collect-only` exits clean.
2. Three test-audit skills ship green behavior/golden suites; scripts ≥50%
   covered; coverage baseline = 2 justified entries, zero rule-frozen.
3. Self-audit baseline strictly < 168 with ZERO blanket/rule freezes — final
   count, per-round net change, every new freeze justification.
4. CI workflow committed + statically validated; post-push verification is the
   human's.
5. Umbrella v2: coverage-gap-audit registered artifact-gated; no-artifact output
   byte-identical (golden); artifact path golden.
6. v0.3.0 everywhere; pack dry-run clean; **nothing pushed**.
7. Run report: per-task gate evidence, per-round burn-down table, final baseline
   counts.
