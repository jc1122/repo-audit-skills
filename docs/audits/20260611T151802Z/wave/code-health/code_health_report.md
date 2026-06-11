# code-health-audit-pipeline report — ADVISE

## DECOMPOSE (9)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:80` decide [medium/complexity] — Split decide() — complexity 15 exceeds 10
- `skills/complexity-audit/scripts/complexity_audit.py:53` _lizard_findings [medium/complexity] — Shorten _lizard_findings() — 81 lines exceeds 50
- `skills/dead-code-audit/scripts/dead_code_audit.py:145` _ruff_findings [medium/complexity] — Split _ruff_findings() — complexity 11 exceeds 10
- `skills/dead-code-audit/scripts/dead_code_audit.py:145` _ruff_findings [medium/complexity] — Shorten _ruff_findings() — 60 lines exceeds 50
- `skills/quality-audit/scripts/quality_audit.py:73` _ruff_lint [medium/complexity] — Shorten _ruff_lint() — 60 lines exceeds 50
- `skills/quality-audit/scripts/quality_audit.py:177` _type_findings [medium/complexity] — Shorten _type_findings() — 55 lines exceeds 50
- `skills/structure-audit/scripts/structure_audit.py:113` _strongly_connected_components [medium/complexity] — Split _strongly_connected_components() — complexity 13 exceeds 10
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree [medium/complexity] — Split analyze_tree() — complexity 20 exceeds 10
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree [medium/complexity] — Shorten analyze_tree() — 115 lines exceeds 50

## EXTRACT (22)
- `shared/health_common.py:1` skills/complexity-audit/scripts/health_common.py:1-101 [high/duplication] — Extract shared code between shared/health_common.py and skills/complexity-audit/scripts/health_common.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:22` skills/dead-code-audit/scripts/dead_code_audit.py:33-60 [high/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/dead-code-audit/scripts/dead_code_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:30` skills/quality-audit/scripts/quality_audit.py:33-63 [high/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:274` skills/duplication-audit/scripts/duplication_audit.py:184-208 [high/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `scripts/check_coverage_gap.py:46` scripts/self_audit.py:27-35 [medium/duplication] — Extract shared code between scripts/check_coverage_gap.py and scripts/self_audit.py
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:323` skills/complexity-audit/scripts/complexity_audit.py:294-306 [medium/duplication] — Extract shared code between skills/code-health-audit-pipeline/scripts/code_health_pipeline.py and skills/complexity-audit/scripts/complexity_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:33` skills/duplication-audit/scripts/duplication_audit.py:21-32 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:252` skills/coverage-gap-audit/scripts/coverage_gap_audit.py:128-142 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/coverage-gap-audit/scripts/coverage_gap_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:291` skills/dead-code-audit/scripts/dead_code_audit.py:275-296 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/dead-code-audit/scripts/dead_code_audit.py
- `skills/complexity-audit/scripts/complexity_audit.py:310` skills/structure-audit/scripts/structure_audit.py:352-358 [medium/duplication] — Extract shared code between skills/complexity-audit/scripts/complexity_audit.py and skills/structure-audit/scripts/structure_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:26` skills/duplication-audit/scripts/duplication_audit.py:42-52 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:36` skills/duplication-audit/scripts/duplication_audit.py:29-42 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:162` skills/structure-audit/scripts/structure_audit.py:337-344 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/structure-audit/scripts/structure_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:183` skills/dead-code-audit/scripts/dead_code_audit.py:297-302 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/dead-code-audit/scripts/dead_code_audit.py
- `skills/coverage-gap-audit/scripts/coverage_gap_audit.py:188` skills/duplication-audit/scripts/duplication_audit.py:210-218 [medium/duplication] — Extract shared code between skills/coverage-gap-audit/scripts/coverage_gap_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:154` skills/quality-audit/scripts/quality_audit.py:83-104 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:156` skills/quality-audit/scripts/quality_audit.py:136-149 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:191` skills/quality-audit/scripts/quality_audit.py:119-129 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/quality-audit/scripts/quality_audit.py
- `skills/dead-code-audit/scripts/dead_code_audit.py:258` skills/duplication-audit/scripts/duplication_audit.py:171-183 [medium/duplication] — Extract shared code between skills/dead-code-audit/scripts/dead_code_audit.py and skills/duplication-audit/scripts/duplication_audit.py
- `skills/duplication-audit/scripts/duplication_audit.py:143` skills/hotspot-audit/scripts/hotspot_audit.py:127-138 [medium/duplication] — Extract shared code between skills/duplication-audit/scripts/duplication_audit.py and skills/hotspot-audit/scripts/hotspot_audit.py
- `skills/hotspot-audit/scripts/_audit_git.py:30` skills/repo-hygiene-audit/scripts/_git_utils.py:36-53 [medium/duplication] — Extract shared code between skills/hotspot-audit/scripts/_audit_git.py and skills/repo-hygiene-audit/scripts/_git_utils.py
- `skills/repo-hygiene-audit/scripts/_thresholds.py:14` skills/security-audit/scripts/_reporting.py:25-33 [medium/duplication] — Extract shared code between skills/repo-hygiene-audit/scripts/_thresholds.py and skills/security-audit/scripts/_reporting.py

## SIMPLIFY (2)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:161` _run_one [low/complexity] — Reduce parameters of _run_one() — 6 exceeds 5
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:194` run_leaves [low/complexity] — Reduce parameters of run_leaves() — 6 exceeds 5

