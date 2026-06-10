# Frozen self-audit findings (Actionability Rule)

Each entry: path :: leaf/metric :: reason.

## Round log

- **R1** (fix): cleared 15 lint findings in `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/check_release.py` (E401/E702/E501/format_drift). Baseline 191 -> 176. 0 frozen. (A parallel leaf-lint attempt was discarded: line-wrapping the near-identical leaf scripts churns `duplicate_tokens` line-range symbols and pushed `_vulture_findings` over the nloc threshold — a regression.)
- **R2** (attempted FIX, DISCARDED): hoisting `ToolError`/`rel`/`iter_python_files` into `shared/health_common.py` traded 17 cross-leaf clones for 13 vendored-copy clones + 6 new `maintainability_index` findings (net +2). `health_common.py` is vendored byte-identical into all 5 leaves, so any code placed there is cloned 6×. Conclusion: cross-leaf duplication is intrinsic to the standalone-vendored-leaf architecture — see freeze rationale below.
- **R3** (fix): fixed B904 in the umbrella + wrapped 13 E501 across the six code-health scripts (+ ruff-format polish on structure_audit.py). Baseline 176 -> 162. 0 real regressions (duplication line-range symbols churned, which is expected and absorbed by the ratchet).
- **R4** (converge): froze the 36 residual actionable findings (17 duplication, 9 module-MI, 5 cyclomatic, 5 nloc) with concrete per-finding justifications + the 126 non-actionable test-audit findings (Actionability Rule). Baseline stays 162 (no code change). **Actionable set is now empty — converged.**
- **SP3-T1**: added TEST to SIGNALS + EFFORT; re-vendored; ratchet absorbed duplication line-range churn (no net new findings).
- **SP3-T4**: added the `coverage-gap-audit` leaf (`coverage_gap_audit.py`, ruff-clean + formatted). Self-audit 162 -> 165 (+3 net): +1 module-MI (section D) and +7 cross-leaf CLI/parse clones involving the new leaf (section C), offset by -5 pre-existing clone-pairs that jscpd re-attributed to the leaf's clone groups. All churn is 100% attributable to introducing the leaf into duplication scope; frozen by the same standalone-vendored-leaf rationale (this front-loads the freeze the plan placed at T5, to keep every commit green).

## Frozen findings (Phase 1 R4 — convergence)

Every remaining baseline finding is justified below: each ACTIONABLE finding has a concrete reason; the test-audit findings are non-actionable per the Actionability Rule. After this round the actionable set is empty (every actionable finding is either fixed in R1/R3 or justified-frozen here).


### A. Non-actionable: untested test-audit scripts (126)
**Rule (Actionability Rule, spec decision 7):** the migrated `test-audit-pipeline`, `test-quality-assurance`, and `test-redundancy-triage` scripts ship no behavior/golden tests in this package, so any refactor is unguarded. They are audited and tracked but never refactored. All findings whose path is under `skills/test-*/` are frozen by this rule.

### B. Vendored health_common duplication (1)
**Reason:** `shared/health_common.py` is vendored byte-identical into all five leaves (the `check:vendored` gate enforces this). The clone *is* the vendoring contract; it cannot be removed without breaking standalone-skill installability.
- `shared/health_common.py` :: duplication/duplicate_tokens :: skills/complexity-audit/scripts/health_common.py:1-98 :: intentional vendored copy; must stay byte-identical to shared/health_common.py

### C. Cross-leaf CLI/parse duplication (18)
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

### D. Module-level maintainability_index (10)
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
