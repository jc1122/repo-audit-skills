# Test Quality Question Bank

Use these questions to drive a comprehensive audit and to surface hidden gaps.

## Contract and TDD Discipline

1. What are the top-level public contracts, and where is each contract tested?
2. Which tests are known to have been written after bugs (regression tests)?
3. Is there evidence of red-green-refactor in commit/PR history for critical changes?
4. Which bug classes have no dedicated regression tests?

## Unit Test Quality

1. Does each unit test have exactly one failure reason?
2. Do unit tests assert contract semantics, or incidental data layout?
3. Are invalid-input tests strict on exception type and message pattern?
4. Which unit tests are effectively mini integration tests?

## Integration Test Quality

1. Which seams (component boundaries) are tested explicitly?
2. Are integration tests validating workflows rather than internal step-by-step details?
3. Which integration tests duplicate unit-level branch checks?
4. Are cross-implementation parity tests complete for all public APIs?

## White-Box vs Black-Box Balance

1. What share of tests call private/internal functions?
2. Which white-box tests are risk-justified versus incidental?
3. Which private-API tests can be rewritten against public contracts?
4. Which critical algorithm branches need white-box protection and why?

## Oracles and Failure Diagnostics

1. Which tests rely only on shape/type checks without behavior assertions?
2. Which tests have circular oracles (same-source expected and actual)?
3. Are assertion messages diagnostic enough to triage quickly?
4. Which tests silently allow broad exception families?

## Determinism and Stability

1. Are all random tests seeded with local RNG objects?
2. Are tests robust under parallel execution and repeated runs?
3. Are global state, env vars, and caches isolated per test?
4. Which tests are known/likely to be flaky?

## Coverage and Mutation

1. Which critical modules have high statement but low branch coverage?
2. Which tests uniquely kill mutants in high-risk code?
3. Are changed-line and branch gates enforced in CI?
4. Is low mutation score due to weak assertions or missing test scenarios?

## Performance and Non-Functional Contracts

1. Are performance tests treated as explicit contracts or ad-hoc checks?
2. Are benchmark scenarios representative of production risk?
3. Are benchmark metadata fields consistent and complete?
4. Are thresholds deterministic enough for unattended CI?

## Maintainability and Change Indicators

1. Which tests are mostly change indicators (snapshots/golden)?
2. Are change indicators intentionally labeled and scoped?
3. Which large snapshot tests should be split into smaller contract checks?
4. Which tests are expensive but low-signal?

## Governance and Process

1. Is there a documented test strategy that maps to risk?
2. Who owns each major test area and quality gate?
3. What is the minimal must-pass contract suite on each commit?
4. What is the review checklist for new/modified tests?
