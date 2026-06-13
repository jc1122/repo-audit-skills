# SP12 Convergent Parallel Loop Ledger

## Entry verification (2026-06-12)

Authority:

- Plan: `docs/superpowers/plans/2026-06-12-sp12-convergent-parallel-loop.md`.
- SP11 ledger tail: `docs/self-audit/2026-06-sp11-unattended-loop.md`.

SP11 entry gate:

- SP11 terminal record is closed as `BLOCKED-by-operator-order`.
- Terminal source state before SP12 plan commits was `61176a1952c5d4cf7d8db01d8a6e17956fadfe14`.
- Current repo-A `main` at SP12 start is `5246e2ae23cc9133510596031389b1830c832e2e`, matching `origin/main`.
- Last release tag remains `v0.5.19`.

Installed versions at entry:

| Repo | Installed version |
| --- | --- |
| repo-A `repo-audit-skills` leaves | `0.5.19` (16 leaves) |
| repo-B `repo-audit-refactor-optimize` | `0.4.3` |
| repo-P `perf-benchmark` | `0.3.8` |
| `perf-optimization` | `0.2.1` |

Bootstrap entry probe:

| Repo | Probe command | Exit | Summary |
| --- | --- | --- | --- |
| repo-A | `python3 /home/jakub/projects/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo /home/jakub/projects/repo-audit-skills --out-dir /tmp/sp12-entry-bootstrap/repo-a --extra-root /home/jakub/.agents/skills` | `0` | `restart_required=false`, `stop_before_discovery=false` |
| repo-B | `python3 /home/jakub/projects/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo /home/jakub/projects/repo-audit-refactor-optimize --out-dir /tmp/sp12-entry-bootstrap/repo-b --extra-root /home/jakub/.agents/skills` | `0` | `restart_required=false`, `stop_before_discovery=false` |
| repo-P | `python3 /home/jakub/projects/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo /home/jakub/projects/perf-benchmark-skill --out-dir /tmp/sp12-entry-bootstrap/repo-p --extra-root /home/jakub/.agents/skills` | `0` | `restart_required=false`, `stop_before_discovery=false` |

Worker bridge readiness:

- `python3 /home/jakub/.agents/skills/opencode-worker-bridge/scripts/opencode_worker.py doctor --json` passed.
- Readiness scope is offline installed surface only; live provider/model readiness remains to be proven by `preflight` before delegation.

W0 status:

- W0 is not present in repo-A history at entry.
- Next action: dispatch W0.1 and W0.2 as disjoint worker packets in `/tmp/sp12` worktrees. Orchestrator will read only file-backed worker status and gate tails, then re-run gates itself before any merge.

## Iteration 1 W0 gate speed + budget (2026-06-12)

### W0 worker runs

| Packet | Worktree | Run dir | Result |
| --- | --- | --- | --- |
| W0.1 full-pytest parallelization | `/tmp/sp12/repo-a-01-w0-full-pytest` | `/tmp/sp12/runs/repo-a-w0-full-pytest` | accepted |
| W0.2 coverage parallelization | `/tmp/sp12/repo-a-01-w0-coverage` | `/tmp/sp12/runs/repo-a-w0-coverage` | accepted |
| W0.3 timed runner and budget | `/tmp/sp12/repo-a-01-w0-run-checks` | `/tmp/sp12/runs/repo-a-w0-run-checks` | accepted |

Accepted commits merged by fast-forward:

- `73c3d7f` `perf(gates): parallelize full-pytest gate across suites`.
- `33a30c6` `fix(gates): normalize full-pytest snapshot tails`.
- `783e5da` `perf(gates): parallelize coverage suites with per-suite data files`.
- `343d3e0` `fix(gates): refresh coverage snapshot after parallel combine`.
- `8b7ec89` `feat(gates): add timed gate runner core`.
- `84e40ef` `feat(gates): wire timed gate runner budget`.
- `f13fb75` `fix(gates): leave generated gate snapshots untracked`.
- `ca0da7d` `fix(gates): cover and simplify timed gate runner`.
- `8cb4ca5` `chore(gates): ignore timing telemetry artifact`.
- `488288a` `chore(gates): tune initial timing budget`.

Discarded batches:

- None. Two repair follow-ups were required before acceptance:
  - W0.1 first pass produced green full-pytest runs but non-identical snapshots because pytest duration strings varied; repaired by normalizing volatile tail timing.
  - W0.3 initially tracked generated snapshot artifacts and introduced undercovered/over-complex `run_checks.py`; repaired by untracking generated artifacts, simplifying the runner, expanding tests, and ignoring the generated timing telemetry artifact.

### W0 verification

Orchestrator re-ran the gates before each merge. Final main check:

- Command: `npm run check`.
- Exit: `0`.
- Summary: `gates: 8/8 cheap, 2/2 heavy, 0 over-budget, 0 failed`.

Timing vs budget table from the final main generated timing telemetry:

| Gate | Seconds | Budget seconds |
| --- | ---: | ---: |
| vendored | 0.03 | 10 |
| fixtures | 0.96 | 15 |
| release | 0.23 | 10 |
| selfaudit | 1.72 | 20 |
| security | 1.29 | 15 |
| hygiene | 0.21 | 10 |
| docs | 0.93 | 10 |
| dependency | 0.13 | 10 |
| coverage | 111.54 | 270 |
| pytest | 117.81 | 260 |

Generated artifacts:

- The timing telemetry JSON is ignored and untracked.
- The coverage-gap snapshot JSON is ignored and untracked.
- The full-pytest snapshot JSON is ignored and untracked.

W0 issue notes:

- Isolated worktrees required `npm ci`; without `node_modules/.bin/jscpd`, duplication-audit tests failed inside W0 workers even though source behavior was not at fault.
- A transient `npm run check` failure in W0.3 left a one-row coverage snapshot for `scripts/self_audit.py`; rerunning `python3 scripts/check_coverage_gap.py` alone reset the generated snapshot to zero rows, and subsequent `python3 scripts/run_checks.py` plus `npm run check` both passed.
- Budgets were tuned only after all gates were functionally green: `coverage=270`, `pytest=260`; all cheap-gate budgets remain at their plan values.

Current state after W0 merge, before W0.4:

- repo-A `main` is ahead of `origin/main` locally.
- W0.4 ship/reinstall has not started yet.

### W0.4 ship and reinstall evidence

Release-prep worker:

- Worktree: `/tmp/sp12/repo-a-01-w0-release-prep`.
- Run dir: `/tmp/sp12/runs/repo-a-w0-release-prep`.
- Accepted commits:
  - `5611a62` `release: prepare v0.5.20`.
  - `7cb3831` `fix(release): correct v0.5.20 changelog date`.

Issues fixed during release-prep:

- The release worktree initially lacked local npm dependencies, so `node_modules/.bin/jscpd`
  was absent and duplication-audit tests failed. Running `npm ci` in that worktree restored
  the executable; focused duplication tests, self-audit, and release checks then passed.
- The first release-prep changelog entry used `2026-06-13`; the worker corrected the
  `0.5.20` heading to `2026-06-12` in commit `7cb3831`.

Local release gates:

- Release-prep `npm run check`: `gates: 8/8 cheap, 2/2 heavy, 0 over-budget, 0 failed`.
- Release-prep `npm run pack:dry-run`: produced `repo-audit-skills-0.5.20.tgz`, 351 files.
- Main after fast-forward `npm run check`: `gates: 8/8 cheap, 2/2 heavy, 0 over-budget, 0 failed`.
- Main `npm run pack:dry-run`: produced `repo-audit-skills-0.5.20.tgz`, 351 files.

Convergence and fresh clone:

- Two W0 convergence runs passed before release-prep; both generated snapshot diffs were empty.
- Fresh-clone simulation passed with `npm ci` plus `npm run check`.

Push, CI, tag, and release:

- Pushed W0 implementation SHA `1c4d3e8`; CI run `27447811876`, job `81136613173`,
  passed in 4m51s.
- Pushed release SHA `7cb3831a6b9282b03cb69d1f54d244235b5179fc`; CI run
  `27448900504`, job `81139870949`, passed in 5m18s.
- Created annotated tag `v0.5.20`.
- Created GitHub release: `https://github.com/jc1122/repo-audit-skills/releases/tag/v0.5.20`.

Installed readback:

- Reinstalled all 16 repo-A skills through `node bin/install-repo-audit-skills.js --dest /home/jakub/.agents/skills --force`.
- Installed version readback: all 16 repo-A skills report `0.5.20`.
- Installed-vs-source parity passed after excluding generated local cache directories.
- Post-install bootstrap probes exited `0` for repo-A, repo-B, and repo-P using
  `/home/jakub/.agents/skills`; all three reported `restart_required=false` and
  `stop_before_discovery=false`.

Next anchor:

- repo-A hotspot anchor for the next installed wave is
  `7cb3831a6b9282b03cb69d1f54d244235b5179fc`.

## Iteration 2 W1/W2 execution and growth leaves (2026-06-13)

Scope:

- W1 `exec-audit` leaf added, registered, and gate-clean.
- W2 `growth-audit` leaf added, registered, and repo-A growth gate wired into
  the timed gate runner.
- Main fast-forwarded from `2e5199a` to `78a012d`.
- This is pre-W5 work; the finding universe is not frozen yet.

Worker runs:

| Packet | Run dir | Result |
| --- | --- | --- |
| W1 exec-audit core | `/tmp/sp12/runs/repo-a-w1-exec-audit-core` | accepted after output-contract follow-up |
| W2 growth-audit core | `/tmp/sp12/runs/repo-a-w2-growth-audit-core` | accepted after signal-contract follow-up |
| exec-audit metadata/helper | `/tmp/sp12/runs/repo-a-w12-exec-metadata` | accepted |
| growth-audit metadata/helper | `/tmp/sp12/runs/repo-a-w12-growth-metadata` | accepted |
| release/install registration | `/tmp/sp12/runs/repo-a-w12-release-installer-registration` | accepted |
| fixture/coverage registration | `/tmp/sp12/runs/repo-a-w12-fixture-coverage-registration` | blocked until coverage repaired |
| leaf coverage tests | `/tmp/sp12/runs/repo-a-w12-leaf-coverage-tests` | accepted |
| fixture/coverage finalize | `/tmp/sp12/runs/repo-a-w12-fixture-coverage-registration-finalize` | accepted |
| growth gate core | `/tmp/sp12/runs/repo-a-w12-growth-gate-core` | accepted |
| initial growth allowances | `/tmp/sp12/runs/repo-a-w12-growth-allowances` | accepted then corrected after committed deltas changed |
| allowance correction | `/tmp/sp12/runs/repo-a-w12-growth-allowances-fix` | accepted |
| run-checks growth wiring | `/tmp/sp12/runs/repo-a-w12-run-checks-growth` | committed but needed repair follow-ups |
| run-checks test repair | `/tmp/sp12/runs/repo-a-w12-run-checks-tests-fix` | accepted |
| exec-audit gate repair | `/tmp/sp12/runs/repo-a-w12-exec-audit-gates-fix` | accepted |
| growth-audit gate repair | `/tmp/sp12/runs/repo-a-w12-growth-audit-gates-fix` | accepted |
| final allowance correction | `/tmp/sp12/runs/repo-a-w12-growth-allowances-final` | accepted |

Accepted commits merged by fast-forward:

- `071a8b3` `feat(exec-audit): add execution audit core`.
- `c4f38fa` `fix(exec-audit): align leaf output contract`.
- `eedbcf7` `feat(growth-audit): add surface growth audit core`.
- `2d931b5` `fix(growth-audit): emit restructure signal for growth rows`.
- `38dc0e4` `chore(exec-audit): add skill metadata and vendored helper`.
- `07afcfb` `chore(growth-audit): add skill metadata and vendored helper`.
- `03bb240` `chore(skills): register exec and growth audits for release/install`.
- `f132595` `test(audit-leaves): cover exec and growth scripts in process`.
- `acfd530` `chore(skills): register exec and growth audits in fixtures and coverage`.
- `d4357f5` `feat(gates): add growth gate core`.
- `161bdca` `chore(gates): add SP12 growth allowances`.
- `7e230b8` `fix(gates): align growth allowances with committed surface`.
- `b3a6513` `feat(gates): wire growth gate into run checks`.
- `e68429b` `test(gates): update run-checks expectations for growth gate`.
- `f10afc4` `fix(exec-audit): satisfy docs security and selfaudit gates`.
- `b736634` `fix(growth-audit): satisfy selfaudit gates`.
- `78a012d` `fix(gates): refresh growth allowance after repairs`.

Issues found and fixed during W1/W2:

- `exec-audit` initially emitted `exec_findings.json` and leaf `exec`; fixed to
  `exec-audit_findings.json` and leaf `exec-audit`.
- `growth-audit` initially emitted signal `GROWTH`; fixed to the planned
  `RESTRUCTURE` signal.
- Both new leaves initially lacked `SKILL.md` and vendored helper copies;
  fixed with byte-identical `health_common.py` copies.
- Release, installer, fixture, and coverage registration were missing; all are
  now wired.
- Coverage registration exposed four new coverage findings for the new leaves
  and vendored helpers; in-process tests raised coverage enough for
  `check_coverage_gap.py` to pass with zero findings across 19 suites.
- `run_checks` root tests still expected the old 8 cheap gates; updated to the
  new 9-cheap-gate contract.
- `exec-audit` tripped docs, security, quality, complexity, and duplication
  gates; repaired without changing its output contract.
- `growth-audit` tripped quality, complexity, dead-code, and duplication gates;
  repaired without changing its output or `RESTRUCTURE` contract.
- Growth allowances required three recalibrations because each admitted gate or
  repair commit changed the final growth delta; final gate reports zero
  unsuppressed growth findings.

Verification:

- Integration branch `npm run check`: `gates: 9/9 cheap, 2/2 heavy, 0 over-budget, 0 failed`.
- Main after fast-forward `npm run check`: `gates: 9/9 cheap, 2/2 heavy, 0 over-budget, 0 failed`.
- Focused root tests after repair: `98 passed`.
- Focused exec-audit tests after repair: `100 passed`.
- Focused growth-audit tests after repair: `48 passed`.
- Growth gate after final allowance correction:
  `{"status": "pass", "count": 0, "baseline": "v0.5.20"}`.

Timing vs budget table from the post-merge main run:

| Gate | Seconds | Budget seconds |
| --- | ---: | ---: |
| vendored | 0.03 | 10 |
| hygiene | 0.14 | 10 |
| dependency | 0.15 | 10 |
| release | 0.23 | 10 |
| growth | 0.29 | 15 |
| docs | 0.69 | 10 |
| fixtures | 1.11 | 15 |
| security | 1.69 | 15 |
| selfaudit | 1.76 | 20 |
| coverage | 112.80 | 270 |
| pytest | 110.23 | 260 |

Growth allowance table:

| Metric | Max delta | Expiry | Reason |
| --- | ---: | --- | --- |
| tracked files | 11 | next release | SP12 W1/W2 exec-audit and growth-audit leaf admission plus gate integration |
| net LOC | 4379 | next release | SP12 W1/W2 implementation, tests, metadata, registrations, and repairs |
| docs LOC | 337 | next release | SP12 W1/W2 skill metadata and operator-facing descriptions |
| CLI flags | 15 | next release | SP12 W1/W2 leaf and gate CLI surfaces |
| dependencies | 0 | never | stdlib-only rule; positive dependency growth remains disallowed |

Current state after merge:

- repo-A `main` is ahead of `origin/main` by 17 commits.
- W1/W2 source work is accepted locally but not yet shipped/reinstalled.
- Next action: continue with W3/W4 or perform the next K-6 ship step when the
  plan reaches W5.
