# SP10 Steady-State Ship Report

Date: 2026-06-11

## Summary

SP10 completed the precision round and steady-state dogfood loop across the
repo-audit skill family. The two precision classes were fixed at the leaf level:
docs-consistency now resolves documented paths against tracked git reality by
default, and complexity-audit relaxes module-MI findings for standalone CLI
entrypoints above the entrypoint floor while counting the relaxation.

No stale-skill purge was performed.

## Versions Shipped

| Repo | Version | Head | Release |
| --- | --- | --- | --- |
| `repo-audit-skills` | `v0.5.1` | `b7c3c12` | GitHub release `v0.5.1` |
| `repo-audit-refactor-optimize` | `v0.4.1` | `7c23276` | GitHub release `v0.4.1` |
| `perf-benchmark-skill` | `v0.3.0` | `ac89675` | no new tag; version unchanged |

## Expected vs Actual Shrink

| Repo | Expected | Actual | Evidence |
| --- | ---: | ---: | --- |
| repo-A selfaudit | `106 -> 105±` | `106 -> 92` | `self_audit_baseline.json`; `npm run check` passes `92/92` |
| repo-B wave | `13 -> ~9` | `13 -> 9` | `wave_baseline.json`; two wave gates pass `9/9` |
| repo-P wave | `59 -> actual` | `59 -> 55` | `wave_baseline.json`; two wave gates pass `55/55` |

Repo-A shrank more than expected because the entrypoint-MI relaxation dissolved
all eligible single-file CLI module-MI rows, not only the original INT-5
docs-consistency row.

## Task Ledger

| Task | Commit | Result |
| --- | --- | --- |
| T1 docs-consistency tracked-path resolution | `4dad9d2` | leaf tests, root tests, docs gate, and full `npm run check` green |
| T2 complexity entrypoint module-MI relaxation | `5c1e771` | entrypoint tests and complexity leaf suite green |
| T3 repo-A selfaudit ratchet | `29fbcf7` | baseline `106 -> 92`, full gate green |
| T4 repo-A v0.5.1 release metadata | `eba4ca7` | installer list `0.5.1`; local and fresh-clone gates green |
| T5 repo-A run report | `b7c3c12` | schema-v2 report green; wave convergence `123 == 123` identities |
| T5 repo-B docs scope fix | `a4676e8` | excludes historical `docs/superpowers` from living-doc wave scope |
| T5 repo-B wave ratchet | `b29cfcb` | baseline `13 -> 9`; two wave gates green |
| T5 repo-B v0.4.1 | `e62f613`, `e11720e` | release metadata plus SKILL.md compaction to avoid release-induced hotspot growth |
| T5 repo-B run report | `7c23276` | schema-v2 report green |
| T5 repo-P wave ratchet | `870471a` | baseline `59 -> 55`; two wave gates green |
| T5 repo-P run report | `ac89675` | schema-v2 report green |

## Structural Batch Ledger

No broad structural batch was accepted in SP10.

| Repo | Attempts | Decision |
| --- | --- | --- |
| repo-A | none accepted | remaining code-health, security, and hotspot rows are baseline debt or ordering signals |
| repo-B | none accepted | remaining helper module-MI, parameter-count, and hotspot rows deferred |
| repo-P | none accepted | benchmark pipeline decomposition and security FP classes deferred |

The only source-support change outside repo-A was the repo-B wave runner scope
fix for `docs/superpowers`, which removed an environment-dependent docs finding
class without growing a baseline.

## Convergence Outputs

| Repo | Suite | Wave / Gate |
| --- | --- | --- |
| repo-A | `npm run check`: selfaudit `92/92`, security `49/49`, hygiene/docs/dependency `0/0`, coverage `0/0` across 17 suites | wave run 1 and run 2 both `123` normalized identities, zero delta |
| repo-B | `python3 -m pytest tests/ -q`: 101 passed | two wave gates pass, count `9`, baseline `9` |
| repo-P | `python3 -m pytest -q`: 154 passed | two wave gates pass, count `55`, baseline `55` |

Fresh-clone simulations used clone basename `sp10-final-WuZHrw`:

| Repo | Fresh-clone result |
| --- | --- |
| repo-A | `npm run check` passed all 9 gates, coverage `0/0` across 17 suites |
| repo-B | 101 tests passed; wave gate `9/9` |
| repo-P | 154 tests passed; wave gate `55/55` |

## CI

| Repo | Ref | Run | Result |
| --- | --- | ---: | --- |
| repo-A | `main` | `27359873909` | success |
| repo-A | `v0.5.1` | `27359894901` | success |
| repo-B | `main` | `27359872793` | success |
| repo-B | `v0.4.1` | `27359894945` | success |
| repo-P | `main` | `27359873076` | success |

Repo-P emitted only the GitHub Actions Node 20 deprecation annotation.

## Reinstall Readback

Installed root: `~/.claude/skills` resolving to `~/.agents/skills`.

| Skill set | Readback |
| --- | --- |
| 16 repo-audit leaves | all `0.5.1` |
| `repo-audit-refactor-optimize` | `0.4.1` |
| `perf-benchmark` | `0.3.0` |
| `perf-optimization` | `0.2.0` |

Bootstrap readback probe against installed skills exited 0:
`restart_required=false`, `stop_before_discovery=false`.

## Ship Record

- Pushed repo-A, repo-B, and repo-P `main`.
- Created and pushed tags `v0.5.1` and `v0.4.1`.
- Created GitHub releases `v0.5.1` and `v0.4.1`.
- Did not create a repo-P tag because no source/version bump occurred.
- Reinstalled repo-A leaves through the node installer.
- Reinstalled repo-B, `perf-benchmark`, and `perf-optimization` by directory sync.
- Verified installed versions and bootstrap probe after reinstall.
