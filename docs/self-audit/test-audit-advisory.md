# Test-audit advisory (not a gate)

    python3 skills/test-audit-pipeline/scripts/audit_pipeline.py \
      --root . --python .venv/bin/python --suite tests --out-dir /tmp/ras-test-advisory

Advisory only; not part of `npm run check`. Surfaces weak/redundant tests in the package itself.
