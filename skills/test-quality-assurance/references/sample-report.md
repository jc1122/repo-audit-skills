# Sample Report (Abbreviated)

Use this as a formatting and calibration example. Numbers are illustrative.

## Best-Practice Rules

1. Public contracts must be explicitly tested.
2. Unit tests should assert behavior, not incidental internals.
3. Integration tests should verify seams and workflow outcomes.
4. White-box tests must be risk-justified.
5. Assertions must be precise and diagnostic.

## Conformance Summary

1. Contract coverage: partial
2. Behavior focus: mixed
3. White-box justification: moderate
4. Determinism: good
5. Assertion precision: weak for exception semantics

## Findings (Severity Ordered)

1. High: Broad exception assertions hide error-contract regressions.
2. High: Private API coupling exceeds target for black-box confidence.
3. Medium: Marker discipline inconsistent (`slow` coverage sparse).
4. Medium: Large snapshot tests act as change indicators but are not labeled as such.
5. Low: Missing examples in test strategy docs for expected unit/integration boundaries.

## Open Questions

1. Which tests are mandatory contract gates in CI?
2. Which white-box tests map to historical bug IDs?
3. What mutation threshold is required for critical modules?

## Prioritized Actions

1. Tighten exception tests (`type` + `match`) in API-facing test files.
2. Rewrite selected private-method tests to public API behavior checks.
3. Label change-indicator tests and scope them to intentional snapshots.
4. Add mutation threshold policy for core algorithm modules.
