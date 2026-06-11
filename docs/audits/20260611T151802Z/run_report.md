# SP10 T5 Steady-State Run - repo-audit-skills

Schema: v2

## Scope

- Source skills root: `/home/jakub/projects/repo-audit-skills/skills` (`0.5.1`)
- Installed readback: `0.5.0` before T6 reinstall, expected by the ship gate
- Wave scope: `shared`, root `scripts`, and `skills/*/scripts`

## Results

| Check | Result |
| --- | --- |
| Bootstrap probe | Pass; restart_required=false, stop_before_discovery=false |
| Wave run 1 | 134 raw findings, 123 normalized identities |
| Wave run 2 | 134 raw findings, 123 normalized identities |
| Wave convergence | Pass; 0 new, 0 stale |
| `npm run check` | Pass; selfaudit 92/92, security 49/49, docs/dependency/hygiene 0/0, coverage 0/0 across 17 suites |

## Wave Totals

| Lane | Findings | Status |
| --- | ---: | --- |
| code-health | 33 | findings |
| security | 43 | findings |
| hotspot | 58 | findings |
| docs | 0 | ok |
| dependency | 0 | ok |
| hygiene | 0 | ok |

## Backlog

| Class | Decision | Rule | Evidence |
| --- | --- | --- | --- |
| wave-runner-scope | accepted | Fix living-doc scope in the runner when historical docs create path noise. | `docs/superpowers` exclusion reduced repo-A docs wave findings from 191 to 0 in runner commit `a4676e8`. |
| code-health | deferred | Defer broad vendored-leaf architecture debt unless a bounded precision fix shrinks a ratcheted baseline. | 33 findings remain; selfaudit is equality-ratcheted at 92. |
| security | deferred | Defer trusted local subprocess wrappers to the security baseline until a dedicated security round can treat them consistently. | 43 wave findings; canonical security gate passes at 49/49. |
| hotspot | deferred | Use hotspot findings for ordering future work, not as a release blocker without a bounded structural candidate. | 58 findings, mostly temporal coupling among release metadata and known churn files. |

## Batches

- `4dad9d2`: docs tracked-path precision.
- `5c1e771`: entrypoint module-MI precision.
- `29fbcf7`: selfaudit baseline ratchet 106 -> 92.
- `eba4ca7`: repo-A v0.5.1 release metadata, fresh-clone simulation green.
- `a4676e8`: runner living-doc support fix in repo-audit-refactor-optimize.
- No repo-A post-release structural batch accepted; remaining findings are baseline debt or hotspot ordering signals for a later refactor round.

## Warnings

- Installed repo-audit skills still read as 0.5.0 until the T6 human-gated reinstall.
- Bootstrap helper skills are unavailable, so raw CLI fallback remains active.
- No benchmark surface detected for repo-A.
