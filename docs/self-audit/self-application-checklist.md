# Self-application checklist (X1.3, standing rule)

The family owns deterministic audit skills but has historically pointed them at
*other* repos, not at itself. **Standing rule (L-1 compatible — tests are not
findings, so this does not break the freeze):** each post-freeze iteration MUST
pick one `not-yet-applied` family skill and run it on the family (repo-A/B/P),
recording the result in the ledger. A skill is "applied-to-family" once it has run
against the family's own tree in the installed wave/gates or a recorded one-off and
its actionable output has been triaged.

Legend: ✅ applied-to-family (runs in wave/gates on the family) · ⬜ not yet applied · 🎯 the iteration target.

| Family skill | Applied to family? | How / where | Notes |
| --- | :---: | --- | --- |
| complexity-audit | ✅ | code-health lane (self-audit wave) | per-function CC/length |
| duplication-audit | ✅ | code-health lane | line-pinned rows (lesson L5) |
| dead-code-audit | ✅ | code-health lane | |
| structure-audit | ✅ | code-health lane | import cycles / god-modules |
| quality-audit | ✅ | code-health lane | ruff/format/type |
| docs-consistency-audit | ✅ | docs lane + check_docs_consistency gate | CLI-flag drift |
| dependency-audit | ✅ | dependency lane | stdlib-only enforcement |
| repo-hygiene-audit | ✅ | hygiene lane | tracked-tree hygiene |
| security-audit | ✅ | security lane | bandit |
| exec-audit | ✅ | exec lane (SP12) | runner/JUnit/bench |
| growth-audit | ✅ | growth lane + check_growth gate | surface budget |
| hotspot-audit | ✅ | hotspot lane | churn/coupling |
| coverage-gap-audit | ✅ | coverage gate (check_coverage_gap) | testedness |
| **instruction-lint** (X1.1) | 🎯 (X3.2) | new check_instruction_lint gate | meta-findings, baselined at freeze |
| **test-redundancy-triage** | 🎯 **FIRST** | repo-A's 220-test triage suite | the gate wall-clock floor; DELETE rows → L-5 speed batches; bootstrap probe TIMED OUT at 300s on the 8-lane wave — this suite is the prime suspect |
| test-effectiveness-audit | ⬜ | (mutation on a hot module) | mutmut; advisory |
| test-quality-assurance | ⬜ | (TDD rubric on a suite) | 0–24 score |
| perf-benchmark | ⬜ | (the gate runner itself) | profile run_checks wall-clock |
| perf-optimization | ⬜ | (consume perf-benchmark finding) | one bounded candidate |

## Iteration log
| Iteration | Target skill | Result (rows surfaced / actioned) | Ledger ref |
| --- | --- | --- | --- |
| (X3.2) | test-redundancy-triage on repo-A 220-test suite | _pending_ | _pending_ |

**First target rationale:** the entry bootstrap probe (installed 8-lane wave on
repo-A) **timed out at the 300s budget** — the 220-test triage suite (2.3× the next
largest) is the wall-clock floor of every gate run. `test-redundancy-triage` has
never been pointed at it. DELETE-tier rows become ordinary L-5 speed batches that
directly attack the floor; tests are not findings, so the freeze does not bind them.
