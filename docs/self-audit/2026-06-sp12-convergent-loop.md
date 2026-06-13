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

## Iteration 2 W3/W4 repo-B wave and synthesis (2026-06-13)

Scope:

- W3 repo-B diagnosis wave is now registry-driven, parallel, and emits
  `wave_timings.json`.
- W3 added the expanded 8-lane registry, including `exec` and `growth`.
- W3 excluded timing telemetry from wave baseline comparison.
- W4 added advisory K-7 packet synthesis and mechanical patch proposal
  artifacts from wave findings.
- repo-B `main` fast-forwarded from `f6ace4b` to `dfc7545`.

Worker runs:

| Packet | Worktree | Run dir | Result |
| --- | --- | --- | --- |
| W3 wave core | `/tmp/sp12/repo-b-03-w3-wave-core` | `/tmp/sp12/runs/repo-b-w3-wave-core` | accepted after dirty-test follow-up |
| W3 wave core finalize | `/tmp/sp12/repo-b-03-w3-wave-core` | `/tmp/sp12/runs/repo-b-w3-wave-core-finalize` | accepted |
| W3 registry/baseline | `/tmp/sp12/repo-b-03-w3-wave-core` | `/tmp/sp12/runs/repo-b-w3-registry-baseline` | accepted after default-registry repair |
| W3 default registry repair | `/tmp/sp12/repo-b-03-w3-wave-core` | `/tmp/sp12/runs/repo-b-w3-default-registry-fix` | accepted |
| W4 synthesis | `/tmp/sp12/repo-b-03-w4-synthesis` | `/tmp/sp12/runs/repo-b-w4-synthesis` | accepted after repair |
| W4 synthesis repair | `/tmp/sp12/repo-b-03-w4-synthesis` | `/tmp/sp12/runs/repo-b-w4-synthesis-repair` | accepted |

Accepted repo-B commits merged by fast-forward:

- `1ed744a` `feat(wave): load lanes from registry and run in parallel`.
- `ee08223` `test(wave): align registry wave tests`.
- `29de3f6` `feat(wave): add lane registry and timing exclusion`.
- `7cf8a39` `fix(wave): use committed lane registry by default`.
- `0637bed` `feat(synthesis): packet and patch proposals from wave findings`.
- `dfc7545` `fix(synthesis): complete packet proposal edge cases`.

Issues found and fixed during W3/W4:

- W3 first pass left the repo-B wave-runner test file modified after commit;
  follow-up committed the intended test correction and left the worktree clean.
- W3 registry smoke initially required explicit `--registry`; repaired so the
  committed repo-B wave lane registry is the default lane source while explicit
  registries remain supported.
- W4 first pass left the repo-B packet-synthesis script modified and failed 8
  synthesis edge-case tests; repaired missing-value/threshold goal wording,
  non-dict and missing-id skips, result shape, signal fallback, and metric
  formatting.

Verification:

- repo-B W3 combined branch tests: `122 passed`.
- repo-B W4 repaired branch tests: `124 passed`.
- repo-B W3/W4 integration branch tests: `140 passed`.
- repo-B main after fast-forward tests: `140 passed`.
- Expanded smoke with repo-A source skills and no explicit registry:
  `exec` lane recognized with 1 finding, `growth` lane recognized with 2
  findings, and `wave_timings.json` written.

Timing artifact smoke:

| Lane | Seconds |
| --- | ---: |
| exec | 0.073 |
| growth | 0.084 |

Current state after W3/W4:

- repo-A `main` contains accepted W1/W2 and ledger entries; it is not pushed or
  released yet.
- repo-B `main` contains accepted W3/W4; it is ahead of `origin/main` by 6
  commits and is not pushed or released yet.
- repo-P remains untouched in SP12 so far.
- Next action: W5 ship repo-A and repo-B, reinstall changed skills, then run the
  expanded installed 8-lane wave on repo-A/repo-B/repo-P before the W5 freeze.

## Iteration 2 W5 ship, installed wave, and freeze boundary (2026-06-13)

Scope:

- Shipped repo-A with the W1 `exec-audit` and W2 `growth-audit` leaves plus the
  repo-A growth gate.
- Shipped repo-B with W3 registry-driven parallel waves and W4 packet/patch
  synthesis.
- Repaired one W5 wave-runner classification defect: the installed
  code-health lane returns exit 2 with parsed findings, which must be a
  findings status, not a wave error.
- Re-shipped repo-B as `v0.4.5` for that installed-behavior fix.
- Ran the expanded installed 8-lane wave on repo-A/repo-B/repo-P.
- Froze the W5 finding universe for repo-B and repo-P via their
  `check_wave_baseline.py` gates. Repo-A has no wave-baseline gate; its freeze
  inputs are this ledger plus the existing self-audit and growth gates.

Ship evidence:

| Repo | Head | Release | CI run | Result |
| --- | --- | --- | --- | --- |
| repo-A | `e099ce0` | `v0.5.21` | `27455580887` | success |
| repo-B | `2b2806f` | `v0.4.4` | `27455149106` | success |
| repo-B | `ebbafed` | `v0.4.5` | `27456126811` | success |
| repo-B freeze | `6373ac6` | no release, baseline-only | `27456374135` | success |
| repo-P freeze | `b35da00` | no release, baseline-only | `27456374180` | success |

Release/readback:

- repo-A release:
  https://github.com/jc1122/repo-audit-skills/releases/tag/v0.5.21
- repo-B releases:
  https://github.com/jc1122/repo-audit-refactor-optimize/releases/tag/v0.4.4
  and
  https://github.com/jc1122/repo-audit-refactor-optimize/releases/tag/v0.4.5
- Reinstalled repo-A leaves into `/home/jakub/.agents/skills`; installed-vs-
  source parity passed for all 18 repo-A skill directories.
- Reinstalled repo-B into `/home/jakub/.agents/skills/repo-audit-refactor-optimize`;
  installed-vs-source parity passed and installed `check_release.py` passed.
- Installed readback versions:
  - repo-A leaves: `0.5.21`.
  - repo-B orchestration skill: `0.4.5`.

Worker runs:

| Packet | Worktree | Run dir | Result |
| --- | --- | --- | --- |
| repo-A W5 release prep | `/tmp/sp12/repo-a-05-release` | `/tmp/sp12/runs/repo-a-w5-release-prep` | accepted |
| repo-A growth dependency false positive | `/tmp/sp12/repo-a-05-release` | `/tmp/sp12/runs/repo-a-w5-growth-dependency-fp` | accepted |
| repo-A current allowance refresh | `/tmp/sp12/repo-a-05-release` | `/tmp/sp12/runs/repo-a-w5-growth-current-allowance` | accepted |
| repo-A SIM114 repair | `/tmp/sp12/repo-a-05-release` | `/tmp/sp12/runs/repo-a-w5-growth-sim114` | accepted |
| repo-A allowance tighten | `/tmp/sp12/repo-a-05-release` | `/tmp/sp12/runs/repo-a-w5-growth-allowance-tighten` | accepted |
| repo-B W5 release prep | repo-B release worktree | `/tmp/sp12/runs/repo-b-w5-release-prep` | accepted |
| repo-B wave status fix | `/tmp/sp12/repo-b-05-wave-status-fix` | `/tmp/sp12/runs/repo-b-w5-wave-status-fix` | accepted |
| repo-B v0.4.5 release prep | `/tmp/sp12/repo-b-05-release-045` | `/tmp/sp12/runs/repo-b-w5-release-045` | accepted |
| repo-B W5 freeze baseline | `/tmp/sp12/repo-b-05-freeze-baseline` | `/tmp/sp12/runs/repo-b-w5-freeze-baseline` | accepted after follow-up |
| repo-B freeze-maintenance baseline follow-up | `/tmp/sp12/repo-b-05-freeze-baseline` | `/tmp/sp12/runs/repo-b-w5-freeze-baseline-followup` | accepted |
| repo-P W5 freeze baseline | `/tmp/sp12/repo-p-05-freeze-baseline` | `/tmp/sp12/runs/repo-p-w5-freeze-baseline` | accepted after follow-up |
| repo-P freeze-maintenance baseline follow-up | `/tmp/sp12/repo-p-05-freeze-baseline` | `/tmp/sp12/runs/repo-p-w5-freeze-baseline-followup` | accepted |

Issues found and fixed during W5:

- repo-A CI initially failed because GitHub Actions checkout did not fetch tags;
  `.github/workflows/check.yml` now uses `fetch-depth: 0`.
- That workflow fix added two net LOC after the exact growth allowance refresh;
  the repo-A growth allowance was updated and the next CI run passed.
- `growth-audit` initially counted package metadata as dependency growth; fixed
  so package self-metadata does not trigger dependency growth.
- `growth-audit` tripped one SIM114 self-audit finding; fixed without changing
  output contracts.
- repo-B wave runner treated code-health exit 2 with parsed findings as
  `error`; fixed and released in `v0.4.5`.
- Baseline freeze commits themselves created growth identities, and repo-B also
  created a hotspot identity on its wave baseline file; follow-up
  baseline commits included those freeze-maintenance identities so the live
  baseline gates pass.

Final installed W5 wave / gate counts:

| Repo | code-health | security | hygiene | docs | dependency | hotspot | exec | growth | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| repo-A installed wave | 18 | 0 | 0 | 0 | 0 | 206 | 0 | 0 | 224 |
| repo-B `check_wave_baseline.py` | 12 | 3 | 0 | 0 | 0 | 7 | 1 | 1 | 24 |
| repo-P `check_wave_baseline.py` | 24 | 0 | 0 | 0 | 0 | 7 | 0 | 1 | 32 |

Repo-A local gates after release:

- `python3 scripts/check_growth.py`:
  `{"status": "pass", "count": 0, "baseline": "v0.5.21"}`.
- `python3 scripts/check_self_audit.py`:
  `{"status": "pass", "count": 40, "baseline": 40}`.

Triage before freeze:

- Duplicate-execution findings are zero on repo-A and repo-P.
- repo-B has one surviving `exec-audit` row:
  `benchmark_entrypoints_missing`. It is advisory residue, not a trivially
  fixable duplicate-run regression.
- Growth rows that survived in repo-B/repo-P are freeze-maintenance
  `net_loc_growth` identities from the baseline commits themselves.
- No new lane/metric/class may be added after this point. The finding universe
  is CLOSED; K-1 is active. Hard cap: 14 iterations from the freeze boundary.
  New classes go to `SP13-CANDIDATES.md`.

Timing vs budget / wave timings:

| Repo/scope | Slowest lane or gate | Seconds | Notes |
| --- | --- | ---: | --- |
| repo-A installed W5 wave | code-health | 2.226 | final installed wave artifact: `/tmp/sp12/w5-wave-installed-final/repo-a` |
| repo-B installed W5 wave gate | code-health | 1.796 | final live baseline count `24/24` |
| repo-P installed W5 wave gate | code-health | 1.799 | final live baseline count `32/32` |
| repo-A release CI | check | 321 | GitHub Actions run `27455580887` |
| repo-B v0.4.5 CI | check | 13 | GitHub Actions run `27456126811` |
| repo-B freeze CI | check | completed success | GitHub Actions run `27456374135` |
| repo-P freeze CI | check | completed success | GitHub Actions run `27456374180` |

Current state after W5 freeze:

- repo-A `main` is at released `v0.5.21` and clean before this ledger append.
- repo-B `main` is pushed at `6373ac6`; baseline gate passes `24/24`.
- repo-P `main` is pushed at `b35da00`; baseline gate passes `32/32`.
- Next action: prune/re-justify repo-A growth allowances after the `v0.5.21`
  release and this ledger append, then start W6 iteration 3 C-0 diagnosis under
  the closed finding universe.
