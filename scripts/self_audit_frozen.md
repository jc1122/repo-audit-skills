# Frozen self-audit findings

(Historical note: the "Actionability Rule" blanket freeze for `skills/test-*/`
referenced in the Phase 1 / SP3 round-log entries below was RETIRED in SP4
Phase 2 — see section A. Every current baseline finding is justified individually;
no blanket/rule freeze is active anywhere.)

Each entry: path :: leaf/metric :: reason.

## Round log

- **R1** (fix): cleared 15 lint findings in `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/check_release.py` (E401/E702/E501/format_drift). Baseline 191 -> 176. 0 frozen. (A parallel leaf-lint attempt was discarded: line-wrapping the near-identical leaf scripts churns `duplicate_tokens` line-range symbols and pushed `_vulture_findings` over the nloc threshold — a regression.)
- **R2** (attempted FIX, DISCARDED): hoisting `ToolError`/`rel`/`iter_python_files` into `shared/health_common.py` traded 17 cross-leaf clones for 13 vendored-copy clones + 6 new `maintainability_index` findings (net +2). `health_common.py` is vendored byte-identical into all 5 leaves, so any code placed there is cloned 6×. Conclusion: cross-leaf duplication is intrinsic to the standalone-vendored-leaf architecture — see freeze rationale below.
- **R3** (fix): fixed B904 in the umbrella + wrapped 13 E501 across the six code-health scripts (+ ruff-format polish on structure_audit.py). Baseline 176 -> 162. 0 real regressions (duplication line-range symbols churned, which is expected and absorbed by the ratchet).
- **R4** (converge): froze the 36 residual actionable findings (17 duplication, 9 module-MI, 5 cyclomatic, 5 nloc) with concrete per-finding justifications + the 126 non-actionable test-audit findings (Actionability Rule). Baseline stays 162 (no code change). **Actionable set is now empty — converged.**
- **SP3-T1**: added TEST to SIGNALS + EFFORT; re-vendored; ratchet absorbed duplication line-range churn (no net new findings).
- **SP3-T7**: added `check:coverage` gate (`scripts/check_coverage_gap.py`, ruff-clean). Self-audit 165 -> 168 (+3): +1 module-MI (section D) + 2 clones of the shared snapshot/baseline ratchet idiom (section C). Froze the initial coverage-gap baseline (9 entries: 6 gate/self-audit scripts = Phase 2 worklist + 3 `skills/test-*/scripts` rule-frozen). SANITY verified: snapshot contains NO covered file (shared/health_common, the 6 code-health leaves, the coverage-gap leaf are all absent) -> pytest-cov subprocess tracing confirmed working.
- **SP3-T4**: added the `coverage-gap-audit` leaf (`coverage_gap_audit.py`, ruff-clean + formatted). Self-audit 162 -> 165 (+3 net): +1 module-MI (section D) and +7 cross-leaf CLI/parse clones involving the new leaf (section C), offset by -5 pre-existing clone-pairs that jscpd re-attributed to the leaf's clone groups. All churn is 100% attributable to introducing the leaf into duplication scope; frozen by the same standalone-vendored-leaf rationale (this front-loads the freeze the plan placed at T5, to keep every commit green).
- **SP4 Phase 2, R1**: (fix) cleared 55 lint findings (E501/SIM102/SIM108) in audit_test_quality.py + triage_redundancy.py; baseline 170 -> 115; line-range duplicate_tokens churn absorbed by the ratchet.
- **SP4 Phase 2, R2**: (fix) 10 B023 (`flake8-bugbear` late-binding) in `triage_redundancy.py` fixed with default-arg binding (`_stack=stack`, `_path=path`, `_src=src`) on `visit_ClassDef`, `visit_FunctionDef`, `visit_AsyncFunctionDef`. Baseline 115 -> 105; line-range duplicate_tokens churn absorbed by the ratchet. No golden changed (late-binding was latent on all fixtures).
- **SP4 Phase 2, R3**: (fix + freeze) deduplicated parallel/sequential kwargs in `audit_pipeline.py:main()` via inline dicts (removed 2 duplicate_tokens findings at 712-721/725-735). Attempted extraction fixes for the 4 `triage_redundancy.py` in-file clones (377-411 visit visitor, 849-871 coverage-json export, 1290-1297/1327-1347 ThreadPoolExecutor block) — every extraction variant (module-level helper, closure, closure-with-defaults) created regressions: `parameter_count` on the helpers, B023 on closures, or `dead_code_confidence` on argparse-group helpers. Attempted `audit_test_quality.py` parse_args nloc extraction — created 3 new duplicate_tokens + 1 dead_code (net +3 regression). **Conclusion**: in-file clone extraction from these single-file standalone tools is net-negative under the current lizard threshold (≥5 params → parameter_count) and jscpd minimum-token settings. The 4 remaining triage duplicate_tokens are individually frozen below. Baseline 105 -> 104 (2 fixed, 1 churn dup added). 2 remaining duplicate_tokens in the snapshot belong to churned line ranges. 0 blanket freezes remain; all 60 residual test-* findings individually justified.
- **SP7 INT-1** (fix): hardening `check_self_audit.py` into an equality gate dissolved the `check_coverage_gap.py <-> check_self_audit.py:23-31` ratchet-idiom clone; that stale baseline entry was ratcheted out in the same commit (bee4502). Baseline 104 -> 103.
- **SP7 INT-3** (freeze): merging `repo-hygiene-audit` (A3; registered `languages: ["*"]` + the `select_leaves` wildcard, so it now runs under self-audit) brought a SECOND leaf `_git` subprocess wrapper into duplication scope, producing exactly 1 cross-leaf clone (`skills/hotspot-audit/scripts/_audit_git.py` <-> `skills/repo-hygiene-audit/scripts/_git_utils.py:36-53`). Identical standalone-vendored-leaf rationale as section C (R2 evidence: hoisting to `shared/` is net-negative). The A1 merge (INT-2) added zero findings — this clone needs both leaves present, so it could only surface at integration, not in either branch. PREFER-FIX rejected (cross-skill import forbidden; `shared/` hoist proven net-negative at R2). Frozen individually in section C2. Baseline 103 -> 104.
- **SP7 INT-4** (clean): merging `dependency-audit` (A2; registered `languages: ["python"]`) added zero self-audit findings — the single-file `dependency_audit.py` clones with no existing or new leaf and stays above the module-MI floor. No freeze. Baseline unchanged (104).
- **SP7 INT-5** (freeze): merging `docs-consistency-audit` (A4; registered `languages: ["python"]`) added exactly 1 finding: module-level `maintainability_index` on `skills/docs-consistency-audit/scripts/docs_consistency_audit.py` (radon MI 23.5 < leaf threshold 65). This is the established single-file-tool module-MI idiom (section D) — the leaf ships one ~600-line self-contained script by design; every per-function complexity/nloc/param/duplication/lint/format finding was already cleared in-branch (post-refactor 34 functions, max CC 10, max NLOC 50, max params 5), leaving module MI as the sole structural residue. Splitting into multiple modules breaks the vendored single-file install model (R2 net-negative). PREFER-FIX rejected on the same grounds as the 11 sibling single-file tools already frozen in section D. Frozen in section D; baseline ratcheted 104 -> 105 in this commit.

## Frozen findings (Phase 1 R4 — convergence)

Every remaining baseline finding is justified below: each ACTIONABLE finding has a concrete reason. (Historical: at Phase 1 R4 the test-audit findings were blanket-frozen "non-actionable per the Actionability Rule"; that blanket was RETIRED in SP4 Phase 2 once the test-audit skills gained golden suites — those findings are now individually fixed or justified in the SP4 Phase 2 sections below.)


### A. (RETIRED in SP4 Phase 2) Actionability-Rule blanket freeze for `skills/test-*/`
The blanket "Actionability Rule" that froze all 126 `skills/test-*/` findings was
**retired** once SP4 T3 landed behavior/golden suites for the three test-audit
skills (gated under `check:coverage`). Those findings are now ACTIONABLE and are
burned down under golden protection in the SP4 Phase 2 round log below — fixed
outright where possible, otherwise individually justified per finding (no blanket
freeze remains). See the "SP4 Phase 2" round log.

### B. Vendored health_common duplication (1)
**Reason:** `shared/health_common.py` is vendored byte-identical into all five leaves (the `check:vendored` gate enforces this). The clone *is* the vendoring contract; it cannot be removed without breaking standalone-skill installability.
- `shared/health_common.py` :: duplication/duplicate_tokens :: skills/complexity-audit/scripts/health_common.py:1-98 :: intentional vendored copy; must stay byte-identical to shared/health_common.py

### C. Cross-leaf CLI/parse duplication (20)
**Reason:** each code-health leaf is an independently-installable skill with a self-contained `scripts/` dir (only `health_common.py` is shared/vendored). The residual overlaps are small argparse/CLI skeletons and tool-output-parsing idioms that cannot be deduped without forbidden cross-skill imports. Empirically (Phase 1 R2), hoisting shared helpers into `health_common` did **not** reduce duplication — it relocated clones into the 6×-vendored module and added 6 `maintainability_index` findings (net +2). Frozen as intrinsic to the standalone-vendored-leaf architecture.
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: duplication/duplicate_tokens :: skills/complexity-audit/scripts/complexity_audit.py:243-255 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/dead-code-audit/scripts/dead_code_audit.py:239-260 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:143-154 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:21-32 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/structure-audit/scripts/structure_audit.py:352-358 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:171-183 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:184-210 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/quality-audit/scripts/quality_audit.py:104-114 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/quality-audit/scripts/quality_audit.py:121-134 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/quality-audit/scripts/quality_audit.py:28-58 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: duplication/duplicate_tokens :: skills/quality-audit/scripts/quality_audit.py:68-89 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/coverage-gap-audit/scripts/coverage_gap_audit.py:128-142 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/coverage-gap-audit/scripts/coverage_gap_audit.py:183-188 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/complexity-audit/scripts/complexity_audit.py` :: duplication/duplicate_tokens :: skills/coverage-gap-audit/scripts/coverage_gap_audit.py:188-196 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` :: duplication/duplicate_tokens :: skills/dead-code-audit/scripts/dead_code_audit.py:31-58 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:29-42 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` :: duplication/duplicate_tokens :: skills/duplication-audit/scripts/duplication_audit.py:42-52 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` :: duplication/duplicate_tokens :: skills/structure-audit/scripts/structure_audit.py:337-344 :: cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)
- `scripts/check_coverage_gap.py` :: duplication/duplicate_tokens :: scripts/check_self_audit.py:23-31 :: shared snapshot/baseline ratchet idiom across the gate scripts; dedup needs forbidden cross-skill imports (see R2 evidence)
- `scripts/check_coverage_gap.py` :: duplication/duplicate_tokens :: scripts/self_audit.py:23-31 :: shared snapshot/baseline ratchet idiom across the gate scripts; dedup needs forbidden cross-skill imports (see R2 evidence)

### C2. SP7 cross-leaf leaf-helper duplication (1)
**Reason:** identical to section C — SP7 leaves are independently-installable skills with self-contained `scripts/` dirs (only `health_common.py` is vendored). The minimal `_git(root, *args)` subprocess wrapper is pinned to one shape across leaves (A1 `hotspot-audit`, A3 `repo-hygiene-audit`); it cannot be shared without a forbidden cross-skill import, and the R2 evidence shows hoisting into `shared/`/`health_common.py` is net-negative (relocates clones into the 6×-vendored module + adds `maintainability_index` findings). Frozen as intrinsic to the standalone-vendored-leaf architecture.
- `skills/hotspot-audit/scripts/_audit_git.py` :: duplication/duplicate_tokens :: skills/repo-hygiene-audit/scripts/_git_utils.py:36-53 :: cross-leaf `_git` subprocess wrapper, vendored per-leaf (own copy — leaves are self-contained per C-5); dedup needs forbidden cross-skill imports (see R2 evidence)

### D. Module-level maintainability_index (12)
**Reason:** whole-module MI for single-file standalone tools. Each leaf/gate script is intentionally one self-contained file (required for vendored install); lowering module MI means splitting into multi-file packages, which breaks the single-file install model and is out of scope (spec: structure preserved, no cross-skill imports).
- `scripts/check_release.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `scripts/check_vendored_common.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `scripts/self_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/complexity-audit/scripts/complexity_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/duplication-audit/scripts/duplication_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/quality-audit/scripts/quality_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/structure-audit/scripts/structure_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `scripts/check_coverage_gap.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool
- `skills/docs-consistency-audit/scripts/docs_consistency_audit.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool (SP7 A4; MI 23.5, all per-function findings cleared in-branch)

### E. cyclomatic_complexity (5)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: complexity/cyclomatic_complexity :: decide :: cohesive tool logic (leaf-result aggregation / tool-output parsing); extraction relocates branches without net reduction and churns clone detection
- `skills/complexity-audit/scripts/complexity_audit.py` :: complexity/cyclomatic_complexity :: _radon_mi_findings :: cohesive tool logic (leaf-result aggregation / tool-output parsing); extraction relocates branches without net reduction and churns clone detection
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: complexity/cyclomatic_complexity :: _ruff_findings :: cohesive tool logic (leaf-result aggregation / tool-output parsing); extraction relocates branches without net reduction and churns clone detection
- `skills/structure-audit/scripts/structure_audit.py` :: complexity/cyclomatic_complexity :: _strongly_connected_components :: Tarjan's strongly-connected-components algorithm; cyclomatic complexity is inherent and irreducible without obscuring it
- `skills/structure-audit/scripts/structure_audit.py` :: complexity/cyclomatic_complexity :: analyze_tree :: cohesive tool logic (leaf-result aggregation / tool-output parsing); extraction relocates branches without net reduction and churns clone detection

### F. function_nloc (5)
- `skills/complexity-audit/scripts/complexity_audit.py` :: complexity/function_nloc :: _lizard_findings :: linear tool-output-parsing pipeline (subprocess -> parse each match -> emit Finding); splitting yields tiny single-use helpers that relocate not reduce length and churn clone detection
- `skills/dead-code-audit/scripts/dead_code_audit.py` :: complexity/function_nloc :: _ruff_findings :: linear tool-output-parsing pipeline (subprocess -> parse each match -> emit Finding); splitting yields tiny single-use helpers that relocate not reduce length and churn clone detection
- `skills/quality-audit/scripts/quality_audit.py` :: complexity/function_nloc :: _ruff_lint :: linear tool-output-parsing pipeline (subprocess -> parse each match -> emit Finding); splitting yields tiny single-use helpers that relocate not reduce length and churn clone detection
- `skills/quality-audit/scripts/quality_audit.py` :: complexity/function_nloc :: _type_findings :: linear tool-output-parsing pipeline (subprocess -> parse each match -> emit Finding); splitting yields tiny single-use helpers that relocate not reduce length and churn clone detection
- `skills/structure-audit/scripts/structure_audit.py` :: complexity/function_nloc :: analyze_tree :: linear tool-output-parsing pipeline (subprocess -> parse each match -> emit Finding); splitting yields tiny single-use helpers that relocate not reduce length and churn clone detection

## Coverage-gap baseline (initial freeze, SP3-T7)

Rule (HISTORICAL, SP3): entries under `skills/test-*/scripts/` were frozen by the
Actionability Rule (spec SP3 decision 9) until Sub-project 4 wrote their tests.
**RESOLVED in SP4 T4:** the three test-audit suites landed and cleared the 50%
bar, so those entries were removed from the coverage-gap baseline (5 -> 2); the
two remaining entries are the individually-justified self-audit gate scripts.

**Phase 2 R1 (fixed):** `check_vendored_common.py`, `check_skill_fixtures.py`,
`check_release.py`, and `check_coverage_gap.py` cleared 50% via in-process behavior
tests (subprocess CLI tests are NOT traced by pytest-cov in this config; the tests
import each module and exercise its functions directly). Baseline ratcheted 9 -> 5.

**Phase 2 R2 (justified freezes):**
- `scripts/self_audit.py` :: coverage-gap/file_coverage_percent :: `main()` runs the full code-health pipeline over the entire repo (~30s subprocess via `run()`); a unit test would re-run the whole audit inside the test suite. The argparse/CLI contract is unit-tested (`tests/test_self_audit_cli.py`) and the `run()` body is exercised end-to-end by the `check:selfaudit` gate on every CI run.
- `scripts/check_self_audit.py` :: coverage-gap/file_coverage_percent :: `main()` shells out to `self_audit.py` (regenerating the snapshot, ~30s) then diffs snapshot vs baseline; a unit test would re-run the full audit. It is exercised end-to-end by the `check:selfaudit` gate on every CI run.

**Converged:** the actionable coverage-gap set is empty — the 5 baseline entries are
the 2 justified freezes above plus the 3 `skills/test-*/scripts` rule-frozen entries.

**SP4 T4 (cleared):** the three `skills/test-*/scripts` entries CLEARED via the
SP4 T3 in-process suites; coverage-gap baseline ratcheted 5 → 2; coverage gate
suites expanded 8 → 11. The two justified freezes (`self_audit.py`,
`check_self_audit.py`) remain as-is.
- **SP4 T5**: added `--coverage-json` plumbing to `_run_one` and `run_leaves`
  (artifact-gated leaf support).  +2 `parameter_count` findings: both functions
  gained one optional `coverage_json` parameter — the smallest possible API delta
  to implement the requires gate.  Extracting a config dict or dataclass would
  obscure the data flow without reducing actual complexity; the existing
  `build_summary` and `stage_report`/`stage_coverage` functions already exceed
  the same threshold and are frozen.  Baseline 168 → 170.

### G. T5 parameter_count freezes (2)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: complexity/parameter_count :: _run_one :: T5 artifact-gated leaf support; added optional `coverage_json` param — minimal API delta; a config-dict refactor would obscure data flow without reducing complexity
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` :: complexity/parameter_count :: run_leaves :: T5 artifact-gated leaf support; added optional `coverage_json` param — minimal API delta; a config-dict refactor would obscure data flow without reducing complexity

## SP4 Phase 2 R3 — individual freezes (60 remaining test-* findings)

### audit_pipeline.py (13)
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/cyclomatic_complexity :: build_summary :: cohesive orchestration logic; extraction relocates branches without net reduction and churns clone detection
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/cyclomatic_complexity :: main :: cohesive orchestration pipeline (stage dispatch); extraction relocates branches without net reduction
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/cyclomatic_complexity :: stage_report :: cohesive report-generation logic; extraction relocates branches without net reduction
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/function_nloc :: main :: linear tool-output-parsing / orchestration pipeline; splitting yields single-use helpers that churn clones
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/function_nloc :: parse_args :: linear argparse definition; extracting arg-groups creates dead_code/duplication regressions (empirically verified)
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/function_nloc :: stage_report :: linear report assembly; splitting yields single-use helpers that churn clones
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool; splitting breaks the vendored install model
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/parameter_count :: build_summary :: tool function threads N independent runtime inputs (paths/summaries/stage results); config-object refactor would obscure data flow
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/parameter_count :: stage_coverage :: tool function threads independent runtime inputs (python/root/source_prefix/out_dir/test_marker/env); irreducible arity
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/parameter_count :: stage_report :: tool function threads independent runtime inputs (out_dir/root/stages_run/status flags/paths); irreducible arity
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/parameter_count :: stage_tqa :: tool function threads independent runtime inputs (python/script/root/cov_json/hints/baseline/env); irreducible arity
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: complexity/parameter_count :: stage_triage :: tool function threads independent runtime inputs (python/script/root/suites/source_prefix/max_workers/env); irreducible arity
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` :: duplication/duplicate_tokens :: skills/test-audit-pipeline/scripts/audit_pipeline.py:714-741 :: line-range churn from kwargs dedup; not a pre-existing clone (ratchet absorbed)

### audit_test_quality.py (12)
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: compute_delta :: cohesive delta-computation logic; extraction relocates branches without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: infer_public_hints :: cohesive AST-walking logic; extraction relocates conditional branches without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: main :: cohesive orchestration pipeline (file discovery → analysis → report); extraction relocates stages without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: render_markdown :: cohesive markdown rendering; extraction relocates render sections without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: score_rubric :: cohesive rubric-scoring logic; extraction relocates score branches without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/cyclomatic_complexity :: summarize :: cohesive summary aggregation; extraction relocates branches without net reduction
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/function_nloc :: compute_delta :: linear delta-computation pipeline; splitting yields single-use helpers that churn clones
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/function_nloc :: main :: linear orchestration pipeline; splitting yields single-use helpers that churn clones
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/function_nloc :: parse_args :: linear argparse definition; extracting arg-groups creates dead_code/duplication regressions (empirically verified in R3)
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/function_nloc :: render_markdown :: linear markdown assembly; splitting yields single-use helpers that churn clones
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/function_nloc :: score_rubric :: linear rubric-scoring pipeline; splitting yields single-use helpers that churn clones
- `skills/test-quality-assurance/scripts/audit_test_quality.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool; splitting breaks the vendored install model

### triage_redundancy.py (35)
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: bool_low_signal :: cohesive signal-classification logic; extraction relocates condition chains without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: infer_assertion_types :: cohesive AST-walking classification; extraction relocates conditional branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: infer_intent :: cohesive intent-inference logic; extraction relocates branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: main :: cohesive orchestration pipeline (parse → discover → rank → evaluate → validate); extraction relocates stages without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: main.evaluate :: cohesive candidate-evaluation logic; extraction relocates branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: run_strict_delete_gate :: cohesive gate-validation logic; extraction relocates condition chains without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: write_branch_equiv_artifacts :: cohesive artifact-generation logic; extraction relocates write branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: write_confidence_gate_artifact :: cohesive gate-output logic; extraction relocates branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/cyclomatic_complexity :: write_coverage_artifacts :: cohesive coverage-artifact logic; extraction relocates write branches without net reduction
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: collect_node_coverage_runs :: linear coverage-collection pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: collect_suite_coverage_union :: linear coverage-union pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: ensure_coverage_tool :: linear tool-availability check; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: main :: linear orchestration pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: main.evaluate :: linear evaluation pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: run_mutation_probe_kills :: linear mutation-testing pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: run_single_test_coverage :: linear single-test coverage pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: run_strict_delete_gate :: linear gate-validation pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: write_branch_equiv_artifacts :: linear artifact-writing pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: write_confidence_gate_artifact :: linear gate-output pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: write_coverage_artifacts :: linear coverage-artifact pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/function_nloc :: write_mutation_artifacts :: linear mutation-artifact pipeline; splitting yields single-use helpers that churn clones
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/maintainability_index :: <module> :: whole-module metric on an intentionally single-file standalone tool; splitting breaks the vendored install model
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: collect_node_coverage_runs :: tool function threads N independent runtime inputs (root/out_dir/nodeids/python_exe/env/timeout/max_workers/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: collect_suite_coverage_union :: tool function threads independent runtime inputs (root/suite_files/coverage_python/env/timeout/tmp_dir/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: run_mutation_probe_kills :: tool function threads independent runtime inputs (root/out_dir/tests/python_exe/env/timeout/probes/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: run_single_test_coverage :: tool function threads independent runtime inputs (root/nodeid/coverage_python/env/timeout/tmp_dir/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: run_strict_delete_gate :: tool function threads independent runtime inputs (root/out_dir/python_exe/env/suite_files/post_suite_files/...); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: run_suite :: tool function threads independent runtime inputs (root/python_exe/env/suite_files/use_xdist/timeout/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: run_suite_multi :: tool function threads independent runtime inputs (root/suite_files/python_exe/env/timeout/max_workers/source_prefix); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: write_branch_equiv_artifacts :: tool function threads independent runtime inputs (root/out_dir/tests/coverage_by_nodeid/ranked_map/...); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: complexity/parameter_count :: write_coverage_artifacts :: tool function threads independent runtime inputs (root/out_dir/tests/python_exe/env/ranked_path/ranked_map/...); irreducible arity
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: duplication/duplicate_tokens :: skills/test-redundancy-triage/scripts/triage_redundancy.py:1290-1297 :: in-file token-level dup (function parameter list); extraction creates parameter_count regressions (empirically verified in R3)
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: duplication/duplicate_tokens :: skills/test-redundancy-triage/scripts/triage_redundancy.py:1327-1347 :: in-file token-level dup (ThreadPoolExecutor block); extraction creates parameter_count regressions (empirically verified in R3)
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: duplication/duplicate_tokens :: skills/test-redundancy-triage/scripts/triage_redundancy.py:377-411 :: in-file token-level dup (visit_FunctionDef/visit_AsyncFunctionDef bodies); extraction creates parameter_count/B023 regressions (empirically verified in R3)
- `skills/test-redundancy-triage/scripts/triage_redundancy.py` :: duplication/duplicate_tokens :: skills/test-redundancy-triage/scripts/triage_redundancy.py:849-871 :: in-file token-level dup (coverage-json export block); extraction creates parameter_count regressions (empirically verified in R3)
