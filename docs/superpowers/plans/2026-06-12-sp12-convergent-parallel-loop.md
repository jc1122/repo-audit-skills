# SP12: Convergent Parallel Dogfood Loop — execution-domain sight, bounded growth, worker-only hands

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For the SP12 orchestrator:** this plan is the single authority for scope, contracts, and DoD. ONE orchestrator session runs UNATTENDED and NEVER edits source itself (K-3). All implementation happens in worker sessions inside dedicated git worktrees. The orchestrator's job is: dispatch packets, read evidence artifacts, re-run gates, merge green work, keep the ledger. A worker's green is NEVER evidence — the orchestrator re-runs every gate itself and reads real output.

**Goal:** give the repo-audit family eyes on the execution domain (its own slowness, redundant test execution, missing benchmarks) and a hard convergence guarantee (frozen finding universe, strict-shrink-or-terminal, surface budget), then run the recursive dogfood loop in parallel across repos with worker-only execution until every baseline is `[]` or each repo is honestly terminal.

**Architecture:** three layers. (1) Speed + telemetry: parallelize the two heavy repo-A gates and the repo-B wave, time every gate/lane, ratchet a runtime budget. (2) Two new repo-agnostic leaves — `exec-audit` (execution-config redundancy, junit runtimes, benchmark gaps) and `growth-audit` (surface growth vs a baseline rev) — wired into a registry-driven wave. (3) A convergent burn-down loop: one-time baseline freeze, then parallel per-repo worker iterations under a strict-shrink-or-terminal rule with a hard iteration cap.

**Tech Stack:** Python 3.11+ stdlib only for new leaves (family rule); pinned tools already in use (jscpd, bandit, lizard, radon, mutmut); git worktrees; opencode-worker-bridge / codex-cli-branch-workers / native subagents for workers.

---

## Repos and entry state (RE-VERIFY AT LAUNCH — SP11 is live and numbers advance)

- repo-A `/home/jakub/projects/repo-audit-skills` — v0.5.19 at SP11 terminal (iteration 18). 10 npm gates. Selfaudit baseline 40 rows; installed wave code-health 18, hotspot 204 (anchor-pinned). Read the actual baselines from `scripts/self_audit_baseline.json` and the SP11 ledger tail (`docs/self-audit/2026-06-sp11-unattended-loop.md`).
- repo-B `/home/jakub/projects/repo-audit-refactor-optimize` — v0.4.3, wave baseline 7 (3 code-health + 4 hotspot).
- repo-P `/home/jakub/projects/perf-benchmark-skill` — v0.3.8, wave baseline 31 (24 code-health + 7 hotspot).
- Installed root `~/.claude/skills` → `~/.agents/skills`; bootstrap probe must be green before starting.
- **Entry gate:** SP11 must be terminal (DONE or BLOCKED, ledger closed) before SP12 starts. Never run two loops against the same repos.

## Measured facts motivating this plan (verified 2026-06-12)

1. `npm run check` ≈ 5.3 min; `check:coverage` (153 s) + `check:pytest` (156 s) are 97 % of it. Both run the same 17 suites serially on an 8-core machine — the suite set is identical (compare `SUITES` in `scripts/check_coverage_gap.py:24-42` with `suite_dirs()` in `scripts/check_full_pytest.py:19-22`).
2. The wave runner (`repo-B scripts/run_diagnosis_wave.py:163`) runs its 6 lanes in a serial for-loop and records no durations, while repo-B's own `references/pipeline.md` says lanes should run concurrently.
3. `PERF` is a valid signal in `shared/health_common.py:30` but no leaf in repo-A emits it; perf-benchmark (repo-P) emits it only with an explicit `--target`/`--binary`.
4. `triage_redundancy.py:169` measures per-test `runtime_ms` and discards it.
5. SP11 iterations 12–17: repo-B and repo-P shipped nothing while paying full per-iteration ceremony; ~50 min/iteration was fixed cost for ≤2 accepted batches.
6. SP11 grew surface every iteration (9→10 gates, 3 suppression classes, 2 config files, 18 releases) with zero counter-pressure anywhere in the system.

## Design rules (apply to every task)

- **R1 repo-agnostic:** new leaves declare `languages: ["*"]`, read only universal artifacts (command graphs, CI text, junit XML, git history, wall-clock), and ship fixtures including one non-Python repo skeleton and one degenerate repo (no tests, no CI) that must produce exit 0 and zero spurious findings.
- **R2 admission:** any new skill/gate/config key must state in its SKILL.md (or gate docstring): the signal class it makes visible, why no existing leaf could host it, and its sunset criterion. This plan's own additions carry those statements.
- **R3 surface budget:** from the W2 growth gate onward, every repo-A commit that increases a growth metric needs an allowance entry with a reason (W2.4). The loop must end with the allowance file empty of expired entries.
- **R4 determinism vs timing:** timing artifacts are NEVER part of convergence comparison. Findings/identities/snapshots stay timing-free; durations live in separate gitignored artifacts (`check_timings.json`, `wave_timings.json`).

## Contracts (FROZEN)

- **K-0 recursion:** identical to SP11 C-0. Every iteration starts from the installed skillset: bootstrap probe, installed wave on each repo; wave findings are the backlog; ship → reinstall → next iteration diagnoses with the improved skill.
- **K-1 convergence guarantee:** after the W5 baseline freeze, the finding universe is CLOSED — no new finding classes, no new lanes, no new metrics may be added for the remainder of the run (write candidates to `docs/superpowers/SP13-CANDIDATES.md` instead). Baselines are shrink-only and equality-ratcheted. Each iteration, every ACTIVE repo must shrink its total open rows by ≥1; a repo with two consecutive zero-shrink iterations becomes TERMINAL (residue documented in the ledger; convergence-verification visits only). The loop ends when all repos are TERMINAL (DONE if baseline `[]`, else BLOCKED-with-residue). Hard cap: 14 iterations after the freeze. Because the row set is finite and frozen, and every non-terminal iteration strictly decreases it, termination is guaranteed.
- **K-2 surface budget:** the growth gate (W2) blocks unallowed growth of tracked-file count, net LOC, dependency count, CLI-flag count, and docs LOC relative to the last release tag. Allowances are counted, reasoned, and expire at the next release (re-justify or shrink). Pure deletions never need allowances.
- **K-3 worker-only execution + context conservation:** the orchestrator NEVER edits or reads source files. It consumes only: packet `status.json`, gate stdout tails (≤40 lines), findings/identities JSON, ledger text it writes. Code review = a read-only reviewer packet returning a verdict JSON. If the orchestrator catches itself about to open a source file, it dispatches a worker instead.
- **K-4 parallelism:** repos are visited CONCURRENTLY (disjoint trees, one writer per repo enforced by per-repo worktrees). Within a repo, ≤2 concurrent worker worktrees on disjoint file sets. Global cap: 4 concurrent worker sessions (post-W0 gate runs are ~90 s, so contention is bounded). CI watches are always overlapped with other work, never busy-waited.
- **K-5 batch discipline:** structural batches in throwaway worktrees (`git worktree add /tmp/sp12/<repo>-<slug>`), single-signal, ≤6 accepted batches per repo per iteration. Mutation gate inherited verbatim from SP11 C-3 (≥80 % scoped kill rate for behavior-changing batches, 30-min budget, golden-suite + byte-identical CLI output for mechanical moves). Discards recorded, never retried identically.
- **K-6 ship gate:** per changed repo at iteration end — all gates green → convergence ×2 (cheap post-W0) → fresh-clone sim → push → CI watch → bump+tag+release **only when leaf behavior changed** (refactor-only/docs-only iterations push without releasing; the reinstall is skipped because the installed diagnosis cannot differ) → reinstall when released → readback + bootstrap probe → hotspot re-anchor. One bounded fix-forward on CI red; second red on the same repo = that repo TERMINAL(BLOCKED).
- **K-7 worker packets:** file-backed only, one goal, ≤2 files, full content inlined ≤200 lines else grep-anchored excerpts, failing test included, exact run command + expected output, ≤8k tokens, TDD. Routes: opencode-worker-bridge primary; codex-cli-branch-workers or native subagents on infrastructure failure (one-way, logged). Reviewer packets are read-only and return `{verdict: approve|reject, reasons[]}`.
- **K-8 termination:** DONE = DoD met. BLOCKED = K-1 cap/zero-shrink fired, or second CI red, or any gate impossible without violating K-0..K-7. Both are valid; both require complete ledger + final report. Never game thresholds; never suppress real findings silently.
- **K-9 ledger:** `docs/self-audit/2026-06-sp12-convergent-loop.md` in repo-A, appended once per iteration: installed versions, per-repo row counts before/after, batches accepted/discarded with worktree paths, worker run dirs, timings vs budget, ship evidence, growth-allowance table.

## Definition of Done (falsifiable)

1. repo-A: `npm run check` green in ≤150 s wall-clock on the reference machine (timed by `check_timings.json`; per-gate budgets in `check_budget.json` are the binding limits); all baselines `[]` or repo TERMINAL with documented residue; fresh-clone sim green; CI green, zero deprecation annotations; final release tagged.
2. repo-B: wave registry-driven and parallel; `wave_timings.json` emitted; wave baseline `[]` or TERMINAL; suite green; CI green.
3. repo-P: wave baseline `[]` or TERMINAL; suite green; CI green.
4. `exec-audit` and `growth-audit` installed, registered in fixtures/release/installer/coverage gates, each with the R1 fixture pair (non-Python + degenerate) passing, and each present as a wave lane.
5. The growth gate is live in repo-A with an empty (or fully reasoned, unexpired) allowance file.
6. Patch-proposal artifacts: `synthesize_packets.py` emits ≥1 packet JSON and ≥1 `.patch` proposal from a real wave findings file, covered by tests.
7. Ledger complete per K-9; every iteration recorded; suppression/allowance counts reconciled.

---

## Work package W0 — repo-A gate speed + timing budget (iteration 1, lands FIRST: it cheapens everything after)

### Task W0.1: parallelize the full-pytest gate

**Files:**
- Modify: `scripts/check_full_pytest.py` (full rewrite below)
- Test: `tests/test_check_full_pytest.py` (extend)

- [ ] **Step 1: Read the existing test** `tests/test_check_full_pytest.py` to preserve its contract (snapshot schema `[{suite, returncode, tail}]`, exit 1 on any failed suite).
- [ ] **Step 2: Write the failing test for parallel determinism** — append to `tests/test_check_full_pytest.py`:

```python
def test_snapshot_order_is_sorted_not_completion_order(tmp_path, monkeypatch):
    """Results must be ordered by suite path so reruns are byte-identical."""
    import scripts.check_full_pytest as gate

    recorded = [
        {"suite": "skills/b/tests", "returncode": 0, "tail": ["1 passed"]},
        {"suite": "skills/a/tests", "returncode": 0, "tail": ["1 passed"]},
    ]
    ordered = gate.sort_results(recorded)
    assert [r["suite"] for r in ordered] == ["skills/a/tests", "skills/b/tests"]
```

- [ ] **Step 3: Run it to verify it fails.** `python3 -m pytest tests/test_check_full_pytest.py -q` → FAIL (`sort_results` not defined).
- [ ] **Step 4: Replace `scripts/check_full_pytest.py` with the parallel implementation:**

```python
#!/usr/bin/env python3
"""Gate: run every pytest suite in isolation, in parallel; aggregate results.

Suites are independent by family design (each runs with its own rootdir).
Results are sorted by suite path so the snapshot is byte-identical across
reruns regardless of completion order (R4 / C-5 convergence).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "scripts" / "full_pytest_snapshot.json"
WORKERS = max(2, (os.cpu_count() or 2) - 1)


def suite_dirs() -> list[Path]:
    dirs = [ROOT / "tests"] if (ROOT / "tests").is_dir() else []
    dirs += sorted(path for path in ROOT.glob("skills/*/tests") if path.is_dir())
    return dirs


def run_suite(suite: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(suite), "-q", "--color=no",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=suite.parent, check=False,
    )
    tail = (proc.stdout.strip().splitlines()[-1:]
            or proc.stderr.strip().splitlines()[-1:])
    return {
        "suite": str(suite.relative_to(ROOT)),
        "returncode": proc.returncode,
        "tail": tail,
    }


def sort_results(results: list[dict]) -> list[dict]:
    return sorted(results, key=lambda r: r["suite"])


def main() -> int:
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = sort_results(list(pool.map(run_suite, suite_dirs())))
    SNAPSHOT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failed = [r for r in results if r["returncode"] != 0]
    print(f"full-pytest: {len(results) - len(failed)}/{len(results)} suites green")
    for r in failed:
        print(f"FAIL {r['suite']}: {r['tail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the focused test, then the gate twice.** `python3 -m pytest tests/test_check_full_pytest.py -q` → PASS. Then `time python3 scripts/check_full_pytest.py` twice → both `17/17 suites green`, wall time ≤60 s, and `diff <(run1 snapshot) <(run2 snapshot)` empty.
- [ ] **Step 6: Commit** `perf(gates): parallelize full-pytest gate across suites`.

### Task W0.2: parallelize the coverage gate

**Files:**
- Modify: `scripts/check_coverage_gap.py:54-101` (replace `run_suites_with_coverage`)
- Test: `tests/test_check_coverage_gap.py` (extend)

- [ ] **Step 1: Write the failing test** — append to `tests/test_check_coverage_gap.py`:

```python
def test_per_suite_coverage_files_are_combined(tmp_path, monkeypatch):
    """Each suite gets its own COVERAGE_FILE; combine produces one report."""
    import scripts.check_coverage_gap as gate

    env = gate.suite_env(out_dir=tmp_path, suite="skills/quality-audit/tests")
    assert env["COVERAGE_FILE"].endswith(".coverage.skills_quality-audit_tests")
```

- [ ] **Step 2: Run it to verify it fails** (`suite_env` not defined).
- [ ] **Step 3: Replace `run_suites_with_coverage` and add `suite_env`:**

```python
def suite_env(out_dir: Path, suite: str) -> dict[str, str]:
    slug = suite.replace("/", "_")
    return dict(os.environ, COVERAGE_FILE=str(out_dir / f".coverage.{slug}"))


def _run_one_suite(suite: str) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", suite, "-q", "-p", "no:cacheprovider",
         "--cov", "--cov-report=", f"--cov-config={RCFILE}"],
        cwd=ROOT, env=suite_env(OUT, suite), text=True,
        capture_output=True, timeout=SUITE_TIMEOUT, check=False,
    )
    return suite, proc.returncode


def run_suites_with_coverage() -> tuple[Path, dict[str, int]]:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob(".coverage*"):
        stale.unlink()
    from concurrent.futures import ThreadPoolExecutor

    workers = max(2, (os.cpu_count() or 2) - 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(_run_one_suite, SUITES))
    env = dict(os.environ, COVERAGE_FILE=str(OUT / ".coverage"))
    subprocess.run(
        [sys.executable, "-m", "coverage", "combine", "--keep",
         *sorted(str(p) for p in OUT.glob(".coverage.*"))],
        cwd=ROOT, env=env, text=True, capture_output=True,
        timeout=120, check=False,
    )
    coverage_json = OUT / "coverage.json"
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", str(coverage_json),
         f"--rcfile={RCFILE}"],
        cwd=ROOT, env=env, text=True, capture_output=True,
        timeout=120, check=False,
    )
    return coverage_json, results
```

(`.coveragerc` already sets `relative_files = True`, so per-suite data files combine cleanly.)

- [ ] **Step 4: Verify equivalence, not just green.** Run `python3 scripts/check_coverage_gap.py` → exit 0, then `diff scripts/coverage_gap_snapshot.json` against the pre-change snapshot (regenerate the old one from `git stash` if needed) → identical finding set.
- [ ] **Step 5: Run the root suite.** `python3 -m pytest tests -q` → all green. Wall time of the gate ≤60 s.
- [ ] **Step 6: Commit** `perf(gates): parallelize coverage suites with per-suite data files`.

### Task W0.3: timed gate runner with runtime budget (gate telemetry — the family seeing its own slowness)

**Files:**
- Create: `scripts/run_checks.py`
- Create: `scripts/check_budget.json`
- Modify: `package.json:11` (`"check": "python3 scripts/run_checks.py"` — keep all `check:*` aliases)
- Modify: `.gitignore` (add `scripts/check_timings.json`)
- Test: `tests/test_run_checks.py` (new)

Admission note (R2): signal = "gate wall-clock regression"; no existing leaf can host it because gates are repo-A process, not target-repo source; sunset = if gates merge into a single tool, the budget moves there.

- [ ] **Step 1: Write the failing tests** — `tests/test_run_checks.py`:

```python
import json
import scripts.run_checks as rc


def test_budget_violation_fails_gate(tmp_path):
    budget = {"selfaudit": 0.000001}
    timings = {"selfaudit": 1.5}
    violations = rc.budget_violations(timings, budget)
    assert violations == [("selfaudit", 1.5, 0.000001)]


def test_within_budget_passes():
    assert rc.budget_violations({"selfaudit": 1.0}, {"selfaudit": 30}) == []


def test_missing_budget_entry_is_a_violation():
    # Every gate must have a budget row: silence is not allowed.
    assert rc.budget_violations({"newgate": 1.0}, {}) == [("newgate", 1.0, None)]
```

- [ ] **Step 2: Run to verify failure** (`scripts.run_checks` missing).
- [ ] **Step 3: Implement `scripts/run_checks.py`:**

```python
#!/usr/bin/env python3
"""Run all repo-A gates with wall-clock telemetry and a runtime budget.

Phase 1 runs the cheap gates in parallel; phase 2/3 run the two heavy
suite-running gates one after the other (each is internally parallel).
Timings go to scripts/check_timings.json (gitignored, never part of
convergence comparison — R4). A gate exceeding its budget FAILS the run:
slowness is a defect, not a log line.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMINGS = ROOT / "scripts" / "check_timings.json"
BUDGET = ROOT / "scripts" / "check_budget.json"

CHEAP = [
    ("vendored", "scripts/check_vendored_common.py"),
    ("fixtures", "scripts/check_skill_fixtures.py"),
    ("release", "scripts/check_release.py"),
    ("selfaudit", "scripts/check_self_audit.py"),
    ("security", "scripts/check_security_audit.py"),
    ("hygiene", "scripts/check_repo_hygiene.py"),
    ("docs", "scripts/check_docs_consistency.py"),
    ("dependency", "scripts/check_dependency_audit.py"),
]
HEAVY = [
    ("coverage", "scripts/check_coverage_gap.py"),
    ("pytest", "scripts/check_full_pytest.py"),
]


def run_gate(name: str, script: str) -> tuple[str, int, float, str]:
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    elapsed = time.monotonic() - start
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return name, proc.returncode, elapsed, tail


def budget_violations(
    timings: dict[str, float], budget: dict[str, float]
) -> list[tuple[str, float, float | None]]:
    out: list[tuple[str, float, float | None]] = []
    for name, took in sorted(timings.items()):
        limit = budget.get(name)
        if limit is None or took > limit:
            out.append((name, took, limit))
    return out


def main() -> int:
    results: list[tuple[str, int, float, str]] = []
    with ThreadPoolExecutor(max_workers=len(CHEAP)) as pool:
        results.extend(pool.map(lambda g: run_gate(*g), CHEAP))
    for gate in HEAVY:
        results.append(run_gate(*gate))

    timings = {name: round(took, 2) for name, _, took, _ in results}
    TIMINGS.write_text(json.dumps(timings, indent=2, sort_keys=True) + "\n")
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))

    failed = [(n, rc, tail) for n, rc, _, tail in results if rc != 0]
    over = budget_violations(timings, budget)
    for name, rc_, tail in failed:
        print(f"FAIL {name} (exit {rc_}):\n{tail}")
    for name, took, limit in over:
        print(f"OVER-BUDGET {name}: {took}s > {limit}s")
    ordered = sorted(results, key=lambda r: r[0])
    print(
        "gates: "
        + " ".join(f"{n}={'ok' if rc_ == 0 else 'FAIL'}" for n, rc_, _, _ in ordered)
    )
    return 1 if failed or over else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create `scripts/check_budget.json`** with honest post-W0.1/W0.2 headroom (measure first, then set ≈ 2× measured):

```json
{
  "vendored": 10,
  "fixtures": 15,
  "release": 10,
  "selfaudit": 20,
  "security": 15,
  "hygiene": 10,
  "docs": 10,
  "dependency": 10,
  "coverage": 120,
  "pytest": 120
}
```

- [ ] **Step 5: Wire npm + gitignore.** `package.json` `"check"` → `"python3 scripts/run_checks.py"`; add `scripts/check_timings.json` to `.gitignore` next to the other snapshots.
- [ ] **Step 6: Verify.** `python3 -m pytest tests/test_run_checks.py -q` → PASS. `time npm run check` → all gates ok, wall ≤120 s. Grep the output for `gates:` line listing 10 `ok`.
- [ ] **Step 7: Commit** `feat(gates): timed parallel gate runner with runtime budget`.

### Task W0.4: ship W0 (K-6; behavior changed → release + reinstall)

- [ ] Convergence ×2 (`npm run check` twice, identical pass counts; snapshots diff empty), fresh-clone sim (`git clone . /tmp/sp12-fc && cd /tmp/sp12-fc && npm ci && npm run check` → green), push, CI watch, bump + tag + release per repo-A ritual (package.json + all SKILL.mds + check_release + installer + CHANGELOG), reinstall, readback. Record wall-clock for one full ship in the ledger — this is the new fixed-cost baseline.

## Work package W1 — `exec-audit` leaf (NEW, `languages: ["*"]`) — execution-domain sight on any repo

Admission note (R2): signal = duplicate/serial/slow execution and benchmark absence; no existing leaf reads execution configs or junit XML; sunset = if a language-native build-graph analyzer leaf supersedes it, fold detectors there and purge.

**Files (whole package):**
- Create: `skills/exec-audit/SKILL.md`, `skills/exec-audit/scripts/exec_audit.py`, `skills/exec-audit/scripts/health_common.py` (byte-copy of `shared/health_common.py`)
- Create: `skills/exec-audit/tests/{conftest.py,test_npm_redundancy.py,test_workflows.py,test_junit.py,test_degenerate.py}` + `skills/exec-audit/tests/fixtures/{npm-dup,node-skeleton,degenerate}/…`
- Modify: `scripts/check_skill_fixtures.py` (HELP_COMMANDS + exec-audit row), `scripts/check_release.py` (REQUIRED_SKILLS/REQUIRED_SCRIPTS), `bin/install-repo-audit-skills.js` (leaf list), `scripts/check_coverage_gap.py` (SUITES + `skills/exec-audit/tests`)

### Task W1.1: detectors — RED

- [ ] **Step 1: Fixtures.** `tests/fixtures/npm-dup/package.json`:

```json
{
  "scripts": {
    "check": "npm run check:cov && npm run check:plain",
    "check:cov": "pytest tests --cov --cov-report=",
    "check:plain": "pytest tests -q"
  }
}
```

`tests/fixtures/node-skeleton/package.json` (non-Python repo, R1):

```json
{
  "scripts": {
    "test": "jest --coverage",
    "lint": "eslint ."
  }
}
```

`tests/fixtures/degenerate/` contains a single `README.md` ("empty repo").

- [ ] **Step 2: Failing tests.** `tests/test_npm_redundancy.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "exec_audit.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_leaf(root: Path, out: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root),
         "--out-dir", str(out), *extra],
        text=True, capture_output=True, check=False,
    )


def findings(out: Path) -> list[dict]:
    return json.loads((out / "exec-audit_findings.json").read_text())


def test_duplicate_test_invocation_detected(tmp_path):
    proc = run_leaf(FIXTURES / "npm-dup", tmp_path)
    assert proc.returncode == 1
    rows = [f for f in findings(tmp_path)
            if f["metric"]["name"] == "duplicate_execution"]
    assert len(rows) == 1
    assert rows[0]["signal"] == "PERF"
    assert "tests" in rows[0]["evidence"]["raw"]


def test_node_skeleton_no_false_positive(tmp_path):
    proc = run_leaf(FIXTURES / "node-skeleton", tmp_path)
    dup = [f for f in findings(tmp_path)
           if f["metric"]["name"] == "duplicate_execution"]
    assert dup == []
```

`tests/test_degenerate.py`:

```python
def test_degenerate_repo_exits_clean(tmp_path):
    proc = run_leaf(FIXTURES / "degenerate", tmp_path)
    assert proc.returncode in (0, 1)  # benchmark-gap info row is allowed
    rows = findings(tmp_path)
    assert all(f["metric"]["name"] == "benchmark_entrypoints_missing"
               for f in rows)
```

`tests/test_junit.py` (fixture `tests/fixtures/junit/report.xml` with one testcase `time="9.0"`, one `time="0.1"`):

```python
def test_slow_test_from_junit(tmp_path):
    proc = run_leaf(FIXTURES / "junit", tmp_path,
                    "--junit-xml", str(FIXTURES / "junit" / "report.xml"))
    rows = [f for f in findings(tmp_path) if f["metric"]["name"] == "slow_test"]
    assert len(rows) == 1 and rows[0]["metric"]["value"] == 9.0
```

- [ ] **Step 3: Run** `python3 -m pytest skills/exec-audit/tests -q` → FAIL (script missing).

### Task W1.2: detectors — GREEN

- [ ] **Step 1: Implement `skills/exec-audit/scripts/exec_audit.py`.** Family CLI (`--root`, `--out-dir`, `--format json|md`, `--config` JSON thresholds, `--junit-xml` repeatable). Core detectors (complete logic — keep functions ≤40 nloc to stay under the family's own selfaudit thresholds):

```python
#!/usr/bin/env python3
"""exec-audit: deterministic, advisory execution-efficiency audit.

Reads execution configs (package.json scripts, GitHub workflow run lines),
optional junit XML, and benchmark-entrypoint markers. Emits shared-schema
PERF findings. languages: ["*"] — no source parsing, no execution, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from health_common import EXIT_CLEAN, EXIT_ERROR, EXIT_FINDINGS, Finding, write_findings

LEAF = "exec-audit"
DEFAULTS = {"slow_test_seconds": 5.0, "serial_chain_min": 4}
RUNNERS = ("pytest", "jest", "mocha", "go test", "cargo test", "npm test")


def split_chain(command: str) -> list[str]:
    return [seg.strip() for seg in re.split(r"&&|;", command) if seg.strip()]


def expand_npm(scripts: dict[str, str], name: str, seen: frozenset[str] = frozenset()) -> list[str]:
    if name in seen or name not in scripts:
        return []
    segments: list[str] = []
    for seg in split_chain(scripts[name]):
        match = re.match(r"npm run ([\w:.-]+)", seg)
        if match:
            segments += expand_npm(scripts, match.group(1), seen | {name})
        else:
            segments.append(seg)
    return segments


def normalize(segment: str, root: Path) -> tuple[str, ...] | None:
    """(runner, path, path...) for test-runner segments; None otherwise."""
    tokens = segment.split()
    runner = next((r for r in RUNNERS if segment.startswith(r) or
                   f" {r} " in f" {segment} "), None)
    if runner is None:
        return None
    paths = tuple(sorted(t for t in tokens
                         if not t.startswith("-") and (root / t).exists()))
    return (runner, *paths)


def duplicate_execution_findings(root: Path) -> list[Finding]:
    pkg = root / "package.json"
    if not pkg.exists():
        return []
    try:
        scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
    except (json.JSONDecodeError, OSError):
        return []
    out: list[Finding] = []
    for name in scripts:
        keys: dict[tuple[str, ...], int] = {}
        for seg in expand_npm(scripts, name):
            key = normalize(seg, root)
            if key:
                keys[key] = keys.get(key, 0) + 1
        for key, count in sorted(keys.items()):
            if count > 1:
                out.append(Finding(
                    LEAF, "PERF", "medium", "package.json", 1, 1,
                    f"scripts.{name}", "duplicate_execution", float(count), 1.0,
                    "exec-audit", f"{' '.join(key)} runs {count}x in chain",
                    "medium",
                    "run the suite once and reuse its results across gates",
                ))
    return out
```

Workflow detector: extract `run:` lines (single-line and `run: |` blocks) per job from `.github/workflows/*.yml` with the same `normalize`/duplicate logic per job (path `".github/workflows/<file>"`, symbol = job id). Junit detector: parse each `--junit-xml` file with `ET.parse`; for each `testcase` with `time > slow_test_seconds` emit `slow_test` (value = time, threshold = config, symbol = `classname.name`, capped at the 20 slowest). Benchmark-gap detector: if none of (`pytest-benchmark` in any `requirements*.txt`/`pyproject.toml`, a `benchmarks/` or `benches/` dir, a package.json script name containing `bench`) exists → one `benchmark_entrypoints_missing` info finding (path ".", confidence low). `main()` mirrors hotspot-audit's main (`--format json|md`, exit 0/1/2 via EXIT_* constants, `write_findings(...)`).

- [ ] **Step 2: Run the leaf suite** → all green. Run against repo-A at the pre-W0 commit (`git worktree add /tmp/exec-proof <pre-W0-sha>` then `python3 skills/exec-audit/scripts/exec_audit.py --root /tmp/exec-proof --out-dir /tmp/exec-proof-out`) → MUST report `duplicate_execution` on the old check chain. This proves the leaf would have caught SP11's blind spot. Record in ledger; remove the worktree.
- [ ] **Step 3: SKILL.md** with name `exec-audit`, version = current package version, R2 admission statement, Limits section (Makefile/tox parsing deferred to SP13; yaml extraction is line-based best-effort).
- [ ] **Step 4: Register everywhere.** Add to `scripts/check_skill_fixtures.py` HELP_COMMANDS, `scripts/check_release.py` REQUIRED_SKILLS (`"exec-audit": "exec-audit"`) + REQUIRED_SCRIPTS (`["scripts/exec_audit.py"]`), installer leaf list in `bin/install-repo-audit-skills.js`, coverage SUITES (`"skills/exec-audit/tests"`). Vendored copy is picked up by `check_vendored_common.py` automatically.
- [ ] **Step 5: Full gates.** `npm run check` → green (coverage baseline stays `[]`: the new scripts must be covered by the new tests in this same batch).
- [ ] **Step 6: Commit** `feat(exec-audit): execution-efficiency leaf (duplicate runs, junit slowness, benchmark gaps)`.

## Work package W2 — `growth-audit` leaf (NEW, `languages: ["*"]`) + repo-A growth gate — the convergence guard

Admission note (R2): signal = unjustified surface growth; hotspot-audit mines history for *risk concentration*, not growth, and its decision classes differ (BLOAT/DELETE vs DECOMPOSE); sunset = if hotspot-audit grows a trend engine, merge and purge.

**Files (whole package):**
- Create: `skills/growth-audit/SKILL.md`, `skills/growth-audit/scripts/growth_audit.py`, `skills/growth-audit/scripts/health_common.py` (byte-copy)
- Create: `skills/growth-audit/tests/{conftest.py,test_growth_metrics.py,test_allowances.py}` (+ synthetic git-repo fixtures built in `tmp_path` like hotspot-audit's tests)
- Create: `scripts/check_growth.py`, `scripts/growth_allowances.json`
- Modify: same four registration files as W1.2 step 4, plus `scripts/run_checks.py` CHEAP list (add `("growth", "scripts/check_growth.py")`) and `scripts/check_budget.json` (add `"growth": 15`)

### Task W2.1: metrics — RED

- [ ] **Step 1: Failing tests** — `skills/growth-audit/tests/test_growth_metrics.py` (fixture helper creates a git repo in `tmp_path`, commits base state, tags `base`, adds a file + a dependency line, commits):

```python
def test_loc_and_file_growth_detected(synthetic_repo, tmp_path):
    # synthetic_repo: base commit tagged 'base'; HEAD adds new_module.py (+30 loc)
    proc = run_leaf(synthetic_repo, tmp_path, "--baseline-rev", "base")
    assert proc.returncode == 1
    names = {f["metric"]["name"] for f in findings(tmp_path)}
    assert {"tracked_files_growth", "net_loc_growth"} <= names


def test_pure_deletion_is_clean(synthetic_repo_deletion, tmp_path):
    proc = run_leaf(synthetic_repo_deletion, tmp_path, "--baseline-rev", "base")
    assert proc.returncode == 0
    assert findings(tmp_path) == []
```

`test_allowances.py` (C-1 both directions):

```python
def test_allowed_growth_is_suppressed_and_counted(synthetic_repo, tmp_path):
    config = tmp_path / "cfg.json"
    config.write_text(json.dumps({"allow_growth": [
        {"metric": "tracked_files_growth", "max_delta": 5,
         "reason": "W1 exec-audit leaf admission"}]}))
    proc = run_leaf(synthetic_repo, tmp_path, "--baseline-rev", "base",
                    "--config", str(config))
    rows = findings(tmp_path)
    assert "tracked_files_growth" not in {f["metric"]["name"] for f in rows}
    summary = json.loads((tmp_path / "growth-audit_summary.json").read_text())
    assert summary["suppressed"][0]["metric"] == "tracked_files_growth"


def test_growth_beyond_allowance_still_fires(synthetic_repo_big, tmp_path):
    config = tmp_path / "cfg.json"
    config.write_text(json.dumps({"allow_growth": [
        {"metric": "net_loc_growth", "max_delta": 1, "reason": "tiny"}]}))
    proc = run_leaf(synthetic_repo_big, tmp_path, "--baseline-rev", "base",
                    "--config", str(config))
    assert "net_loc_growth" in {f["metric"]["name"] for f in findings(tmp_path)}
```

- [ ] **Step 2: Run** → FAIL (script missing).

### Task W2.2: metrics — GREEN

- [ ] **Step 1: Implement `growth_audit.py`.** CLI: `--root`, `--out-dir`, `--baseline-rev` (required), `--format`, `--config`. Metrics, all via git so they are language-blind:

```python
METRICS = {
    "tracked_files_growth": lambda r, b: _count_delta(
        r, b, ["git", "ls-tree", "-r", "--name-only"]),
    "net_loc_growth": lambda r, b: _shortstat_net(r, b, pathspec=None),
    "docs_loc_growth": lambda r, b: _shortstat_net(r, b, pathspec="*.md"),
    "dependency_growth": lambda r, b: _dependency_delta(r, b),
    "cli_flag_growth": lambda r, b: _grep_count_delta(
        r, b, "add_argument(", "*.py"),
}
```

`_shortstat_net` parses `git diff --shortstat <base>..HEAD [-- <pathspec>]` → insertions − deletions. `_dependency_delta` reads `requirements*.txt` line counts, `pyproject.toml` `[project] dependencies` entries, and `package.json` dependencies+devDependencies key counts at both revs via `git show rev:path` (missing file → 0). `_grep_count_delta` sums `git grep -c <needle> <rev> -- <glob>` (zero matches → 0; the metric reads 0 on non-Python repos, which is correct, not an error). Positive delta beyond its allowance → `RESTRUCTURE` finding, severity medium, evidence `"<base_value> -> <head_value> (+<delta>)"`, suggested action `"shrink the surface or record a reasoned allowance"`. Suppressed rows are counted in `growth-audit_summary.json` under `suppressed` with metric/reason — same counted-suppression discipline as SP11's trusted-subprocess class.
- [ ] **Step 2: Leaf suite green.** Include conftest fixtures that build the synthetic git repos (init, config user, commit, tag — mirror `skills/hotspot-audit/tests/conftest.py` patterns).
- [ ] **Step 3: SKILL.md** (name `growth-audit`, R2 statement, Limits: dead-flag detection deferred to SP13; `cli_flag_growth` is Python-grep best-effort and reads 0 elsewhere).
- [ ] **Step 4: Register** in fixtures/release/installer/coverage gates (same four files as W1.2 step 4).
- [ ] **Step 5: Commit** `feat(growth-audit): surface-growth leaf with reasoned allowances`.

### Task W2.3: repo-A growth gate

- [ ] **Step 1: Failing test** — `tests/test_check_growth.py`:

```python
def test_gate_uses_last_release_tag(monkeypatch):
    import scripts.check_growth as cg
    assert cg.baseline_rev().startswith("v")  # repo-A always has release tags
```

- [ ] **Step 2: Implement `scripts/check_growth.py`:** `baseline_rev()` = `git describe --tags --abbrev=0`; invoke the leaf with `--baseline-rev <tag> --config scripts/growth_allowances.json`; exit nonzero iff the leaf exits 1 with any unsuppressed finding (grep the findings JSON, never trust the pipe — SP11 binding lesson). Initialize `scripts/growth_allowances.json` with reasoned entries for W0–W2's own additions (this plan grows surface; it justifies itself):

```json
{
  "allow_growth": [
    {"metric": "tracked_files_growth", "max_delta": 40,
     "reason": "SP12 W0-W2: exec-audit + growth-audit leaves and gate runner",
     "expires": "next-release"},
    {"metric": "net_loc_growth", "max_delta": 2500,
     "reason": "SP12 W0-W2 admission per plan R2",
     "expires": "next-release"},
    {"metric": "dependency_growth", "max_delta": 0,
     "reason": "stdlib-only rule, growth never allowed", "expires": "never"}
  ]
}
```

- [ ] **Step 3: Wire into `run_checks.py` CHEAP list + budget (`"growth": 15`).** Run `npm run check` → 11 gates ok.
- [ ] **Step 4: Commit** `feat(gates): growth gate with reasoned allowances (convergence guard)`.

### Task W2.4: allowance expiry rule (K-2)

- [ ] At every K-6 release, the orchestrator dispatches a worker to: re-baseline (the new tag becomes the baseline rev, so deltas reset), delete `"expires": "next-release"` entries, and re-justify or shrink anything still growing. Gate must be green with the pruned file before the tag is pushed. Add this as a labeled step in the ship checklist in the ledger template.

## Work package W3 — repo-B wave: registry-driven, parallel, timed, with the new lanes

**Files:**
- Create: `repo-B scripts/wave_lanes.json`
- Modify: `repo-B scripts/run_diagnosis_wave.py` (LANES table → registry; serial loop → pool; timings artifact)
- Test: `repo-B tests/test_run_diagnosis_wave.py` (extend — find the existing wave tests with `grep -rl run_diagnosis_wave repo-B/tests`)

### Task W3.1: lane registry — RED then GREEN

- [ ] **Step 1: Failing test:**

```python
def test_lanes_load_from_registry(tmp_path):
    import scripts.run_diagnosis_wave as wave
    registry = tmp_path / "wave_lanes.json"
    registry.write_text(json.dumps({"lanes": [
        {"name": "hygiene",
         "script": "repo-hygiene-audit/scripts/repo_hygiene_audit.py",
         "languages": ["*"]}]}))
    lanes = wave.load_lanes(registry)
    assert list(lanes) == ["hygiene"]
    assert lanes["hygiene"].endswith("repo_hygiene_audit.py")
```

- [ ] **Step 2: Create `scripts/wave_lanes.json`** — the six existing lanes plus the two new ones, in fixed order (order = output order, R4 determinism):

```json
{
  "lanes": [
    {"name": "code-health", "script": "code-health-audit-pipeline/scripts/code_health_pipeline.py", "languages": ["python"]},
    {"name": "security", "script": "security-audit/scripts/security_audit.py", "languages": ["python"]},
    {"name": "hygiene", "script": "repo-hygiene-audit/scripts/repo_hygiene_audit.py", "languages": ["*"]},
    {"name": "docs", "script": "docs-consistency-audit/scripts/docs_consistency_audit.py", "languages": ["python"]},
    {"name": "dependency", "script": "dependency-audit/scripts/dependency_audit.py", "languages": ["python"]},
    {"name": "hotspot", "script": "hotspot-audit/scripts/hotspot_audit.py", "languages": ["*"]},
    {"name": "exec", "script": "exec-audit/scripts/exec_audit.py", "languages": ["*"]},
    {"name": "growth", "script": "growth-audit/scripts/growth_audit.py", "languages": ["*"], "requires": {"baseline_rev": true}}
  ]
}
```

- [ ] **Step 3: Implement `load_lanes(path) -> dict[str, str]`** (ordered dict from the registry; the old `LANES` constant is deleted; `_selected_lanes` consumes the loaded dict). The `growth` lane is skipped with `{"exit": 0, "status": "skipped"}` when the wave got no `--rev` (it reuses `--rev` as `--baseline-rev`); `exec` lane needs no extra args.
- [ ] **Step 4: Parallelize `_run_wave`:**

```python
def _run_wave(selected, skills_root, lanes, context):
    summary: dict[str, dict[str, Any]] = {}
    findings_by_lane: dict[str, list] = {}
    timings: dict[str, float] = {}

    def _one(lane: str):
        leaf = skills_root / lanes[lane]
        if not leaf.exists():
            return lane, (2, []), 0.0
        start = time.monotonic()
        result = _run_lane(lane, leaf, context)
        return lane, result, time.monotonic() - start

    with ThreadPoolExecutor(max_workers=len(selected)) as pool:
        for lane, (exit_code, findings), took in pool.map(_one, selected):
            summary[lane] = {"exit": exit_code,
                             "status": _status_for_exit(exit_code),
                             "findings": len(findings)}
            findings_by_lane[lane] = findings
            timings[lane] = round(took, 2)

    ordered = {lane: summary[lane] for lane in selected}        # registry order
    wave_findings = [f for lane in selected for f in findings_by_lane[lane]]
    wave_exit = 1 if any(s["exit"] >= 2 for s in ordered.values()) else 0
    return wave_exit, ordered, wave_findings, timings
```

Timings go to `wave_timings.json` next to `wave_summary.json` — and `wave_timings.json` is added to the convergence-comparison EXCLUDE list in `check_wave_baseline.py` (R4; find the comparison glob and exclude it there).
- [ ] **Step 5: Determinism proof.** Run the wave twice against repo-B itself; `wave_summary.json` and `wave_findings.json` byte-identical across runs (timings file may differ).
- [ ] **Step 6: repo-B suite green; commit** `feat(wave): registry-driven parallel lanes with timing artifact`.

## Work package W4 — patch proposals + packet synthesis (repo-B) — findings become actionable, on any repo

Admission note (R2): signal = "finding with a mechanical fix nobody applied"; advisory contract preserved — artifacts only, nothing is applied.

**Files:**
- Create: `repo-B scripts/synthesize_packets.py`
- Test: `repo-B tests/test_synthesize_packets.py`

### Task W4.1: packet synthesizer — RED then GREEN

- [ ] **Step 1: Failing tests:**

```python
def test_packet_from_finding(tmp_path):
    import scripts.synthesize_packets as sp
    finding = {"id": "abc123", "leaf": "complexity-audit", "signal": "DECOMPOSE",
               "path": "src/big.py",
               "location": {"line_start": 10, "line_end": 80, "symbol": "run"},
               "metric": {"name": "cyclomatic_complexity", "value": 19,
                          "threshold": 10},
               "suggested_action": "split run() by phase"}
    packet = sp.packet_for(finding, repo="/repo")
    assert packet["goal"].startswith("Reduce cyclomatic_complexity of run")
    assert packet["files"] == ["src/big.py"]
    assert packet["token_budget"] <= 8000
    assert "must_run" in packet and "expected" in packet


def test_mechanical_patch_for_lint_class(tmp_path, synthetic_pyrepo):
    # synthetic_pyrepo has one unused import; ruff is pinned in repo-B's env
    import scripts.synthesize_packets as sp
    artifacts = sp.mechanical_patches(
        [{"id": "f401", "signal": "DELETE", "path": "mod.py",
          "metric": {"name": "unused_import"}, "leaf": "dead-code-audit"}],
        repo=synthetic_pyrepo, out_dir=tmp_path)
    patch = tmp_path / "proposals" / "f401.patch"
    verify = tmp_path / "proposals" / "f401.verify.json"
    assert patch.exists() and patch.read_text().startswith("--- ")
    assert json.loads(verify.read_text())["commands"]
```

- [ ] **Step 2: Implement.** `packet_for(finding, repo)` → K-7-shaped dict: `{packet_id: finding["id"], repo, goal: f"Reduce {metric} of {symbol} in {path} from {value} to <= {threshold}", files: [path], must_run: ["python3 -m pytest <nearest tests dir> -q"], expected: ["exit 0", "<metric> row absent from re-run leaf findings"], forbidden: ["editing files outside `files`", "changing public CLI behavior"], token_budget: 8000}`. `mechanical_patches(findings, repo, out_dir)` → for findings whose `(leaf, metric)` is in the safe table (`dead-code-audit/unused_import`, `quality-audit/format_drift`), run `ruff check --select F401 --fix --diff <path>` (or `ruff format --diff`) inside the repo capturing the unified diff to `proposals/<id>.patch`, and write `proposals/<id>.verify.json` `{"commands": ["git apply --check proposals/<id>.patch", "<suite command>"], "expected": ["apply clean", "suite green"]}`. Never applies anything. Unknown classes are skipped silently — the safe table only grows via R2.
- [ ] **Step 3: Suite green; commit** `feat(synthesis): packet + mechanical patch proposal artifacts from wave findings`.

## Work package W5 — baseline freeze (the K-1 convergence boundary)

- [ ] **W5.1:** Ship everything from W1–W4 per K-6 (repo-A release with both new leaves; repo-B release with wave + synthesis; reinstall both; readback green). repo-P is untouched so far — no release.
- [ ] **W5.2:** Run the EXPANDED installed wave (8 lanes) on all three repos with `--rev` = each repo's fresh anchor. Triage every NEW exec/growth finding fixed-first: anything trivially fixable (the family's own duplicate executions are already gone via W0 — verify exec lane reports zero `duplicate_execution` on repo-A; if not, fix before freezing).
- [ ] **W5.3:** FREEZE: write each repo's wave baseline (now including exec/growth rows that survived triage) via the existing `check_wave_baseline.py` ratchet files, commit, and declare in the ledger: "finding universe closed; K-1 active; hard cap 14 iterations from here." From this commit, any would-be new lane/metric/class goes to `docs/superpowers/SP13-CANDIDATES.md`.

## Work package W6 — convergent parallel burn-down (iterations 3..N, after the freeze)

Per-iteration procedure (the orchestrator follows this verbatim; all hands are workers per K-3):

- [ ] **1. C-0 diagnosis (K-0):** bootstrap probe + installed 8-lane wave per repo, concurrently (three independent invocations). Backlog = wave findings + repo-A selfaudit baseline rows.
- [ ] **2. Dispatch:** for each ACTIVE repo, create a repo branch worktree; rank rows (concentration files first — same heuristic as SP11 B2); emit worker packets via `synthesize_packets.py` for single-file rows and orchestrator-authored K-7 packets for ≤2-file structural batches; apply `.patch` proposals only through a worker who runs the verify commands. ≤6 accepted batches per repo (K-5), ≤2 concurrent worktrees per repo, ≤4 worker sessions globally (K-4).
- [ ] **3. Verify per batch (orchestrator):** `npm run check` (repo-A, ~90 s) or suite + `check_wave_baseline.py` (B/P) inside the worktree; grep the gate JSON/stdout counts, never trust exit codes alone; merge ff-only on green; ratchet shrink-only; discard and record otherwise.
- [ ] **4. Strict-shrink bookkeeping (K-1):** per repo, record `rows_open_before/after`. Zero shrink → strike 1; second consecutive → repo TERMINAL (residue table to ledger; future visits = convergence verification only).
- [ ] **5. Ship (K-6):** per changed repo — convergence ×2, fresh-clone, push, CI watch (overlapped: start the next repo's step 2 while polling), release+reinstall only if leaf behavior changed, allowance expiry (W2.4), re-anchor.
- [ ] **6. Ledger append (K-9)** including the timings-vs-budget table for the iteration.

## Work package W7 — close-out (final iteration)

- [ ] **W7.1:** stale-skill purge, allowlist-driven, identical rule to SP11 B5.1 (CURRENT ∪ HISTORICAL sets from family manifests across git history; foreign dirs never touched; eligibility table to ledger before any removal).
- [ ] **W7.2:** final reinstall + readback (now 18 repo-A leaves), bootstrap probe green.
- [ ] **W7.3:** final report in the K-9 ledger: per-repo row trajectory per iteration, TERMINAL declarations with residue, growth-allowance audit (must be empty of expired entries), suppression counts, purge table, ship evidence. Final repo-A release `0.6.0`. Verify every DoD row; report DONE or BLOCKED — both valid, neither retried silently.

---

## Orchestration protocol (K-3/K-4 mechanics)

- **Worktrees:** `git worktree add /tmp/sp12/<repo>-<iter>-<slug> <main-sha>`; removed after merge/discard; `git worktree prune` at iteration end.
- **Packet lifecycle:** orchestrator writes `packet.json` → launches worker (bridge or CLI) pointed at the worktree → worker writes `status.json` (`{state: done|blocked, commands_run[], tails{}, files_touched[]}`) → orchestrator reads ONLY `status.json` + gate tails, re-runs gates itself, then merges or discards. The run dir is the evidence; chat memory is not.
- **Reviewer packets:** for structural batches, a second read-only worker gets the diff path + the plan's contract list and returns `{verdict, reasons[]}`; orchestrator rejects on any `reject` and records why.
- **Context conservation:** the orchestrator's transcript should contain packet IDs, row counts, gate tails, and ledger text — never file bodies. If a decision seems to need source reading, that's a packet, not a read.
- **Timeouts:** worker silent >30 min → kill, mark discarded, requeue once with a tightened packet; second timeout → row goes to the residue table.

## Convergence argument (why this terminates)

After W5.3 the open-row set R is finite and the universe is closed (K-1): no lane, metric, or class may be added, so |R| never grows except by hotspot re-anchor rows, which are triaged fixed-first at ship and cannot survive two iterations unfixed without making their repo TERMINAL. Every iteration, each ACTIVE repo either strictly shrinks |R_repo| or moves one strike toward TERMINAL (two strikes). Therefore the loop reaches all-repos-TERMINAL in at most `2 × |R| + 2 × repos` iterations, and the hard cap of 14 binds it regardless. Surface cannot ratchet upward because the growth gate blocks unallowed increases and allowances expire at each release (K-2). DONE and BLOCKED are both reachable, well-defined terminals.

## Out of scope (SP13 candidates — write them down, do not start them)

Makefile/tox/nox parsing in exec-audit; dead-flag detection in growth-audit; flaky-test rerun detection; multi-language code-health leaves; applying patches automatically; any new wave lane after the W5 freeze.
