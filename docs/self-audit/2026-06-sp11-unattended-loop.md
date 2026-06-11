# SP11 Unattended Dogfood Loop Ledger

Run plan: `docs/superpowers/plans/2026-06-11-sp11-unattended-dogfood-loop.md`

Mode: single Codex orchestrator, unattended, approvals disabled. Source of truth is
the frozen plan plus command/artifact evidence recorded here.

## Iteration 1

### Anchors and installed readback

- repo-A `/home/jakub/projects/repo-audit-skills`: `30d670a318e6109a3cf13fb9862e7bcb3ca40a71`
  (`docs(superpowers): compact SP11 launch key to <=3900 chars, plan-pointer style`).
  Version readback: `package.json` `0.5.1`; 16 source leaf `SKILL.md`
  files read `0.5.1`.
- repo-B `/home/jakub/projects/repo-audit-refactor-optimize`:
  `7c23276ad6fb72ec1c05d93f8992e20ddbc9d989`, tag `v0.4.1`.
- repo-P `/home/jakub/projects/perf-benchmark-skill`:
  `ac896751703cba56bbbd99e201c1f355c5238567`.
- Installed root: `/home/jakub/.claude/skills` resolves to
  `/home/jakub/.agents/skills`.
- Installed versions: 16 repo-audit leaves `0.5.1`;
  `repo-audit-refactor-optimize` `0.4.1`; `perf-benchmark` `0.3.0`;
  `perf-optimization` `0.2.0`.

### Entry verification

- repo-A entry gate: `npm run check` exited 0 before B0.1 edits.
  Counts: selfaudit `92/92`, security `49/49`, hygiene `0/0`,
  docs `0/0`, dependency `0/0`, coverage `0/0` across 17 suites.
- repo-B suite: `python3 -m pytest -q` -> `101 passed in 0.49s`.
- repo-P suite: `python3 -m pytest -q` -> `154 passed in 3.99s`.
- Bootstrap probes with installed `repo-audit-refactor-optimize`:
  repo-A and repo-B active lanes included bootstrap, test-python,
  code-health-python, coverage-python, security, performance, hygiene,
  orchestration; repo-P included bootstrap, code-health-python, security,
  performance, hygiene, orchestration. All three reported
  `restart_required=false` and `stop_before_discovery=false`.
- repo-B ratchet wave, installed runner and installed skills:
  `SKILLS_ROOT=/home/jakub/.agents/skills WAVE_RUNNER=/home/jakub/.agents/skills/repo-audit-refactor-optimize/scripts/run_diagnosis_wave.py python3 scripts/check_wave_baseline.py`
  exited 0 with `count=9`, `baseline=9`.
- repo-P ratchet wave, installed runner and installed skills:
  same command shape exited 0 with normalized `count=55`, `baseline=55`.
  Raw scoped wave artifact had 67 rows:
  20 cyclomatic complexity, 12 function nloc, 5 maintainability index,
  3 parameter count, 21 security, 6 hotspot.

### C-0 diagnosis artifacts

Artifact root: `artifacts/sp11/iteration-01/` (gitignored).

- Bootstrap artifacts:
  `bootstrap/repo-a`, `bootstrap/repo-b`, `bootstrap/repo-p`.
- Scoped installed waves:
  `c0-wave/repo-a-scoped`, `c0-wave/repo-b-scoped`,
  `c0-wave/repo-p-scoped`.
- repo-B scoped wave summary: 4 code-health rows + 5 hotspot rows = 9.
- repo-P scoped wave summary: 40 code-health rows + 21 security rows +
  6 hotspot rows = 67 raw, normalized by the repo-P ratchet to 55.
- repo-A scoped installed wave summary: 65 code-health rows, 49 security
  rows, 58 hotspot rows. The code-health wave missed the 27 duplication
  rows because the installed `duplication-audit` leaf looked for
  `node_modules/.bin/jscpd` under `/home/jakub/.agents/skills`, where no
  `node_modules` exists. The source self-audit gate remains authoritative
  for the repo-A baseline and reported 92 rows, including 27 duplication
  rows, using the source checkout where `node_modules/.bin/jscpd` exists.
  This installed-surface caveat must be considered by the next C-0 wave
  after repo-A is shipped/reinstalled.
- Unscoped exploratory waves were run first and intentionally not used as
  backlog evidence because they scanned ignored/generated repo contents.
  Gate-equivalent scoped waves above are the actionable C-0 evidence.

### B0.1 full-pytest aggregator gate

Reproduction command:

```bash
python3 -m pytest skills -q --color=no
```

Actual result differed from the plan's collection-error wording but matched
the same cross-suite module identity class:

- Exit 1.
- Summary: `9 failed, 636 passed in 113.79s`.
- Failure shape:
  - `helpers` imports resolved to
    `skills/test-redundancy-triage/tests/helpers.py`, breaking
    code-health and repo-hygiene tests that expected their own helpers.
  - `_reporting` resolved to the wrong already-imported module, breaking
    six security-audit tests with
    `AttributeError: module '_reporting' has no attribute 'load_thresholds'`.

Accepted implementation:

- Added `scripts/check_full_pytest.py`.
- Added npm script `check:pytest`.
- Appended `&& npm run check:pytest` to the `check` chain, making repo-A a
  10-gate repo.
- Added `scripts/full_pytest_snapshot.json` to `.gitignore`.
- Added `tests/test_check_full_pytest.py` so the new gate clears the
  coverage-gap ratchet.

Implementation notes:

- The first subprocess-based version added new security findings
  (`B404`, `B603`) on `scripts/check_full_pytest.py`, so it was replaced
  with a child-process implementation using `multiprocessing`.
- The first `spawn`/plain child version made the repo-level `tests` suite
  fail because the gate's `scripts/` directory remained first on
  `sys.path`. The final version normalizes each child to emulate
  `python -m pytest` from the suite parent before importing pytest.

Verification:

- `python3 -m pytest tests/test_check_full_pytest.py -q --color=no`
  -> `3 passed in 0.11s`.
- `python3 scripts/check_self_audit.py` -> `status=pass`, `count=92`,
  `baseline=92`.
- `python3 scripts/check_security_audit.py` -> `status=pass`, `count=49`,
  `baseline=49`.
- `python3 scripts/check_coverage_gap.py` -> `status=pass`, `count=0`,
  `baseline=0`, `suites=17`.
- `python3 scripts/check_full_pytest.py` -> `full-pytest: 17/17 suites green`.
- `npm run check` exited 0 with the new 10-gate chain; final gate output:
  `full-pytest: 17/17 suites green`.

Next required plan task: B0.2 opencode-worker-bridge smoke on DeepSeek v4 Pro Max.
