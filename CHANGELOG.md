# Changelog

## 0.5.2 - 2026-06-11

- Added the full-pytest aggregate gate so all 17 skill/root suites run in
  isolated import contexts.
- Added counted `trusted_subprocess` suppressions to security-audit and
  ratcheted the repo security baseline from 49 findings to 0.
- Added counted hotspot family policy suppressions for declared coupling pairs
  and explicit single-maintainer repositories while keeping churn-complexity
  findings unsuppressible.
- Bumped the GitHub Actions workflow runtimes to checkout v5, setup-node v6
  with Node 22, and setup-python v6.

## 0.5.1 - 2026-06-11

- Updated docs-consistency to track-only path resolution.
- Relaxed complexity MI boundaries with an MI floor and entrypoint MI reporting updates.
- Ratcheted self-audit baseline from 106 to 92.

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
