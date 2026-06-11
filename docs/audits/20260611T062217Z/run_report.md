# SP8 Track G — Run Report (B4 contract)

- **schema_version:** 1
- **repo_root:** `/home/jakub/projects/repo-audit-skills`
- **started_utc:** 2026-06-11T06:22:17Z  |  **finished_utc:** 2026-06-11T08:19:29Z
- **orchestrator_skill_version:** 0.3.1
- **HEAD (final):** dc463e5  |  **plan commit (start):** 15682c6

## Lanes (from G0 bootstrap probe)

| Lane | State |
|---|---|
| bootstrap | degraded |
| code-health-python | full |
| coverage-python | full |
| hygiene | full |
| orchestration | manual |
| performance | manual |
| security | full |
| test-python | full |

## Findings totals by signal (G1 diagnosis, canonical lane outputs)

| Signal | Count |
|---|---|
| SECURITY | 64 |
| DECOMPOSE | 57 |
| SIMPLIFY | 31 |
| EXTRACT | 23 |
| LINT | 18 |
| RESTRUCTURE | 6 |
| MERGE | 5 |
| TEST | 1 |
| **TOTAL** | **205** |

## Backlog

- **accepted (fixes applied):** 33 — 18 docs refs + 13 hashlib + 1 tmp + 1 try_except
- **deferred (frozen, individually justified):** 49 — security residual (26 B603, 17 B404, 4 B607, 2 B105 FP)
- **coverage_gated:** 0

## Batches (per G2 task + per Phase-2 round; evidence = commit SHA + gate output)

| id | signal | result | evidence |
|---|---|---|---|
| G0-bootstrap | bootstrap | accepted | 3d0af2d — bootstrap report: 5 FULL lanes, perf/orch manual, bootstrap degraded |
| G1-diagnosis | diagnosis | accepted | 138d068 — 8 lanes: security 64, docs 18, hygiene 0, dependency 0, umbrella ADVISE 108, hotspot 15, coverage pass, test-eff N/A (mutmut tool error) |
| G2-0-gate_common | LINT | accepted | c14476e — gate_common verdict library; check_self_audit rewired onto gate_main(GateSpec); check:selfaudit 107==107 (0 new/0 stale); 5 gates green; test_check_self_audit byte-unchanged |
| G2-1-docs-leaf-fix | LINT | accepted | 769c450 — _script_for_tokens skips out-of-root tokens (no more ValueError crash); regression test; real-repo unprefixed docs run now completes; 5 gates green |
| G2-2-check-security | SECURITY | accepted | e6bdd30 — thin gate wrapper, production scope; live vs empty baseline: fail 64; check:selfaudit clean |
| G2-3-check-hygiene | LINT | accepted | c20bedb — unprefixed full-repo gate; live: pass 0; check:selfaudit clean |
| G2-4-check-docs | LINT | accepted | 1496601 — living-docs scope gate; live: fail 18 doc_path_missing; check:selfaudit clean |
| G2-5-check-dependency | LINT | accepted | e11d52a — production scope gate; live: pass 0 (manifest:false); check:selfaudit clean |
| G2-6-runbooks | docs | accepted | b245252 — 4 runbooks cloning coverage-gap.md format |
| G3-coverage-ratchet | TEST | accepted | 3e80276 — coverage baseline 2->1 (check_self_audit.py covered); check:coverage 1==1 |
| G4-R1-fixes | mixed | accepted | dbd5416 — 18 docs refs + 13 hashlib (usedforsecurity=False re-vendored) + 1 tmp + 1 try_except; check:vendored green; check:selfaudit 107==107; security leaf 64->49; docs 18->0 |
| G4-R1-seed-wire | SECURITY | accepted | 879fbd5 — seed baselines (security 49 frozen per-finding, hygiene/docs/dependency []); wire 9-gate chain; npm run check = 9 gates green |
| G4-R2-shrink | SECURITY | discarded | dc463e5 — no honest shrink: 2 B105 FPs (rename=schema churn, nosec=suppression), 47 subprocess findings intrinsic; baseline unchanged 49 |
| G4-R3-structural | DECOMPOSE | discarded | dc463e5 — no attempt taken: hotspot top-3 are frozen single-file tools; ledger (Phase-1 R2, SP4-R3) shows extraction net-negative; equality gate would discard; baseline 107 unchanged |
| G4-R4-converge | none | accepted | dc463e5 — convergence declared; all baselines hold at equality; zero unjustified |

## Verification (real exit codes, this task)

| command | exit_code |
|---|---|
| `npm run check` | 0 |
| `python3 -m pytest --collect-only -q` | 0 |
| `python3 -m pytest tests -q` | 0 |

`npm run check` = **9 gates** all `"status": "pass"` (vendored, fixtures, release, selfaudit 107==107, security 49==49, hygiene 0==0, docs 0==0, dependency 0==0, coverage 1==1).

## C-8 expected vs actual

| Item | Expected | Actual |
|---|---|---|
| repo-A `npm run check` | 9 gates green, C-1 order | **9 gates green** ✓ |
| `check:selfaudit` | equality; 107 ± line-pin swaps | **107 == 107** (hashlib edit in-place, finding-neutral; 0 swaps needed) ✓ |
| `check:security` baseline | ≈64−fixes (~47–50 frozen) | **49** (64 − 15 fixed: 13 hashlib + 1 tmp + 1 try_except) ✓ |
| `check:hygiene` baseline | `[]` | **[]** (0 pre-seed) ✓ |
| `check:docs` baseline | ≈0–5 | **[]** (0; all 18 doc_path_missing fixed) ✓ |
| `check:dependency` baseline | `[]` | **[]** (manifest:false) ✓ |
| `check:coverage` | green; baseline 2→1 | **pass, 1 == 1** ✓ |
| repo-A collect-only | 645 + N, zero errors | **675** (645 + 30 gate/leaf tests), zero errors ✓ |
| Run report | committed, B4 complete | this file ✓ |
| Pushes/tags/releases | ZERO | **ZERO** ✓ |

## Frozen-entry accounting

- **security_frozen.md:** 49 entries, every one individually justified (per-class rationale named per file). **Zero unjustified.**
- **self_audit_baseline.json:** 107 (unchanged; the SP8 gate code is finding-clean — gate_main/normalize_findings/GateSpec exercised in production via check_self_audit; the 4 wrappers stayed clone-free).
- hygiene / docs / dependency baselines: empty `[]` (no frozen logs).

## Warnings

- Raw .self_audit_out/coverage/coverage.json (284 KB) NOT committed per C-6; coverage-gap leaf findings + report committed under the run dir instead.
- test-effectiveness lane produced NO kill-rate data: mutmut baseline collection fails on all three top-hotspot files because their owning suites contain subprocess-integration tests (e.g. test_byte_identical_across_runs) incompatible with mutmut's mutants/ sandbox; the leaf also raises an uncaught CalledProcessError (_pipeline.py:74) instead of a clean ToolError. Two SP9-backlog items recorded in G1_diagnosis_summary.md.
- performance and orchestration lanes are manual for repo-A (no benchmark surface; verification-before-completion not mirrored) per the G0 bootstrap probe.
- HEAD started at 15682c6 (the SP8 plan commit, docs-only on top of 14fc35b that the plan's empirical pre-flight pinned); npm run check was green there, so the run proceeded per the goal's pre-flight rule.

