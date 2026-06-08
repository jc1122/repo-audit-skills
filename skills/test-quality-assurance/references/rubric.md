# Test Quality Rubric

Use this rubric to score the suite as a whole and major test clusters.

## Scoring Scale

Score each dimension from 0 to 3.

1. `0`: Missing or actively harmful
2. `1`: Weak/inconsistent
3. `2`: Good baseline
4. `3`: Strong and intentional

## Dimensions

### 1. Contract Coverage
Checks whether public contracts are explicitly tested.

1. `0`: No clear mapping from contracts to tests.
2. `1`: Partial mapping; major contracts unowned.
3. `2`: Most contracts mapped; gaps known.
4. `3`: Full contract map with clear ownership and regression tests.

### 2. Behavior-First Focus (Black-Box Bias)
Checks if tests validate observable outcomes over implementation internals.

1. `0`: Mostly internal/private API coupling.
2. `1`: Mixed, but internals dominate.
3. `2`: Mostly public behavior; internals justified.
4. `3`: Strong behavior focus with explicit exceptions for justified white-box tests.

### 3. White-Box Justification
Checks if internal tests are limited to high-risk algorithm branches.

1. `0`: Internal tests are incidental and brittle.
2. `1`: Some justified, many incidental.
3. `2`: Mostly justified by risk/history.
4. `3`: Every white-box test maps to a concrete bug/risk class.

### 4. Determinism and Isolation
Checks repeatability and independence across runs.

1. `0`: Frequent nondeterminism/flakiness.
2. `1`: Some deterministic controls; still unstable.
3. `2`: Deterministic seeds/fixtures and isolated state.
4. `3`: Deterministic by design, stable under parallelization.

### 5. Assertion and Oracle Quality
Checks if assertions are strong, specific, and non-circular.

1. `0`: Weak shape checks and broad exceptions.
2. `1`: Moderate strength, many generic assertions.
3. `2`: Precise assertions for key contracts.
4. `3`: Strong oracles with focused, diagnostic failures.

### 6. Test Pyramid and Scope Discipline
Checks unit/integration/property/e2e mix and role clarity.

1. `0`: Flat suite; scope confusion.
2. `1`: Some layering, significant overlap.
3. `2`: Healthy layering with manageable overlap.
4. `3`: Intentional pyramid with clear boundaries and minimal duplication.

### 7. Coverage and Mutation Signal
Checks whether numeric gates are meaningful and risk-oriented.

Suggested baseline targets:
1. Statement coverage: `>= 85%`
2. Branch coverage: `>= 75%`
3. Changed-line coverage in PRs: `>= 90%`
4. Mutation score overall: `>= 60%`
5. Mutation score critical algorithm modules: `>= 80%`

Scoring:
1. `0`: No coverage/mutation data.
2. `1`: Coverage only, low threshold discipline.
3. `2`: Coverage and partial mutation discipline.
4. `3`: Coverage+mutation gates tied to risk hotspots.

### 8. Non-Functional Contract Coverage
Checks performance/memory/stability tests as explicit contracts.

1. `0`: No non-functional tests for critical paths.
2. `1`: Ad-hoc benchmarks only.
3. `2`: Benchmarks present with baseline workflow.
4. `3`: Enforced regression gates and reproducible benchmark practice.

## Unit vs Integration Expectations

### Unit Tests Should

1. Validate one unit contract at a time.
2. Cover edge/error cases with precise semantics.
3. Avoid integration wiring concerns unless the unit contract requires it.

### Integration Tests Should

1. Validate component seams and data-flow correctness.
2. Validate cross-implementation parity where relevant.
3. Avoid re-asserting every unit-level algorithm branch.

## White-Box vs Black-Box Guidance

### Good White-Box Targets

1. Tie-break precedence in algorithms.
2. Boundary branch behavior with historical bug risk.
3. Invariants difficult to infer from public output.

### Good Black-Box Targets

1. Public API outputs and error contracts.
2. Stable invariants observable by consumers.
3. Behavioral parity across implementations.

## Interpretation

1. `>= 20/24`: strong suite with targeted improvements.
2. `15-19/24`: workable baseline; notable weaknesses.
3. `< 15/24`: high risk; prioritize architecture-level test refactor.
