# complexity-audit report

## Precision counters
- entrypoint_mi_relaxed: 12

## DECOMPOSE (9)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:80` decide — cyclomatic_complexity=15 (>10) [medium]
- `skills/complexity-audit/scripts/complexity_audit.py:53` _lizard_findings — function_nloc=81 (>50) [medium]
- `skills/dead-code-audit/scripts/dead_code_audit.py:145` _ruff_findings — cyclomatic_complexity=11 (>10) [medium]
- `skills/dead-code-audit/scripts/dead_code_audit.py:145` _ruff_findings — function_nloc=60 (>50) [medium]
- `skills/quality-audit/scripts/quality_audit.py:73` _ruff_lint — function_nloc=60 (>50) [medium]
- `skills/quality-audit/scripts/quality_audit.py:177` _type_findings — function_nloc=55 (>50) [medium]
- `skills/structure-audit/scripts/structure_audit.py:113` _strongly_connected_components — cyclomatic_complexity=13 (>10) [medium]
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree — cyclomatic_complexity=20 (>10) [medium]
- `skills/structure-audit/scripts/structure_audit.py:171` analyze_tree — function_nloc=115 (>50) [medium]

## SIMPLIFY (2)
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:161` _run_one — parameter_count=6 (>5) [low]
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:194` run_leaves — parameter_count=6 (>5) [low]

