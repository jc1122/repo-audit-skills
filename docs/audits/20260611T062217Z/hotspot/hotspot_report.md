# hotspot-audit report

## DECOMPOSE (9)
- `scripts/check_release.py:1` scripts/check_release.py -- churn_complexity_product=2028 [medium]
- `scripts/self_audit_baseline.json:1` scripts/self_audit_baseline.json -- churn_complexity_product=7728 [high]
- `scripts/self_audit_frozen.md:1` scripts/self_audit_frozen.md -- churn_complexity_product=2730 [medium]
- `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:1` skills/code-health-audit-pipeline/scripts/code_health_pipeline.py -- churn_complexity_product=2648 [medium]
- `skills/complexity-audit/scripts/complexity_audit.py:1` skills/complexity-audit/scripts/complexity_audit.py -- churn_complexity_product=1488 [low]
- `skills/dead-code-audit/scripts/dead_code_audit.py:1` skills/dead-code-audit/scripts/dead_code_audit.py -- churn_complexity_product=1452 [low]
- `skills/duplication-audit/scripts/duplication_audit.py:1` skills/duplication-audit/scripts/duplication_audit.py -- churn_complexity_product=1146 [low]
- `skills/quality-audit/scripts/quality_audit.py:1` skills/quality-audit/scripts/quality_audit.py -- churn_complexity_product=1686 [low]
- `skills/structure-audit/scripts/structure_audit.py:1` skills/structure-audit/scripts/structure_audit.py -- churn_complexity_product=1635 [low]

## RESTRUCTURE (6)
- `README.md:1` README.md<->scripts/check_release.py -- temporal_coupling_ratio=0.83 [medium]
- `scripts/check_release.py:1` scripts/check_release.py -- author_concentration=1 [low]
- `scripts/check_release.py:1` scripts/check_release.py<->scripts/check_skill_fixtures.py -- temporal_coupling_ratio=1 [medium]
- `scripts/self_audit_baseline.json:1` scripts/self_audit_baseline.json -- author_concentration=1 [low]
- `scripts/self_audit_baseline.json:1` scripts/self_audit_baseline.json<->scripts/self_audit_frozen.md -- temporal_coupling_ratio=0.92 [medium]
- `scripts/self_audit_frozen.md:1` scripts/self_audit_frozen.md -- author_concentration=1 [low]

