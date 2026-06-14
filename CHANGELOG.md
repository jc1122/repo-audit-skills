# Changelog

## 0.7.2 - 2026-06-14

Convergent-family Phase 1 bookkeeping (family version sync 0.7.1 → 0.7.2 to anchor
the family's self-contained convergence-gate CI pins). No leaf code changed. The
orchestrator now runs `perf-smell-audit` as a deterministic wave lane against every
target, so repo-A is perf-smell-audited via the wave; adding perf-smell to repo-A's
*separate* self-audit engine was measured (589 findings over `skills`/`scripts`/`shared`)
and deferred to the Phase-2 self-application campaign (`docs/superpowers/SP15-CANDIDATES.md`)
to keep Phase 1 bounded. SP15 "auto-consume the remediation-scope policy in the engine"
marked resolved-by-design (the filter correctly lives at the `mprr_run` orchestration
boundary). Lesson LM2 escalated (fixed in repo-B's KPI miner).

## 0.7.1 - 2026-06-14

Self-audit baseline migrated onto the portable acceptance schema (Phase 2). The
convergence gate (`scripts/check_self_audit.py`) now reads its frozen floor from
the report-stage `finding` entries in `.repo-audit/accept.json` instead of the
legacy flat `scripts/self_audit_baseline.json`; the `scripts/remediation_excludes.json`
fixtures policy is folded in as a remediation-stage `path` entry. Provably
count-neutral: the same 40 finding identities (0 new / 0 stale). Both legacy
files removed; `check_release` repointed to require the acceptance policy. Family
version sync 0.7.0 → 0.7.1.

## 0.7.0 - 2026-06-14

New leaf: **perf-smell-audit** — a deterministic, advisory algorithmic
performance-smell audit that wraps perflint (via pylint) to emit `PERF` findings
(loop-invariant computation, wrong container types) to the shared code-health
schema. Source-level only; complementary to exec-audit's execution-level PERF
findings. Registered in the installer, `check_release`, the coverage suite, and
self-audit scope; CI installs pylint/perflint. Family version sync 0.6.1 → 0.7.0.

## 0.6.1 - 2026-06-13

SP14 family-side closeout (no audit-leaf behavior change — all 18 leaf scripts byte-identical to 0.6.0).

- Test-tree hygiene: removed unused imports/locals across 28 test files (56 ruff F401/F841/F811).
- growth-audit tests: removed 9 dead/obsolete shadowed duplicate definitions (a rewrite left-behind);
  revived 2 gap-closing tests (Gemfile + package.json dependency parsing) -> growth_audit.py coverage 83%->87%.
- Added scripts/remediation_excludes.json: durable machine-readable policy excluding intentional
  tests/fixtures from automated remediation.
- Growth allowances re-baselined at this tag (SP14 doc-growth allowances purged post-release).

## 0.6.0 - 2026-06-13

- Final SP13 release: runtime self-improvement loop hardening.
- Added the instruction-lint gate that detects SKILL.md command/section drift.
- Added loop telemetry (iteration KPI miner) and a two-tier lessons ledger.
- Added behavioral instruction-eval (advisory) for skill prompt quality.
- Added the batch allocator for worker packet sizing.
- Added the amendment-proposal protocol for safe plan amendments.
- Added `## Overview` and `## Limits` sections to 16 leaf SKILL.md docs.
- Ratcheted self-audit and instruction-lint baselines to measured deltas.
- Bumped version metadata to 0.6.0 across package.json and all 18 skill
  SKILL.md frontmatter entries.

## 0.5.21 - 2026-06-13

- Added and registered the W1 exec-audit leaf.
- Added and registered the W2 growth-audit leaf and repo-A growth gate.
- Refreshed the W5 pre-release growth allowance for W3/W4 ledger growth.

## 0.5.20 - 2026-06-12

- Release preparation for W0 behavior-change release.
- Version metadata bumped from 0.5.19 to 0.5.20 across package.json and all 16
  skill SKILL.md frontmatter entries.

## 0.5.19 - 2026-06-12

- Split test-redundancy-triage coverage bootstrap, mutation artifacts, and
  mutation-probe execution into focused helpers while preserving fixture
  decisions and public CLI behavior.
- Ratcheted the self-audit baseline from 44 to 40 normalized identities.

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
