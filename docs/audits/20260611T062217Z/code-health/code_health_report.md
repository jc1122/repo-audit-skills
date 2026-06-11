# code-health-audit-pipeline report — ADVISE

## DECOMPOSE (48)
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:339` stage_report [high/complexity] — Split stage_report() — complexity 43 exceeds 10
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:619` main [high/complexity] — Split main() — complexity 23 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:365` score_rubric [high/complexity] — Split score_rubric() — complexity 33 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:612` render_markdown [high/complexity] — Split render_markdown() — complexity 37 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:286` infer_intent [high/complexity] — Split infer_intent() — complexity 24 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:881` write_coverage_artifacts [high/complexity] — Split write_coverage_artifacts() — complexity 28 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1363` write_branch_equiv_artifacts [high/complexity] — Split write_branch_equiv_artifacts() — complexity 34 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1679` write_confidence_gate_artifact [high/complexity] — Split write_confidence_gate_artifact() — complexity 34 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2145` run_strict_delete_gate [high/complexity] — Split run_strict_delete_gate() — complexity 65 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2457` main [high/complexity] — Split main() — complexity 43 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2748` main.evaluate [high/complexity] — Split main.evaluate() — complexity 28 exceeds 10
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:80` decide [medium/complexity] — Split decide() — complexity 15 exceeds 10
- `skills/complexity-audit/scripts/complexity_audit.py:44` _lizard_findings [medium/complexity] — Shorten _lizard_findings() — 81 lines exceeds 50
- `skills/complexity-audit/scripts/complexity_audit.py:127` _radon_mi_findings [medium/complexity] — Split _radon_mi_findings() — complexity 12 exceeds 10
- `skills/dead-code-audit/scripts/dead_code_audit.py:126` _ruff_findings [medium/complexity] — Split _ruff_findings() — complexity 11 exceeds 10
- `skills/dead-code-audit/scripts/dead_code_audit.py:126` _ruff_findings [medium/complexity] — Shorten _ruff_findings() — 60 lines exceeds 50
- `skills/quality-audit/scripts/quality_audit.py:58` _ruff_lint [medium/complexity] — Shorten _ruff_lint() — 60 lines exceeds 50
- `skills/quality-audit/scripts/quality_audit.py:162` _type_findings [medium/complexity] — Shorten _type_findings() — 55 lines exceeds 50
- `skills/structure-audit/scripts/structure_audit.py:113` _strongly_connected_components [medium/complexity] — Split _strongly_connected_components() — complexity 13 exceeds 10
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree [medium/complexity] — Split analyze_tree() — complexity 20 exceeds 10
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree [medium/complexity] — Shorten analyze_tree() — 115 lines exceeds 50
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:281` build_summary [medium/complexity] — Split build_summary() — complexity 11 exceeds 10
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:339` stage_report [medium/complexity] — Shorten stage_report() — 175 lines exceeds 50
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:544` parse_args [medium/complexity] — Shorten parse_args() — 72 lines exceeds 50
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:619` main [medium/complexity] — Shorten main() — 134 lines exceeds 50
- `skills/test-quality-assurance/scripts/audit_test_quality.py:106` infer_public_hints [medium/complexity] — Split infer_public_hints() — complexity 14 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:294` summarize [medium/complexity] — Split summarize() — complexity 15 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:365` score_rubric [medium/complexity] — Shorten score_rubric() — 148 lines exceeds 50
- `skills/test-quality-assurance/scripts/audit_test_quality.py:539` compute_delta [medium/complexity] — Split compute_delta() — complexity 14 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:539` compute_delta [medium/complexity] — Shorten compute_delta() — 61 lines exceeds 50
- `skills/test-quality-assurance/scripts/audit_test_quality.py:612` render_markdown [medium/complexity] — Shorten render_markdown() — 171 lines exceeds 50
- `skills/test-quality-assurance/scripts/audit_test_quality.py:798` parse_args [medium/complexity] — Shorten parse_args() — 65 lines exceeds 50
- `skills/test-quality-assurance/scripts/audit_test_quality.py:865` main [medium/complexity] — Split main() — complexity 16 exceeds 10
- `skills/test-quality-assurance/scripts/audit_test_quality.py:865` main [medium/complexity] — Shorten main() — 83 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:178` infer_assertion_types [medium/complexity] — Split infer_assertion_types() — complexity 14 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:660` ensure_coverage_tool [medium/complexity] — Shorten ensure_coverage_tool() — 70 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:743` run_single_test_coverage [medium/complexity] — Shorten run_single_test_coverage() — 62 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:811` collect_suite_coverage_union [medium/complexity] — Shorten collect_suite_coverage_union() — 65 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:881` write_coverage_artifacts [medium/complexity] — Shorten write_coverage_artifacts() — 256 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1179` write_mutation_artifacts [medium/complexity] — Shorten write_mutation_artifacts() — 63 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1287` collect_node_coverage_runs [medium/complexity] — Shorten collect_node_coverage_runs() — 71 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1363` write_branch_equiv_artifacts [medium/complexity] — Shorten write_branch_equiv_artifacts() — 221 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1603` bool_low_signal [medium/complexity] — Split bool_low_signal() — complexity 18 exceeds 10
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1679` write_confidence_gate_artifact [medium/complexity] — Shorten write_confidence_gate_artifact() — 152 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2024` run_mutation_probe_kills [medium/complexity] — Shorten run_mutation_probe_kills() — 113 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2145` run_strict_delete_gate [medium/complexity] — Shorten run_strict_delete_gate() — 295 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2457` main [medium/complexity] — Shorten main() — 477 lines exceeds 50
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2748` main.evaluate [medium/complexity] — Shorten main.evaluate() — 118 lines exceeds 50

## EXTRACT (23)
- `shared/health_common.py:1` skills/complexity-audit/scripts/health_common.py:1-101 [high/duplication] — Extract shared code between shared/health_common.py and skills/complexity-audit/scripts/health_common.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:22` skills/dead-code-audit/scripts/dead_code_audit.py:31-58 [high/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/dead-code-audit/scripts/dead_code_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:28` skills/quality-audit/scripts/quality_audit.py:28-58 [high/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:238` skills/duplication-audit/scripts/duplication_audit.py:184-210 [high/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `scripts/check_coverage_gap.py:42` scripts/self_audit.py:23-31 [medium/duplication] — Extract shared code between scripts/check_coverage_gap.py and scripts/self_audit.py
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:323` skills/complexity-audit/scripts/complexity_audit.py:243-255 [medium/duplication] — Extract shared code between skills/code-health-audit-pipeline/scripts/code_health_pipeline.py and skills/complexity-audit/scripts/complexity_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:24` skills/duplication-audit/scripts/duplication_audit.py:21-32 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:188` skills/duplication-audit/scripts/duplication_audit.py:143-154 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:201` skills/coverage-gap-audit/scripts/coverage_gap_audit.py:128-142 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/coverage-gap-audit/scripts/coverage_gap_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:240` skills/dead-code-audit/scripts/dead_code_audit.py:239-260 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/dead-code-audit/scripts/dead_code_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:259` skills/structure-audit/scripts/structure_audit.py:352-358 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/structure-audit/scripts/structure_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:260` skills/coverage-gap-audit/scripts/coverage_gap_audit.py:183-188 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/coverage-gap-audit/scripts/coverage_gap_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:265` skills/coverage-gap-audit/scripts/coverage_gap_audit.py:188-196 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/coverage-gap-audit/scripts/coverage_gap_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:26` skills/duplication-audit/scripts/duplication_audit.py:42-52 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:36` skills/duplication-audit/scripts/duplication_audit.py:29-42 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:162` skills/structure-audit/scripts/structure_audit.py:337-344 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/structure-audit/scripts/structure_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:135` skills/quality-audit/scripts/quality_audit.py:68-89 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:137` skills/quality-audit/scripts/quality_audit.py:121-134 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:172` skills/quality-audit/scripts/quality_audit.py:104-114 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:222` skills/duplication-audit/scripts/duplication_audit.py:171-183 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/docs-consistency-audit/scripts/docs_consistency_audit.py:575` skills/test-effectiveness-audit/scripts/_cli.py:39-50 [medium/duplication] — Extract shared code between skills/docs-consistency-audit/scripts/docs_consistency_audit.py and skills/test-effectiveness-audit/scripts/_cli.py
- `skills/hotspot-audit/scripts/_audit_git.py:30` skills/repo-hygiene-audit/scripts/_git_utils.py:36-53 [medium/duplication] — Extract shared code between skills/hotspot-audit/scripts/_audit_git.py and skills/repo-hygiene-audit/scripts/_git_utils.py
- `skills/repo-hygiene-audit/scripts/_thresholds.py:14` skills/security-audit/scripts/_reporting.py:25-33 [medium/duplication] — Extract shared code between skills/repo-hygiene-audit/scripts/_thresholds.py and skills/security-audit/scripts/_reporting.py

## MERGE (5)
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:687` skills/test-audit-pipeline/scripts/audit_pipeline.py:714-741 [high/duplication] — Merge duplicated block within skills/test-audit-pipeline/scripts/audit_pipeline.py
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:340` skills/test-redundancy-triage/scripts/triage_redundancy.py:377-411 [high/duplication] — Merge duplicated block within skills/test-redundancy-triage/scripts/triage_redundancy.py
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:774` skills/test-redundancy-triage/scripts/triage_redundancy.py:849-871 [medium/duplication] — Merge duplicated block within skills/test-redundancy-triage/scripts/triage_redundancy.py
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:887` skills/test-redundancy-triage/scripts/triage_redundancy.py:1290-1297 [medium/duplication] — Merge duplicated block within skills/test-redundancy-triage/scripts/triage_redundancy.py
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1035` skills/test-redundancy-triage/scripts/triage_redundancy.py:1327-1347 [medium/duplication] — Merge duplicated block within skills/test-redundancy-triage/scripts/triage_redundancy.py

## SIMPLIFY (31)
- `scripts/check_coverage_gap.py:1` <module> [medium/complexity] — Improve maintainability of scripts/check_coverage_gap.py — MI 46.4 below 65
- `scripts/check_release.py:1` <module> [medium/complexity] — Improve maintainability of scripts/check_release.py — MI 43.7 below 65
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:1` <module> [medium/complexity] — Improve maintainability of skills/code-health-audit-pipeline/scripts/code_health_pipeline.py — MI 31.7 below 65
- `skills/complexity-audit/scripts/complexity_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/complexity-audit/scripts/complexity_audit.py — MI 37.6 below 65
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/coverage-gap-audit/scripts/coverage_gap_audit.py — MI 43.2 below 65
- `skills/dead-code-audit/scripts/dead_code_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/dead-code-audit/scripts/dead_code_audit.py — MI 36.2 below 65
- `skills/docs-consistency-audit/scripts/docs_consistency_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/docs-consistency-audit/scripts/docs_consistency_audit.py — MI 23.5 below 65
- `skills/duplication-audit/scripts/duplication_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/duplication-audit/scripts/duplication_audit.py — MI 39.6 below 65
- `skills/quality-audit/scripts/quality_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/quality-audit/scripts/quality_audit.py — MI 33.6 below 65
- `skills/structure-audit/scripts/structure_audit.py:1` <module> [medium/complexity] — Improve maintainability of skills/structure-audit/scripts/structure_audit.py — MI 24.3 below 65
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:1` <module> [medium/complexity] — Improve maintainability of skills/test-audit-pipeline/scripts/audit_pipeline.py — MI 25.6 below 65
- `skills/test-quality-assurance/scripts/audit_test_quality.py:1` <module> [medium/complexity] — Improve maintainability of skills/test-quality-assurance/scripts/audit_test_quality.py — MI 3.8 below 65
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1` <module> [medium/complexity] — Improve maintainability of skills/test-redundancy-triage/scripts/triage_redundancy.py — MI 0.0 below 65
- `scripts/check_vendored_common.py:1` <module> [low/complexity] — Improve maintainability of scripts/check_vendored_common.py — MI 64.2 below 65
- `scripts/self_audit.py:1` <module> [low/complexity] — Improve maintainability of scripts/self_audit.py — MI 62.8 below 65
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:161` _run_one [low/complexity] — Reduce parameters of _run_one() — 6 exceeds 5
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:194` run_leaves [low/complexity] — Reduce parameters of run_leaves() — 6 exceeds 5
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:93` stage_coverage [low/complexity] — Reduce parameters of stage_coverage() — 6 exceeds 5
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:134` stage_tqa [low/complexity] — Reduce parameters of stage_tqa() — 9 exceeds 5
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:184` stage_triage [low/complexity] — Reduce parameters of stage_triage() — 10 exceeds 5
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:281` build_summary [low/complexity] — Reduce parameters of build_summary() — 10 exceeds 5
- `skills/test-audit-pipeline/scripts/audit_pipeline.py:339` stage_report [low/complexity] — Reduce parameters of stage_report() — 12 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:494` run_suite [low/complexity] — Reduce parameters of run_suite() — 7 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:516` run_suite_multi [low/complexity] — Reduce parameters of run_suite_multi() — 7 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:743` run_single_test_coverage [low/complexity] — Reduce parameters of run_single_test_coverage() — 7 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:811` collect_suite_coverage_union [low/complexity] — Reduce parameters of collect_suite_coverage_union() — 7 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:881` write_coverage_artifacts [low/complexity] — Reduce parameters of write_coverage_artifacts() — 11 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1287` collect_node_coverage_runs [low/complexity] — Reduce parameters of collect_node_coverage_runs() — 8 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:1363` write_branch_equiv_artifacts [low/complexity] — Reduce parameters of write_branch_equiv_artifacts() — 11 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2024` run_mutation_probe_kills [low/complexity] — Reduce parameters of run_mutation_probe_kills() — 8 exceeds 5
- `skills/test-redundancy-triage/scripts/triage_redundancy.py:2145` run_strict_delete_gate [low/complexity] — Reduce parameters of run_strict_delete_gate() — 15 exceeds 5

## TEST (1)
- `scripts/self_audit.py:1` <file> [high/coverage-gap] — Add behavior tests covering scripts/self_audit.py (coverage 0.0% < 50.0%)

