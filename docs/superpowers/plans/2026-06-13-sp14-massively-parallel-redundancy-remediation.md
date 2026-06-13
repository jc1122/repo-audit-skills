# SP14: Massively-Parallel Redundancy Remediation (MPRR) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-agnostic engine that takes redundancy findings, partitions them into conflict-free (file-disjoint) work, and remediates them massively in parallel under unattended gate-gated auto-merge — then ship an orchestrator launch prompt that loops until a full re-audit finds no new redundancy issues to resolve.

**Architecture:** A deterministic Python "brain" lives in repo-B `scripts/` (normalize → file-level conflict partition → continuous saturating scheduler → gate-ladder verify → conflict-free merge integrate → KPI mining). The Opus orchestrator is the "hands": it pumps the brain (`plan`/`verify`/`integrate`/`reaudit` subcommands over a persisted run-state file), dispatches workers (native Opus subagents / opencode-worker-bridge) for the actual edits, and never edits/reads source itself.

**Tech Stack:** Python ≥3.11 stdlib only (family rule) + `hypothesis` (already a test dep) + `git`; the existing repo-A redundancy leaves (`duplication-audit`, `dead-code-audit`, `test-redundancy-triage`); the existing repo-B loop tooling (`mine_iteration_kpis.py`, `synthesize_packets.py`).

---

## Orientation (read before Task 1)

- **Spec (authority for intent):** `docs/superpowers/specs/2026-06-13-sp14-massively-parallel-redundancy-remediation-design.md` (in repo-A). Where this plan and the spec differ on detail, the spec's §3 locked decisions win.
- **Entry state:** SP13 is DONE. repo-A `96007fd`/v0.6.0, repo-B `8f27083`, repo-P `ac58303` — all clean, CI-green. Re-verify before launch; ledgers are truth.
- **Where code lands:** ALL new engine modules + tests go in **repo-B** (`~/projects/repo-audit-refactor-optimize`) under `scripts/` and `tests/`, matching the existing flat layout (`scripts/mprr_*.py`, `tests/test_mprr_*.py`). Audit leaves in repo-A are **unchanged**. Orchestration docs (this plan, the launch prompt, the ledger) live in **repo-A** `docs/superpowers/` and `docs/self-audit/`.
- **Test import convention (mirror exactly):** every test file starts with
  ```python
  REPO_ROOT = Path(__file__).resolve().parents[1]
  if str(REPO_ROOT) not in sys.path:
      sys.path.insert(0, str(REPO_ROOT))
  mod = importlib.import_module("scripts.mprr_<name>")
  ```
- **Finding schema (consumed input):** repo-A `skills/code-health-audit-pipeline/references/finding-schema.json`. Required fields: `id, leaf, signal, severity, path, location{line_start,line_end,symbol}, metric{name,value,threshold}, evidence{tool,raw}, confidence, suggested_action`. `signal ∈ {EXTRACT,MERGE,DELETE,...}`. Note: schema has a single `path`; cross-file `EXTRACT/MERGE` partner files live in `evidence.raw`.
- **test-redundancy-triage output is NOT the shared schema:** it emits rows with `test_nodeid` and `validation_decision` like `DELETE_SAFE_HIGH` / `MERGE_*` (confidence tier is the suffix). Task 1 includes an adapter.
- **Design rules carried from SP13 (binding):** R1 repo-agnostic (ship non-Python + degenerate fixtures); R5 mined-not-reported (KPIs derive from artifacts, never prose); R6 process-vs-findings separation (the engine never edits leaf finding-emission logic); R7 lesson honesty. Contracts L-0..L-10 (worker-only hands, surface budget, ship gate, ledger, termination) govern the runtime loop (Part II).
- **Run `pytest` from the repo-B root** (`pytest.ini` sets `testpaths = tests`).

## File structure (locked before tasks)

| File | Responsibility |
|---|---|
| `scripts/mprr_normalize.py` | Ingest findings + triage rows → `RemediationItem` (id, lane, signal, files, remediation_class, confidence, finding). The only module that knows the input schemas. |
| `scripts/mprr_partition.py` | File-level conflict predicate (`conflicts`, `eligible`). Pure. Duck-types on `.id`/`.files`. |
| `scripts/mprr_schedule.py` | `SaturatingScheduler`: pool ceiling N, live `locked_files`, dispatchable/start/complete. Pure state machine; dispatch is injected by the caller. |
| `scripts/mprr_gate.py` | The gate ladder: `verify(remediation_class, evidence)` → (ok, reasons). Pure. |
| `scripts/mprr_integrate.py` | `assert_scope` (worker diff ⊆ declared files) + `merge_clean` (assert conflict-free git merge). |
| `scripts/mprr_packets.py` | `remediation_packet(item, repo, lessons)` → file-backed worker packet (reuses the existing packet shape). |
| `scripts/mprr_run.py` | CLI the orchestrator pumps: `plan`/`verify`/`integrate`/`reaudit`, persisting `mprr_state.json` + `mprr_events.jsonl` in the run dir. |
| `scripts/mine_iteration_kpis.py` (modify) | Add MPRR KPI mining: pool utilization, merge-conflict-rate, peak/mean concurrency. |
| `tests/test_mprr_*.py` | One test module per engine module. |
| `tests/fixtures/mprr/{known_redundancy,degenerate,nonpython}/` | Fixture repos for the e2e + R1 tests. |
| repo-A `docs/superpowers/SP14-LAUNCH-PROMPT.md` | The orchestrator launch key (Task 11). |

---

# Part I — the deterministic engine (repo-B)

### Task 1: `mprr_normalize` — findings + triage rows → `RemediationItem`

**Files:**
- Create: `scripts/mprr_normalize.py`
- Test: `tests/test_mprr_normalize.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_normalize.py."""
from __future__ import annotations
import importlib, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
norm = importlib.import_module("scripts.mprr_normalize")


def _f(**kw):
    base = {"id": "a", "leaf": "dead-code", "signal": "DELETE",
            "path": "pkg/m.py", "evidence": {"raw": ""}, "confidence": "high"}
    base.update(kw); return base


def test_dead_code_is_mechanical_single_file():
    [it] = norm.normalize([_f()])
    assert it.remediation_class == "mechanical"
    assert it.files == ("pkg/m.py",)
    assert it.lane == "dead-code"


def test_duplication_extract_is_refactor_and_pulls_partner_file():
    raw = "Clone of pkg/a.py:10-20 and pkg/b.py:30-40"
    [it] = norm.normalize([_f(leaf="duplication", signal="EXTRACT",
                              path="pkg/a.py", evidence={"raw": raw})])
    assert it.remediation_class == "refactor"
    assert it.files == ("pkg/a.py", "pkg/b.py")


def test_non_redundancy_leaf_is_dropped():
    assert norm.normalize([_f(leaf="complexity", signal="SIMPLIFY")]) == []


def test_triage_high_delete_becomes_test_removal_item():
    rows = [{"test_nodeid": "tests/test_x.py::test_a", "validation_decision": "DELETE_SAFE_HIGH"}]
    [it] = norm.from_triage_report(rows)
    assert it.remediation_class == "test_removal"
    assert it.confidence == "high"
    assert it.files == ("tests/test_x.py",)


def test_triage_non_high_is_dropped():
    rows = [{"test_nodeid": "tests/test_x.py::t", "validation_decision": "DELETE_SAFE_LOW"}]
    assert norm.from_triage_report(rows) == []


def test_items_are_sorted_by_id_deterministically():
    out = norm.normalize([_f(id="b"), _f(id="a")])
    assert [it.id for it in out] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_normalize.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_normalize'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Normalize redundancy findings + triage rows into RemediationItems.

The only module that knows the input schemas. Stdlib only, deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# leaf -> remediation class (the gate ladder key, see scripts.mprr_gate)
_CLASS_BY_LEAF: dict[str, str] = {
    "dead-code": "mechanical",
    "duplication": "refactor",
    "test-redundancy": "test_removal",
}
_REDUNDANCY_LEAVES = frozenset(_CLASS_BY_LEAF)
_PATH_RE = re.compile(r"[\w./-]+\.(?:py|js|ts|jsx|tsx)")


@dataclass(frozen=True)
class RemediationItem:
    id: str
    lane: str
    signal: str
    files: tuple[str, ...]
    remediation_class: str
    confidence: str
    finding: dict[str, Any]


def _files_for(finding: dict[str, Any]) -> tuple[str, ...]:
    paths = {str(finding.get("path", "")).strip()}
    if str(finding.get("signal", "")) in {"EXTRACT", "MERGE"}:
        raw = str((finding.get("evidence") or {}).get("raw") or "")
        paths.update(_PATH_RE.findall(raw))
    return tuple(sorted(p for p in paths if p))


def normalize(findings: list[dict[str, Any]]) -> list[RemediationItem]:
    items: list[RemediationItem] = []
    for f in findings:
        leaf = str(f.get("leaf", ""))
        if leaf not in _REDUNDANCY_LEAVES:
            continue
        items.append(RemediationItem(
            id=str(f.get("id", "")),
            lane=leaf,
            signal=str(f.get("signal", "")),
            files=_files_for(f),
            remediation_class=_CLASS_BY_LEAF[leaf],
            confidence=str(f.get("confidence", "low")),
            finding=f,
        ))
    return sorted(items, key=lambda it: it.id)


def from_triage_report(rows: list[dict[str, Any]]) -> list[RemediationItem]:
    """Adapt test-redundancy-triage rows. Only high-confidence DELETE/MERGE qualify."""
    items: list[RemediationItem] = []
    for r in rows:
        decision = str(r.get("validation_decision", ""))
        if not decision.endswith("_HIGH") or not decision.startswith(("DELETE", "MERGE")):
            continue
        nodeid = str(r.get("test_nodeid", ""))
        path = nodeid.split("::", 1)[0]
        if not path:
            continue
        items.append(RemediationItem(
            id=str(r.get("id") or nodeid),
            lane="test-redundancy",
            signal=decision.split("_", 1)[0],  # DELETE | MERGE
            files=(path,),
            remediation_class="test_removal",
            confidence="high",
            finding=dict(r),
        ))
    return sorted(items, key=lambda it: it.id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_normalize.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_normalize.py tests/test_mprr_normalize.py
git commit -m "feat(mprr): normalize redundancy findings + triage rows into RemediationItems"
```

---

### Task 2: `mprr_partition` — file-level conflict predicate (+ property test)

**Files:**
- Create: `scripts/mprr_partition.py`
- Test: `tests/test_mprr_partition.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_partition.py."""
from __future__ import annotations
import importlib, sys
from dataclasses import dataclass
from pathlib import Path
from hypothesis import given, strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
part = importlib.import_module("scripts.mprr_partition")


@dataclass(frozen=True)
class _It:
    id: str
    files: tuple[str, ...]


def test_shared_file_conflicts():
    assert part.conflicts(_It("a", ("x.py",)), _It("b", ("x.py", "y.py")))

def test_disjoint_files_do_not_conflict():
    assert not part.conflicts(_It("a", ("x.py",)), _It("b", ("y.py",)))

def test_eligible_iff_disjoint_from_locks():
    it = _It("a", ("x.py", "y.py"))
    assert part.eligible(it, set())
    assert part.eligible(it, {"z.py"})
    assert not part.eligible(it, {"y.py"})


@given(st.lists(st.lists(st.sampled_from("abcde"), min_size=1, max_size=3), max_size=8))
def test_eligible_matches_conflicts_against_a_single_running_item(file_lists):
    items = [_It(str(i), tuple(set(fs))) for i, fs in enumerate(file_lists)]
    for a in items:
        for b in items:
            locked = set(b.files)
            # a is eligible against b's locks iff a and b do not conflict
            assert part.eligible(a, locked) == (not part.conflicts(a, b))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_partition.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_partition'`

- [ ] **Step 3: Write minimal implementation**

```python
"""File-level conflict model. Pure; duck-types on `.files` (a tuple of paths)."""
from __future__ import annotations

from typing import Any, Iterable


def conflicts(a: Any, b: Any) -> bool:
    """True iff two items share any file (so they may not run concurrently)."""
    return bool(set(a.files) & set(b.files))


def eligible(item: Any, locked_files: Iterable[str]) -> bool:
    """True iff the item's files are disjoint from the currently-locked files."""
    return not (set(item.files) & set(locked_files))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_partition.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_partition.py tests/test_mprr_partition.py
git commit -m "feat(mprr): file-level conflict + eligibility predicate"
```

---

### Task 3: `mprr_schedule` — continuous saturating scheduler (+ invariant & liveness property tests)

**Files:**
- Create: `scripts/mprr_schedule.py`
- Test: `tests/test_mprr_schedule.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_schedule.py — the saturating scheduler invariant."""
from __future__ import annotations
import importlib, random, sys
from dataclasses import dataclass
from pathlib import Path
from hypothesis import given, settings, strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sched = importlib.import_module("scripts.mprr_schedule")


@dataclass(frozen=True)
class _It:
    id: str
    files: tuple[str, ...]


def _items(specs):
    return [_It(str(i), tuple(sorted(set(fs)))) for i, fs in enumerate(specs)]


def test_dispatchable_never_co_locks_shared_files():
    s = sched.SaturatingScheduler(_items([["x"], ["x", "y"], ["z"]]), ceiling=4)
    batch = s.dispatchable()
    seen: set[str] = set()
    for it in batch:
        assert not (set(it.files) & seen)
        seen |= set(it.files)


def test_respects_ceiling():
    s = sched.SaturatingScheduler(_items([["a"], ["b"], ["c"]]), ceiling=2)
    assert len(s.dispatchable()) == 2


def test_completing_releases_locks_for_blocked_item():
    s = sched.SaturatingScheduler(_items([["x"], ["x"]]), ceiling=4)
    first = s.dispatchable()
    assert len(first) == 1           # second shares "x", blocked
    s.start(first[0])
    assert s.dispatchable() == []    # still blocked while first runs
    s.complete(first[0].id)
    assert len(s.dispatchable()) == 1  # now free


@settings(max_examples=200)
@given(specs=st.lists(st.lists(st.sampled_from("abcd"), min_size=1, max_size=3), max_size=10),
       ceiling=st.integers(min_value=1, max_value=5), seed=st.integers())
def test_invariant_and_liveness_under_random_completion(specs, ceiling, seed):
    rng = random.Random(seed)
    s = sched.SaturatingScheduler(_items(specs), ceiling=ceiling)
    running: dict[str, _It] = {}
    started = 0
    total = len(specs)
    steps = 0
    while not s.done():
        steps += 1
        assert steps < 10_000, "scheduler failed to make progress (liveness)"
        for it in s.dispatchable():
            s.start(it); running[it.id] = it; started += 1
        # INVARIANT: running items are pairwise file-disjoint
        seen: set[str] = set()
        for it in running.values():
            assert not (set(it.files) & seen)
            seen |= set(it.files)
        if running:
            done_id = rng.choice(list(running))
            s.complete(done_id); running.pop(done_id)
    assert started == total  # every item eventually ran
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_schedule.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_schedule'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Continuous saturating scheduler. Pure state machine; the caller injects
dispatch (start) and completion. The disjoint-lock invariant is enforced here.
"""
from __future__ import annotations

from typing import Any


class SaturatingScheduler:
    def __init__(self, items: list[Any], ceiling: int) -> None:
        if ceiling < 1:
            raise ValueError("ceiling must be >= 1")
        # deterministic order: by id
        self._pending: list[Any] = sorted(items, key=lambda it: it.id)
        self._ceiling = ceiling
        self._locked: set[str] = set()
        self._running: dict[str, Any] = {}

    def dispatchable(self) -> list[Any]:
        """Items startable right now: pool has room and files are disjoint from
        current locks AND from each other within this batch."""
        out: list[Any] = []
        locked = set(self._locked)
        for it in self._pending:
            if len(self._running) + len(out) >= self._ceiling:
                break
            if not (set(it.files) & locked):
                out.append(it)
                locked |= set(it.files)
        return out

    def start(self, item: Any) -> None:
        self._pending.remove(item)
        self._running[item.id] = item
        self._locked |= set(item.files)

    def complete(self, item_id: str) -> None:
        item = self._running.pop(item_id)
        # safe: the invariant guarantees no other running item holds these files
        self._locked -= set(item.files)

    def done(self) -> bool:
        return not self._pending and not self._running

    @property
    def running_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._running))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_schedule.py -q`
Expected: PASS (the property test explores 200 random schedules; invariant + liveness hold)

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_schedule.py tests/test_mprr_schedule.py
git commit -m "feat(mprr): saturating scheduler with property-proven disjoint-lock invariant"
```

---

### Task 4: `mprr_gate` — the three-tier gate ladder

**Files:**
- Create: `scripts/mprr_gate.py`
- Test: `tests/test_mprr_gate.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_gate.py — gate ladder verification."""
from __future__ import annotations
import importlib, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
gate = importlib.import_module("scripts.mprr_gate")


def test_mechanical_needs_tests_and_reaudit():
    ok, reasons = gate.verify("mechanical", {"tests_passed": True, "finding_resolved": True})
    assert ok and reasons == []
    ok, reasons = gate.verify("mechanical", {"tests_passed": False, "finding_resolved": True})
    assert not ok and any("tests" in r for r in reasons)


def test_refactor_requires_mutation_80():
    base = {"tests_passed": True, "finding_resolved": True}
    assert gate.verify("refactor", {**base, "mutation_score": 0.80})[0]
    ok, reasons = gate.verify("refactor", {**base, "mutation_score": 0.79})
    assert not ok and any("mutation" in r for r in reasons)


def test_test_removal_requires_parity_and_high_confidence():
    good = {"coverage_parity": True, "mutation_parity": True, "confidence": "high"}
    assert gate.verify("test_removal", good)[0]
    ok, reasons = gate.verify("test_removal", {**good, "confidence": "medium"})
    assert not ok and any("confidence" in r for r in reasons)


def test_unknown_class_fails_closed():
    ok, reasons = gate.verify("bogus", {})
    assert not ok and reasons
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_gate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
"""The gate ladder: what proof authorizes an unattended auto-merge, per class.

Pure: `verify` inspects a worker's reported evidence dict. The orchestrator
re-derives this evidence itself from gate artifacts — it never trusts a
worker's self-reported 'green' (L-3).
"""
from __future__ import annotations

from typing import Any

MUTATION_FLOOR = 0.80


def verify(remediation_class: str, evidence: dict[str, Any] | None) -> tuple[bool, list[str]]:
    ev = evidence or {}
    reasons: list[str] = []

    def need(ok: bool, msg: str) -> None:
        if not ok:
            reasons.append(msg)

    if remediation_class == "mechanical":
        need(ev.get("tests_passed") is True, "tests not green")
        need(ev.get("finding_resolved") is True, "lane re-audit still reports the finding")
    elif remediation_class == "refactor":
        need(ev.get("tests_passed") is True, "tests not green")
        ms = ev.get("mutation_score")
        need(isinstance(ms, (int, float)) and ms >= MUTATION_FLOOR,
             f"mutation score below {MUTATION_FLOOR}")
        need(ev.get("finding_resolved") is True, "duplication re-audit still reports the clone")
    elif remediation_class == "test_removal":
        need(ev.get("coverage_parity") is True, "coverage parity not proven")
        need(ev.get("mutation_parity") is True, "mutation parity not proven")
        need(ev.get("confidence") == "high", "triage confidence below high")
    else:
        reasons.append(f"unknown remediation_class {remediation_class!r}")

    return (not reasons, reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_gate.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_gate.py tests/test_mprr_gate.py
git commit -m "feat(mprr): three-tier gate ladder (mechanical/refactor/test_removal)"
```

---

### Task 5: `mprr_integrate` — scope check + conflict-free merge assertion

**Files:**
- Create: `scripts/mprr_integrate.py`
- Test: `tests/test_mprr_integrate.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_integrate.py."""
from __future__ import annotations
import importlib, subprocess, sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
integ = importlib.import_module("scripts.mprr_integrate")


def test_assert_scope_accepts_subset():
    ok, reasons = integ.assert_scope(["a.py", "b.py"], ["a.py"])
    assert ok and reasons == []


def test_assert_scope_rejects_undeclared_file():
    ok, reasons = integ.assert_scope(["a.py"], ["a.py", "rogue.py"])
    assert not ok and any("rogue.py" in r for r in reasons)


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                   capture_output=True, text=True)


def _init_repo(tmp_path):
    repo = tmp_path / "r"; repo.mkdir()
    _git(repo, "init", "-q"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / "base.py").write_text("x = 1\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "base")
    return repo


def test_merge_clean_merges_disjoint_branch(tmp_path):
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "w1")
    (repo / "a.py").write_text("a = 1\n"); _git(repo, "add", "."); _git(repo, "commit", "-qm", "a")
    _git(repo, "checkout", "-q", "master")
    integ.merge_clean(str(repo), "w1")          # disjoint -> clean
    assert (repo / "a.py").exists()


def test_merge_clean_raises_on_conflict(tmp_path):
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "w1")
    (repo / "base.py").write_text("x = 2\n"); _git(repo, "add", "."); _git(repo, "commit", "-qm", "w1")
    _git(repo, "checkout", "-q", "master")
    (repo / "base.py").write_text("x = 3\n"); _git(repo, "add", "."); _git(repo, "commit", "-qm", "main")
    with pytest.raises(integ.InvariantViolation):
        integ.merge_clean(str(repo), "w1")      # overlapping edit -> must raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_integrate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_integrate'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Merge integration: enforce the disjoint-file invariant at merge time.

A textual conflict during merge is structurally impossible under the scheduler
invariant, so it is treated as a hard error (partitioner/worker bug), not a
normal merge conflict to resolve.
"""
from __future__ import annotations

import subprocess  # nosec B404 — fixed git argv, no shell
from typing import Iterable


class InvariantViolation(RuntimeError):
    """Raised when a merge that must be conflict-free reports a conflict."""


def assert_scope(declared_files: Iterable[str], diff_files: Iterable[str]) -> tuple[bool, list[str]]:
    extra = sorted(set(diff_files) - set(declared_files))
    return (not extra, [f"worker touched undeclared file: {p}" for p in extra])


def merge_clean(repo: str, branch: str) -> None:
    """Merge `branch` into the current branch; raise InvariantViolation on conflict."""
    proc = subprocess.run(  # nosec B603 — fixed argv
        ["git", "merge", "--no-ff", "--no-edit", branch],
        cwd=repo, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        subprocess.run(["git", "merge", "--abort"], cwd=repo,
                       capture_output=True, text=True)  # nosec B603,B607
        raise InvariantViolation(
            f"merge of {branch} conflicted (disjoint-file invariant violated): "
            f"{proc.stdout.strip()} {proc.stderr.strip()}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_integrate.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_integrate.py tests/test_mprr_integrate.py
git commit -m "feat(mprr): scope check + conflict-free merge integrator (invariant enforcement)"
```

---

### Task 6: `mprr_packets` — remediation worker packets

**Files:**
- Create: `scripts/mprr_packets.py`
- Test: `tests/test_mprr_packets.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_packets.py."""
from __future__ import annotations
import importlib, sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
pk = importlib.import_module("scripts.mprr_packets")


@dataclass(frozen=True)
class _It:
    id: str; lane: str; signal: str; files: tuple[str, ...]
    remediation_class: str; confidence: str; finding: dict


def _item(**kw):
    base = dict(id="a", lane="dead-code", signal="DELETE", files=("pkg/m.py",),
                remediation_class="mechanical", confidence="high", finding={"suggested_action": "remove f"})
    base.update(kw); return _It(**base)


def test_packet_declares_only_item_files():
    p = pk.remediation_packet(_item(), repo="/r", lessons=[])
    assert p["files"] == ["pkg/m.py"]
    assert p["packet_id"] == "a"
    assert p["token_budget"] <= 8000


def test_refactor_packet_requires_mutation_in_must_run():
    p = pk.remediation_packet(_item(lane="duplication", signal="EXTRACT",
                                    remediation_class="refactor"), repo="/r", lessons=[])
    assert any("mutmut" in c or "mutation" in c for c in p["must_run"])


def test_lessons_capped_at_five():
    p = pk.remediation_packet(_item(), repo="/r", lessons=[f"L{i}" for i in range(9)])
    assert len(p["lessons"]) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_packets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_packets'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Build file-backed remediation worker packets (one finding -> one packet).

Mirrors the existing K-7 packet shape in scripts.synthesize_packets; the
must_run set is derived from the gate ladder class so a worker proves exactly
what mprr_gate.verify will check.
"""
from __future__ import annotations

from typing import Any

_TOKEN_BUDGET = 8000
_LESSON_CAP = 5

# gate-class -> verification commands the worker must run and pass
_MUST_RUN: dict[str, list[str]] = {
    "mechanical": ["pytest -q", "<re-run the finding's lane; assert the finding is gone>"],
    "refactor": ["pytest -q", "mutmut run --paths-to-mutate <changed modules> (>=80% killed)",
                 "<re-run duplication-audit; assert the clone is gone>"],
    "test_removal": ["pytest -q (suite still green after removal)",
                     "<coverage parity: line+branch unchanged>",
                     "<mutation parity: kill-set not weakened>"],
}
_EXPECTED: dict[str, list[str]] = {
    "mechanical": ["tests_passed=true", "finding_resolved=true"],
    "refactor": ["tests_passed=true", "mutation_score>=0.80", "finding_resolved=true"],
    "test_removal": ["coverage_parity=true", "mutation_parity=true", "confidence=high"],
}


def remediation_packet(item: Any, repo: str, lessons: list[str]) -> dict[str, Any]:
    cls = item.remediation_class
    action = str((item.finding or {}).get("suggested_action", "")) or f"remediate {item.signal} finding"
    return {
        "packet_id": item.id,
        "repo": repo,
        "goal": f"{action} (lane={item.lane}, signal={item.signal})",
        "files": list(item.files),            # the DECLARED allowed files (scope lock)
        "remediation_class": cls,
        "must_run": list(_MUST_RUN.get(cls, [])),
        "expected": list(_EXPECTED.get(cls, [])),
        "forbidden": ["edits to any file outside `files`", "new public API", "test weakening"],
        "lessons": list(lessons)[:_LESSON_CAP],
        "token_budget": _TOKEN_BUDGET,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_packets.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_packets.py tests/test_mprr_packets.py
git commit -m "feat(mprr): remediation worker packet synthesis keyed to the gate ladder"
```

---

### Task 7: `mprr_run` — the CLI the orchestrator pumps

**Files:**
- Create: `scripts/mprr_run.py`
- Test: `tests/test_mprr_run.py`

The orchestrator never holds scheduler state in chat memory; it persists in `<run_dir>/mprr_state.json` and logs every transition to `<run_dir>/mprr_events.jsonl` (R5 mining source). Subcommands:
- `plan --run-dir D --findings F.json --triage T.json --ceiling N` — (re)builds items if absent, then prints the next dispatchable packets as JSON and records `start` events + locks for each.
- `integrate --run-dir D --packet-id P --evidence E.json --diff-files a.py,b.py --repo R --branch B` — runs `assert_scope` then `mprr_gate.verify`; on pass calls `merge_clean` and records a `merge` event (`conflict=false`); on fail records a `discard`. Always `complete`s the item (releases locks).
- `reaudit --findings F.json --triage T.json` — prints the residual redundancy-item count (the convergence metric).

- [ ] **Step 1: Write the failing test**

```python
"""Tests for scripts/mprr_run.py — orchestrator-facing CLI over persisted state."""
from __future__ import annotations
import importlib, json, subprocess, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
run = importlib.import_module("scripts.mprr_run")


def _findings(tmp):
    data = [
        {"id": "d1", "leaf": "dead-code", "signal": "DELETE", "path": "a.py",
         "evidence": {"raw": ""}, "confidence": "high"},
        {"id": "d2", "leaf": "dead-code", "signal": "DELETE", "path": "b.py",
         "evidence": {"raw": ""}, "confidence": "high"},
    ]
    p = tmp / "f.json"; p.write_text(json.dumps(data)); return p


def test_plan_emits_disjoint_packets_and_persists_state(tmp_path):
    run_dir = tmp_path / "rd"; run_dir.mkdir()
    code = run.main(["plan", "--run-dir", str(run_dir),
                     "--findings", str(_findings(tmp_path)), "--ceiling", "4"])
    assert code == 0
    state = json.loads((run_dir / "mprr_state.json").read_text())
    assert set(state["running"]) == {"d1", "d2"}            # disjoint -> both start
    assert set(state["locked"]) == {"a.py", "b.py"}


def test_reaudit_counts_residual_items(tmp_path):
    code = run.main(["reaudit", "--findings", str(_findings(tmp_path))])
    assert code == 2  # exit code carries the residual count (0 == converged)


def test_integrate_releases_locks_on_gate_fail(tmp_path):
    run_dir = tmp_path / "rd"; run_dir.mkdir()
    run.main(["plan", "--run-dir", str(run_dir),
              "--findings", str(_findings(tmp_path)), "--ceiling", "4"])
    ev = tmp_path / "e.json"; ev.write_text(json.dumps({"tests_passed": False}))
    code = run.main(["integrate", "--run-dir", str(run_dir), "--packet-id", "d1",
                     "--evidence", str(ev), "--diff-files", "a.py",
                     "--repo", str(tmp_path), "--branch", "nope", "--no-merge"])
    assert code == 1  # gate failed
    state = json.loads((run_dir / "mprr_state.json").read_text())
    assert "d1" not in state["running"] and "a.py" not in state["locked"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mprr_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.mprr_run'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Orchestrator-facing CLI. Stdlib only. State lives on disk, never in chat."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts import mprr_gate, mprr_integrate, mprr_normalize, mprr_packets
from scripts.mprr_schedule import SaturatingScheduler


def _load(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    return json.loads(Path(path).read_text())


def _items(findings_path: str | None, triage_path: str | None) -> list[Any]:
    items = mprr_normalize.normalize(_load(findings_path))
    items += mprr_normalize.from_triage_report(_load(triage_path))
    return sorted(items, key=lambda it: it.id)


def _log(run_dir: Path, event: dict[str, Any]) -> None:
    with (run_dir / "mprr_events.jsonl").open("a") as fh:
        fh.write(json.dumps(event) + "\n")


def _read_state(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "mprr_state.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"running": {}, "locked": []}


def _write_state(run_dir: Path, running: dict[str, list[str]], locked: set[str]) -> None:
    (run_dir / "mprr_state.json").write_text(
        json.dumps({"running": running, "locked": sorted(locked)}, indent=2))


def _cmd_plan(a: argparse.Namespace) -> int:
    run_dir = Path(a.run_dir)
    items = _items(a.findings, a.triage)
    by_id = {it.id: it for it in items}
    state = _read_state(run_dir)
    running: dict[str, list[str]] = dict(state["running"])
    locked: set[str] = set(state["locked"])
    pending = [it for it in items if it.id not in running]
    sched = SaturatingScheduler(pending, ceiling=a.ceiling)
    # seed scheduler with already-running locks by lowering effective room
    sched._locked = set(locked)                      # noqa: SLF001 (deliberate seed)
    sched._running = {k: by_id.get(k) for k in running}  # noqa: SLF001
    batch = sched.dispatchable()
    packets = []
    for it in batch:
        running[it.id] = list(it.files)
        locked |= set(it.files)
        packets.append(mprr_packets.remediation_packet(it, repo=a.repo or "", lessons=[]))
        _log(run_dir, {"event": "start", "id": it.id, "files": list(it.files)})
    _write_state(run_dir, running, locked)
    print(json.dumps(packets, indent=2))
    return 0


def _cmd_integrate(a: argparse.Namespace) -> int:
    run_dir = Path(a.run_dir)
    state = _read_state(run_dir)
    running: dict[str, list[str]] = dict(state["running"])
    locked: set[str] = set(state["locked"])
    files = running.get(a.packet_id, [])
    evidence = json.loads(Path(a.evidence).read_text())
    diff_files = [f for f in (a.diff_files or "").split(",") if f]
    rc = evidence.get("remediation_class") or _class_of(a, run_dir)
    scope_ok, scope_reasons = mprr_integrate.assert_scope(files, diff_files)
    gate_ok, gate_reasons = mprr_gate.verify(rc, evidence)
    merged = False
    status = "discard"
    if scope_ok and gate_ok:
        if not a.no_merge:
            mprr_integrate.merge_clean(a.repo, a.branch)  # raises on conflict
        merged = True
        status = "merge"
    # always release locks (complete)
    running.pop(a.packet_id, None)
    locked -= set(files)
    _write_state(run_dir, running, locked)
    _log(run_dir, {"event": status, "id": a.packet_id, "conflict": False,
                   "merged": merged, "reasons": scope_reasons + gate_reasons})
    return 0 if merged else 1


def _class_of(a: argparse.Namespace, run_dir: Path) -> str:
    # remediation_class is carried in the evidence; fall back to "mechanical"
    return "mechanical"


def _cmd_reaudit(a: argparse.Namespace) -> int:
    return len(_items(a.findings, a.triage))  # exit code = residual count (0 = converged)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mprr_run")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("plan")
    sp.add_argument("--run-dir", required=True); sp.add_argument("--findings")
    sp.add_argument("--triage"); sp.add_argument("--ceiling", type=int, default=8)
    sp.add_argument("--repo", default=""); sp.set_defaults(fn=_cmd_plan)

    si = sub.add_parser("integrate")
    si.add_argument("--run-dir", required=True); si.add_argument("--packet-id", required=True)
    si.add_argument("--evidence", required=True); si.add_argument("--diff-files", default="")
    si.add_argument("--repo", default="."); si.add_argument("--branch", default="")
    si.add_argument("--no-merge", action="store_true"); si.set_defaults(fn=_cmd_integrate)

    sr = sub.add_parser("reaudit")
    sr.add_argument("--findings"); sr.add_argument("--triage"); sr.set_defaults(fn=_cmd_reaudit)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
```

> Note for the implementer: the two `# noqa: SLF001` scheduler-seed lines are the one deliberate internal-state poke (re-seeding locks/running across CLI ticks). If repo-B's lint forbids `SLF001`, add a public `SaturatingScheduler.seed(running, locked)` method in Task 3 instead and call that here. Pick one and keep it consistent.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mprr_run.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/mprr_run.py tests/test_mprr_run.py
git commit -m "feat(mprr): orchestrator CLI (plan/integrate/reaudit) over persisted run-state"
```

---

### Task 8: KPI miner extension — pool utilization, merge-conflict-rate, concurrency

**Files:**
- Modify: `scripts/mine_iteration_kpis.py` (add `mine_mprr_kpis`)
- Test: `tests/test_mine_iteration_kpis.py` (append cases)

- [ ] **Step 1: Write the failing test (append to the existing test module)**

```python
def test_mine_mprr_kpis_from_events(tmp_path):
    import importlib, sys
    from pathlib import Path
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    miner = importlib.import_module("scripts.mine_iteration_kpis")
    events = tmp_path / "mprr_events.jsonl"
    events.write_text("\n".join([
        '{"event": "start", "id": "a", "files": ["x.py"]}',
        '{"event": "start", "id": "b", "files": ["y.py"]}',
        '{"event": "merge", "id": "a", "conflict": false, "merged": true}',
        '{"event": "discard", "id": "b", "conflict": false, "merged": false}',
    ]) + "\n")
    kpi = miner.mine_mprr_kpis(str(events), ceiling=4)
    assert kpi["dispatched"] == 2
    assert kpi["merged"] == 1
    assert kpi["merge_conflict_rate"] == 0.0
    assert kpi["peak_concurrency"] == 2
    assert 0.0 <= kpi["pool_utilization"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mine_iteration_kpis.py::test_mine_mprr_kpis_from_events -q`
Expected: FAIL — `AttributeError: module 'scripts.mine_iteration_kpis' has no attribute 'mine_mprr_kpis'`

- [ ] **Step 3: Add the implementation to `scripts/mine_iteration_kpis.py`**

```python
def mine_mprr_kpis(events_path: str, ceiling: int) -> dict[str, float | int]:
    """Mine MPRR loop KPIs from the run-dir event log (R5: derived, never typed)."""
    import json
    from pathlib import Path

    running = 0
    peak = 0
    samples: list[int] = []
    dispatched = merged = conflicts = 0
    for line in Path(events_path).read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        kind = ev.get("event")
        if kind == "start":
            running += 1
            dispatched += 1
        elif kind in {"merge", "discard"}:
            running = max(0, running - 1)
            if kind == "merge":
                merged += 1
            if ev.get("conflict"):
                conflicts += 1
        peak = max(peak, running)
        samples.append(running)
    mean = sum(samples) / len(samples) if samples else 0.0
    return {
        "dispatched": dispatched,
        "merged": merged,
        "merge_conflict_rate": (conflicts / merged) if merged else 0.0,
        "peak_concurrency": peak,
        "mean_concurrency": round(mean, 3),
        "pool_utilization": round(mean / ceiling, 3) if ceiling else 0.0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mine_iteration_kpis.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/mine_iteration_kpis.py tests/test_mine_iteration_kpis.py
git commit -m "feat(mprr): mine pool-utilization + merge-conflict-rate + concurrency KPIs (R5)"
```

---

### Task 9: fixtures + end-to-end conflict-free drain test

**Files:**
- Create: `tests/fixtures/mprr/known_redundancy/findings.json` (3 findings: 2 disjoint single-file DELETEs + 1 cross-file EXTRACT spanning both DELETE files)
- Create: `tests/fixtures/mprr/degenerate/findings.json` (3 findings all on `same.py`)
- Create: `tests/fixtures/mprr/nonpython/findings.json` (1 duplication finding on `app.js`, R1 repo-agnostic)
- Test: `tests/test_mprr_e2e.py`

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/mprr/known_redundancy/findings.json`:
```json
[
  {"id": "k1", "leaf": "dead-code", "signal": "DELETE", "path": "pkg/a.py",
   "evidence": {"raw": ""}, "confidence": "high"},
  {"id": "k2", "leaf": "dead-code", "signal": "DELETE", "path": "pkg/b.py",
   "evidence": {"raw": ""}, "confidence": "high"},
  {"id": "k3", "leaf": "duplication", "signal": "EXTRACT", "path": "pkg/a.py",
   "evidence": {"raw": "clone across pkg/a.py and pkg/b.py"}, "confidence": "medium"}]
```
`tests/fixtures/mprr/degenerate/findings.json`:
```json
[
  {"id": "g1", "leaf": "dead-code", "signal": "DELETE", "path": "same.py", "evidence": {"raw": ""}, "confidence": "high"},
  {"id": "g2", "leaf": "dead-code", "signal": "DELETE", "path": "same.py", "evidence": {"raw": ""}, "confidence": "high"},
  {"id": "g3", "leaf": "dead-code", "signal": "DELETE", "path": "same.py", "evidence": {"raw": ""}, "confidence": "high"}]
```
`tests/fixtures/mprr/nonpython/findings.json`:
```json
[{"id": "n1", "leaf": "duplication", "signal": "MERGE", "path": "app.js",
  "evidence": {"raw": "clone within app.js"}, "confidence": "medium"}]
```

- [ ] **Step 2: Write the failing e2e test**

```python
"""End-to-end: normalize -> partition -> schedule drains with 0 conflicts."""
from __future__ import annotations
import importlib, json, random, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
norm = importlib.import_module("scripts.mprr_normalize")
sched = importlib.import_module("scripts.mprr_schedule")
FIX = REPO_ROOT / "tests" / "fixtures" / "mprr"


def _drain(items, ceiling, seed=0):
    rng = random.Random(seed)
    s = sched.SaturatingScheduler(items, ceiling=ceiling)
    running = {}
    while not s.done():
        for it in s.dispatchable():
            s.start(it); running[it.id] = it
            seen = set()
            for r in running.values():        # invariant holds every tick
                assert not (set(r.files) & seen); seen |= set(r.files)
        if running:
            k = rng.choice(list(running)); s.complete(k); running.pop(k)
    return True


def test_known_redundancy_drains_conflict_free():
    items = norm.normalize(json.loads((FIX / "known_redundancy" / "findings.json").read_text()))
    assert len(items) == 3
    # k3 EXTRACT spans a.py+b.py so it can never co-run with k1 or k2
    assert _drain(items, ceiling=8)


def test_degenerate_all_one_file_serializes():
    items = norm.normalize(json.loads((FIX / "degenerate" / "findings.json").read_text()))
    s = sched.SaturatingScheduler(items, ceiling=8)
    assert len(s.dispatchable()) == 1          # only one may run at a time
    assert _drain(items, ceiling=8)


def test_nonpython_fixture_is_handled():
    items = norm.normalize(json.loads((FIX / "nonpython" / "findings.json").read_text()))
    assert len(items) == 1 and items[0].files == ("app.js",)
    assert _drain(items, ceiling=8)
```

- [ ] **Step 3: Run to verify it passes (modules already exist from Tasks 1-3)**

Run: `pytest tests/test_mprr_e2e.py -q`
Expected: PASS (3 passed)

- [ ] **Step 4: Run the full engine suite**

Run: `pytest tests/test_mprr_*.py -q`
Expected: PASS (all MPRR modules green)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/mprr tests/test_mprr_e2e.py
git commit -m "test(mprr): fixtures + e2e conflict-free drain (known/degenerate/non-python)"
```

---

### Task 10: SKILL.md admission docs + instruction-lint green

**Files:**
- Modify: `SKILL.md` (repo-B) — add an "MPRR remediation track" section
- Modify: `references/` (repo-B) — add `references/mprr.md` with the R2 admission statement
- Verify: repo-B gate suite + instruction-lint

- [ ] **Step 1:** Add to repo-B `SKILL.md` a section documenting the MPRR subcommands (`scripts/mprr_run.py plan|integrate|reaudit`), the file-level conflict rule, the gate ladder, and that every quoted command answers `--help`. (R2 admission: the signal MPRR makes visible = "which redundancy findings are safely auto-remediable in parallel"; why no existing component hosts it = the wave/synthesizer are advisory-only; sunset = fold non-redundancy lanes in SP15.)

- [ ] **Step 2:** Create `references/mprr.md` capturing the spec §3 locked decisions + the gate ladder table verbatim so the instruction layer is self-describing.

- [ ] **Step 3:** Run instruction-lint + the repo-B gate suite:

Run: `python scripts/run_diagnosis_wave.py --help && pytest -q`
Expected: help prints; full suite PASS.

- [ ] **Step 4:** Run the family's instruction-lint gate (the SP13 X1.1 gate) against repo-B and confirm 0 findings for the new sections.

Run: (the repo-A instruction-lint command per its SKILL.md) — Expected: 0 new findings.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md references/mprr.md
git commit -m "docs(mprr): SKILL.md remediation track + R2 admission reference; instruction-lint green"
```

---

# Part II — the orchestrator runtime

### Task 11: write `SP14-LAUNCH-PROMPT.md` (the launch key)

**Files:**
- Create: repo-A `docs/superpowers/SP14-LAUNCH-PROMPT.md`

- [ ] **Step 1:** Write the file with the exact block below (≤3900 chars in the fenced block, mirroring the SP12 launch-key format). The orchestrator pastes the fenced block into a fresh unattended session.

````markdown
# SP14 Launch Prompt — massively-parallel redundancy remediation — paste as the orchestrator's goal

Paste the block below into a fresh **Claude Opus 4.8** orchestrator session started
inside `/home/jakub/projects/repo-audit-skills`, approvals disabled. It is only a
launch key: all detail lives in the plan, which the orchestrator must read in full.
Do NOT launch while any other loop is writing these repos.

---

```
You are the ORCHESTRATOR (Claude Opus 4.8, UNATTENDED, approvals disabled) for SP14,
the massively-parallel redundancy-remediation loop of the repo-audit skill family,
in /home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY — read IN FULL before acting:
docs/superpowers/plans/2026-06-13-sp14-massively-parallel-redundancy-remediation.md
and its spec docs/superpowers/specs/2026-06-13-sp14-massively-parallel-redundancy-remediation-design.md.
Contracts L-0..L-10, design rules R1/R5/R6/R7, the gate ladder, and the DoD are
FROZEN there. Where this prompt and the plan differ, the plan wins.

ENTRY: SP13 must be terminal (v0.6.0, ledgers closed). Re-verify the three mains
are clean + CI-green with no live worker; ledgers are truth. Bootstrap probe green.
Build Part I FIRST (the MPRR engine in repo-B) via worker packets, suite green +
reinstalled, before any remediation iteration.

YOUR HANDS ARE WORKERS (L-3): you NEVER edit or read source. All edits happen in
worker sessions inside git worktrees (/tmp/sp14/<repo>-<iter>-<slug>). PRIMARY route
= native Opus subagents (Agent tool, run_in_background, isolation=worktree);
ALTERNATIVE = opencode-worker-bridge; infra failure switches that packet once
(logged). You read ONLY status.json + gate tails (<=40 lines) + findings/KPI JSON,
re-derive every gate yourself, and a worker's green is NEVER evidence.

THE ENGINE IS THE BRAIN, YOU ARE THE PUMP. Per iteration, per target repo:
1. Run the redundancy lanes (duplication-audit, dead-code-audit, test-redundancy
   -triage) -> findings.json + triage.json.
2. `python scripts/mprr_run.py reaudit --findings findings.json --triage triage.json`
   -> residual count. If 0, this repo has CONVERGED (no new issues to resolve).
3. Else `mprr_run.py plan --run-dir RD --findings ... --ceiling N` -> dispatch the
   emitted disjoint packets as workers (file-level conflict-free, so merges are
   clean by construction). Keep the pool SATURATED at ceiling N: as each worker
   returns, immediately `mprr_run.py integrate --packet-id P --evidence E.json
   --diff-files ... --repo R --branch B`, then `plan` again to refill freed slots.
4. integrate enforces the GATE LADDER (mechanical: tests+reaudit; refactor:
   mutation>=0.80+reaudit; test_removal: coverage+mutation parity at HIGH confidence
   only) and asserts every merge is conflict-free. A reported merge conflict =
   InvariantViolation = HARD STOP + escalate (partitioner/worker bug), never a
   manual resolve. A worker diff touching an undeclared file = discard.
5. On pool drain: local full gate + fresh-clone sim -> ONE batched push -> CI watch.
   Reinstall if leaf behavior changed. Mine KPIs (mprr_run events -> mine_mprr_kpis):
   merge-conflict-rate MUST be 0.

CONVERGENCE (the goal predicate — keep running until this holds for ALL repos):
a full re-audit pass finds NO new redundancy issues to resolve — every finding is
either remediated, or documented residue (SP12-justified intrinsic clone), or
deferred-hard (a fix that cannot reach its gate, e.g. an EXTRACT below mutation 0.80
or a test-merge below HIGH confidence). Per L-1: each iteration every ACTIVE repo
shrinks its residual count >=1 or takes a strike; two strikes -> TERMINAL with
documented residue. HARD CAP 12 iterations. Never suppress a real finding to force
convergence; never game the gate ladder.

TERMINALS (L-9): DONE = every repo converged/terminal, DoD met, repo-B released +
reinstalled, CI green. BLOCKED = cap hit / two strikes / second CI red / invariant
violation, with a complete ledger. Both are honest outcomes.

BINDING LESSONS (carried): fresh-clone sim before ANY push; never trust a piped exit
code — read the gate JSON; the engine's disjoint-file invariant is load-bearing — a
nonzero merge-conflict-rate is a STOP, not a retry; KPIs are mined, never typed (R5);
the engine never edits leaf finding-emission logic (R6).

LEDGER: docs/self-audit/2026-06-sp14-mprr-loop.md, appended once per iteration:
installed versions, residual counts before/after per repo, packets dispatched/merged/
discarded/deferred-hard, worker run dirs, the mined MPRR KPI row (pool utilization,
peak/mean concurrency, merge-conflict-rate=0, rows/hr), ship evidence, growth-
allowance table, TERMINAL declarations.
```

---
````

- [ ] **Step 2:** Verify the fenced block is ≤3900 chars:

Run: `awk '/^```$/{f=!f;next} f{c+=length($0)+1} END{print c}' docs/superpowers/SP14-LAUNCH-PROMPT.md`
Expected: a number ≤ 3900.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/SP14-LAUNCH-PROMPT.md
git commit -m "docs(sp14): orchestrator launch prompt — converge-until-no-new-issues"
```

---

### Task 12: pre-launch checklist + universe freeze

- [ ] **Step 1:** Re-verify entry state: `git -C ~/projects/repo-audit-skills status`, repo-B, repo-P all clean + CI-green; no live worker.
- [ ] **Step 2:** Prune stale `/tmp/sp1*` worktrees and artifacts; `git worktree prune` in each repo.
- [ ] **Step 3:** Confirm opencode-worker-bridge answers a probe.
- [ ] **Step 4:** Confirm Part I is shipped: repo-B `pytest -q` green, MPRR modules reinstalled into `~/.claude/skills` → `~/.agents/skills`, bootstrap probe green.
- [ ] **Step 5:** Freeze: the redundancy-lane finding universe is the convergence target; any NEW finding class/lane/metric discovered mid-run goes to `docs/superpowers/SP15-CANDIDATES.md`, never into this run (L-1). Commit the (empty) SP15-CANDIDATES.md stub.

```bash
git add docs/superpowers/SP15-CANDIDATES.md
git commit -m "chore(sp14): freeze — open SP15 candidate overflow, ready to launch"
```

---

## Definition of Done (falsifiable — from spec §8)

1. ✅ Partitioner property-proven conflict-free (`test_mprr_schedule.py` invariant test, 200 examples).
2. ✅ ≥1 real iteration ran **N ≥ 8** workers concurrently with **merge-conflict-rate = 0** (mined via `mine_mprr_kpis`, in the ledger).
3. ✅ The **142-MERGE triage backlog** acted on — merged-or-deferred-hard — each with coverage+mutation-parity evidence at HIGH confidence.
4. ✅ Ran unattended end-to-end on a **family repo AND ≥1 foreign repo** (chosen at launch).
5. ✅ Gate ladder enforced per class (a `refactor` with mutation <0.80 cannot merge — `test_mprr_gate.py`).
6. ✅ KPI miner records pool utilization, merge-conflict-rate (=0), rows/hr; ledger appended per iteration (L-10).
7. ✅ Family repos terminal-with-documented-residue, CI green, **repo-B released + reinstalled + readback/probe green**.

## Self-review notes (spec coverage)

- Spec §4.2 components 1-8 → Tasks 1-8 (normalize, partition, schedule, packets, route is the orchestrator's worker dispatch in Part II, integrator, convergence controller = the loop in Task 11, KPI miner).
- Spec §5 invariant + gate ladder → Tasks 3 (invariant), 5 (merge assertion + scope), 4 (ladder).
- Spec §6 failure modes → Task 5 (InvariantViolation), Task 7 (discard/release on gate fail), Task 11 (CI red / route switch).
- Spec §7 convergence + §8 DoD → Task 11 prompt + the DoD section above.
- Spec §10 testing → Tasks 2/3 property tests, Task 9 fixtures (incl. non-Python R1), Task 7 dry-run via `plan`.
- Spec §9 non-goals (region/symbol conflict, across-repo, multi-language) → explicitly out; SP15-CANDIDATES.md (Task 12).
- Open at launch (not blockers): concrete ceiling **N** (start 8, raise per pool-utilization KPI) and the foreign repo for DoD #4.
