# Changelog

## 0.5.18 - 2026-06-12

- Grouped the remaining test-redundancy-triage strict-gate,
  mutation-probe, and branch-equivalence parameters behind context/request
  objects while preserving fixture decisions and public CLI behavior.
- Split quality-audit lint and type finding construction into focused helpers
  while preserving byte-identical dirty-fixture CLI output.
- Ratcheted the self-audit baseline from 49 to 44 normalized identities.

## 0.5.17 - 2026-06-12

- Grouped test-redundancy-triage pytest suite and coverage run parameters into
  context objects while preserving fixture decisions and public CLI behavior.
- Ratcheted the self-audit baseline from 53 to 49 normalized identities.

## 0.5.16 - 2026-06-12

- Split test-redundancy-triage assertion and intent classifiers into focused
  helpers while preserving fixture decisions and public CLI behavior.
- Ratcheted the self-audit baseline from 55 to 53 normalized identities.

## 0.5.15 - 2026-06-12

- Split structure-audit `analyze_tree` finding assembly into focused helpers
  while preserving byte-identical dirty-fixture CLI output.
- Added direct finding-builder tests and ratcheted the self-audit baseline from
  57 to 55 normalized identities.

## 0.5.14 - 2026-06-12

- Split structure-audit's iterative Tarjan SCC search into a focused helper
  module with direct SCC coverage while preserving byte-identical CLI output.
- Ratcheted the self-audit baseline from 58 to 57 normalized identities.

## 0.5.13 - 2026-06-12

- Split test-quality-assurance public-hint inference into focused helpers while
  preserving inferred hints and CLI fixture output.
- Split dead-code-audit ruff execution, parsing, and finding construction into
  focused helpers while preserving dead-code output contracts.
- Ratcheted the self-audit baseline from 61 to 58 normalized identities.

## 0.5.12 - 2026-06-12

- Split test-quality-assurance rubric scoring and summary aggregation into
  focused helpers while preserving JSON and Markdown output contracts.
- Ratcheted the self-audit baseline from 64 to 61 normalized identities.

## 0.5.11 - 2026-06-12

- Split test-quality-assurance Markdown rendering and CLI report assembly into
  focused helpers while preserving JSON and Markdown output contracts.
- Ratcheted the self-audit baseline from 68 to 64 normalized identities.

## 0.5.10 - 2026-06-12

- Split test-quality-assurance delta comparison logic into focused helpers
  while preserving the public `compute_delta()` report shape.
- Ratcheted the self-audit baseline from 70 to 68 normalized identities.

## 0.5.9 - 2026-06-12

- Split test-quality-assurance CLI argument registration into focused helpers
  while preserving the public `parse_args()` entry point and CLI options.
- Ratcheted the self-audit baseline from 71 to 70 normalized identities.

## 0.5.8 - 2026-06-12

- Grouped test-audit-pipeline report summary inputs behind compatibility
  wrappers while preserving existing public call shapes.
- Ratcheted the self-audit baseline from 74 to 71 normalized identities.

## 0.5.7 - 2026-06-12

- Grouped code-health leaf execution inputs behind a focused run context.
- Split code-health pipeline decision gating into focused stat/predicate helpers.
- Ratcheted the self-audit baseline from 77 to 74 normalized identities.

## 0.5.6 - 2026-06-12

- Fixed test-audit-pipeline so parallel TQA and triage stages run once.
- Grouped test-audit-pipeline stage-runner inputs into focused runtime/config
  objects.
- Ratcheted the self-audit baseline from 81 to 77 normalized identities.

## 0.5.5 - 2026-06-12

- Split test-audit-pipeline report rendering and parser construction into
  focused helpers.
- Ratcheted the self-audit baseline from 84 to 81 normalized identities.
- Recorded SP11 iteration 4 convergence evidence for repo-A and repo-P.

## 0.5.4 - 2026-06-11

- Split test-redundancy-triage coverage collection and coverage-artifact
  request handling into focused helpers.
- Ratcheted the self-audit baseline from 88 to 84 normalized identities.
- Recorded SP11 iteration 3 convergence evidence for repo-A, repo-B, and
  repo-P.

## 0.5.3 - 2026-06-11

- Reduced test-redundancy-triage self-audit complexity/duplication rows through
  focused helper extraction and command-context sharing.
- Recorded SP11 iteration 2 convergence evidence for repo-A, repo-B, and
  repo-P.
- Kept all release, self-audit, security, hygiene, docs, dependency, coverage,
  and full-pytest gates green after the iteration-2 changes.

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
