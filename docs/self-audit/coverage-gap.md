# Testedness gate (check:coverage)

`npm run check:coverage` (part of `npm run check`) does three things:
1. Runs every pytest suite (root + 7 skills) as separate processes under
   pytest-cov (separate processes — the suites collide if collected together).
2. Combines coverage into `.self_audit_out/coverage/coverage.json`.
3. Runs the coverage-gap-audit leaf over the production scope and ratchets the
   normalized findings against `scripts/coverage_gap_baseline.json`.

A finding here = an under-tested production file = NOT safe to refactor.
This is the machine-readable Actionability Rule from the dogfooding run.

To use the leaf on a target repo:

    python -m pytest tests -q --cov --cov-report= && python -m coverage json -o coverage.json
    python3 skills/coverage-gap-audit/scripts/coverage_gap_audit.py \
      --root . --source-prefix src/ --coverage-json coverage.json --out-dir /tmp/covgap
