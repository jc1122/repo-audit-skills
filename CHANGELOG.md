# Changelog

## 0.5.0 - 2026-06-11

- Added docs-consistency `--exclude-prefix` and placeholder token skipping for generated output paths.
- Added counted precision suppressions for placeholder docs tokens, solo-author hotspot findings, own-test temporal-coupling pairs, test-referenced vulture findings, and config-gated format checks.
- Switched self-audit duplication identities to content-hash symbols so harmless line shifts do not churn baselines.
- Reused `gate_common` in the coverage gate so stale coverage baselines fail closed and can be ratcheted down same-commit.
- Made mutmut baseline failures return a clean test-effectiveness `ToolError` instead of a traceback.
- Completed the SP9 brevity pass across all 16 skill instructions while preserving CLI flags, limits, and exit-code contracts.

## 0.4.0 - 2026-06-11

- Added deterministic release checks and installer readback for the repo-audit skill family.
- Added self-audit, security, hygiene, docs-consistency, dependency, and coverage-gate baselines.
