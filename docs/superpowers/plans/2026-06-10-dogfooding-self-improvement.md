# Dogfooding Self-Improvement Run — Implementation Plan (Sub-project 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make `repo-audit-skills` deterministic and hardened (Phase 0), then run a bounded loop that refactors the package's own code against its own audit until the actionable finding set is empty (Phase 1).

**Architecture:** Phase 0 is mostly a **sequential** chain of mechanical source edits (they touch overlapping files) plus a few parallelizable test-only/disjoint tasks; it ends by freezing a machine-portable, production-scoped self-audit baseline. Phase 1 is a data-driven loop where each round either fixes or justifiably-freezes each selected finding, so the actionable set strictly shrinks to a fixpoint. Golden tests are the invariant: a refactor may change structure but never a tool's findings on given input.

**Tech Stack:** Python (tools + gates), Node (jscpd, installer, release gate), pytest, npm, ruff.

**Spec:** `docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md`

**Environment:** `. .venv/bin/activate`; node >=18. Run leaf tests from each skill dir; root tests from repo root.

**Pinned versions (this env):** lizard 1.23.0, radon 6.0.1, vulture 2.16, ruff 0.15.5, mypy 2.1.0, jscpd 5.0.5.

**Dry-run baseline reality (informs Phase 1 sizing):** the pre-remediation self-audit reports ~611 findings — 128 on test fixtures (excluded by Task 9 scoping), ~400 auto-fixable LINT/FORMAT (cleared by Task 8), leaving a tractable residual for the loop.

---

## Task ordering / overlap notes (for the orchestrator)

Source-editing tasks overlap on files and **serialize**: Task 1 and Task 2 both edit
`duplication_audit.py`; Tasks 2 and 4 both edit `quality_audit.py`/`dead_code_audit.py`; Task 8
reformats them all. Run the source chain **1 → 2 → 3 → 4 → 8**. The test-only/disjoint tasks
(**5** adversarial, **6** idempotence, **7** test-audit segregation, **10** advisory) only add
files or touch `test-audit-pipeline`, so they can run alongside the chain. **Task 9 is last**
(baseline must reflect the pinned/normalized/hardened/bulk-remediated package).

---

# PHASE 0 — Safety net

## Task 1: Pin tool versions + lockfile jscpd

**Files:** `skills/*/pyproject.toml`; root `package.json` + `package-lock.json`; `skills/duplication-audit/scripts/duplication_audit.py:45-53`

- [ ] **Step 1: Pin Python tool versions to `==`**

In each leaf `pyproject.toml`, change `>=` to `==`: complexity → `radon==6.0.1`, `lizard==1.23.0`;
dead-code → `vulture==2.16`, `ruff==0.15.5`; quality → `ruff==0.15.5`, `mypy==2.1.0`; duplication
and structure have no Python tool dep. Pin any `dev` `ruff`/`pytest` extras the same way.

- [ ] **Step 2: Add a pinned, lockfiled jscpd**

Run: `npm install --save-dev jscpd` — writes `devDependencies.jscpd` + `package-lock.json`. Commit both.

- [ ] **Step 3: Invoke the local jscpd binary**

In `skills/duplication-audit/scripts/duplication_audit.py` `_run_jscpd` (line ~45), replace the
`npx --yes jscpd` command head with the repo-local binary:
```python
    repo_root = Path(__file__).resolve().parents[3]
    jscpd_bin = repo_root / "node_modules" / ".bin" / "jscpd"
    cmd = [str(jscpd_bin), "--silent", "--reporters", "json", "--output", str(out_dir),
           "--min-tokens", str(thresholds["min_tokens"]), "--min-lines", str(thresholds["min_lines"]),
           *rel_files]
```
Keep the `FileNotFoundError -> ToolError` handler; update its message to mention the local binary.

- [ ] **Step 4: Verify**

Run: `cd skills/duplication-audit && python3 -m pytest tests/ -q` → pass. Then repo root: `npm run check` → three `"status": "pass"`.

- [ ] **Step 5: Commit**

```bash
git add skills/*/pyproject.toml package.json package-lock.json skills/duplication-audit/scripts/duplication_audit.py
git commit -m "build: pin audit tool versions and lockfile jscpd (determinism)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 2: Subprocess timeouts (after Task 1)

**Files:** `quality_audit.py:45,74,102`; `complexity_audit.py:93`; `duplication_audit.py:55`; `dead_code_audit.py:62,93`; `code_health_pipeline.py:104`

- [ ] **Step 1: Failing test (quality-audit representative)**

`skills/quality-audit/tests/test_quality_timeout.py`:
```python
import subprocess
import quality_audit as qa  # match the skill's existing test import style (see tests/helpers.py)

def test_timeout_maps_to_exit_error(monkeypatch, tmp_path):
    monkeypatch.setattr(qa.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("ruff", 1)))
    (tmp_path / "pkg").mkdir(); (tmp_path / "pkg" / "m.py").write_text("x=1\n")
    rc = qa.main(["--root", str(tmp_path), "--out-dir", str(tmp_path/"out"), "--source-prefix", "pkg"])
    assert rc == qa.hc.EXIT_ERROR
```

- [ ] **Step 2: Confirm it fails** — `cd skills/quality-audit && python3 -m pytest tests/test_quality_timeout.py -q` → FAIL.

- [ ] **Step 3: Add a timeout constant + handling at each site**

Add near the top of each affected script: `TOOL_TIMEOUT = 120`. Add `timeout=TOOL_TIMEOUT` to each
`subprocess.run`. In leaf scripts add `except subprocess.TimeoutExpired as exc: raise ToolError(f"<tool> timed out after {TOOL_TIMEOUT}s") from exc` next to the existing `FileNotFoundError`
handler. In the umbrella `_run_one` (`code_health_pipeline.py:104`):
```python
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=TOOL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return leaf["name"], 2, []
```

- [ ] **Step 4: Verify** — run all five code-health suites + umbrella suite → pass.

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit skills/complexity-audit/scripts skills/duplication-audit/scripts skills/dead-code-audit/scripts skills/code-health-audit-pipeline/scripts
git commit -m "harden: add subprocess timeouts mapped to EXIT_ERROR

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 3: Guard `ast.parse` in structure-audit

**Files:** `skills/structure-audit/scripts/structure_audit.py:57-71`; test `skills/structure-audit/tests/test_structure_hardening.py`

- [ ] **Step 1: Failing test**

```python
import structure_audit as sa
def test_syntax_error_file_is_skipped_not_raised(tmp_path):
    pkg = tmp_path / "pkg"; pkg.mkdir()
    (pkg / "ok.py").write_text("import os\n")
    (pkg / "bad.py").write_text("def broken(:\n    return\n")
    findings = sa.analyze_tree(str(tmp_path), ["pkg"], dict(sa.DEFAULT_THRESHOLDS))
    assert isinstance(findings, list)
```

- [ ] **Step 2: Confirm fail** — `cd skills/structure-audit && python3 -m pytest tests/test_structure_hardening.py -q` → FAIL (`SyntaxError`).

- [ ] **Step 3: Guard the parse** — in `_imported_names`:
```python
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
```

- [ ] **Step 4: Verify** — `cd skills/structure-audit && python3 -m pytest tests/ -q` → pass.

- [ ] **Step 5: Commit**

```bash
git add skills/structure-audit
git commit -m "harden: skip unparseable files in structure-audit instead of crashing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 4: Normalize finding paths to be relative to `--root` (determinism)

The `quality` and `dead-code` leaves leak absolute paths from `ruff`. Make every emitted path
relative to `--root`, mirroring `duplication_audit.py`'s existing `_rel` helper.

**Files:** `skills/quality-audit/scripts/quality_audit.py:63,84,113`; `skills/dead-code-audit/scripts/dead_code_audit.py:77,109`; tests in each skill.

- [ ] **Step 1: Failing test (quality-audit)**

`skills/quality-audit/tests/test_quality_relpaths.py`:
```python
import json, subprocess, sys
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
def test_no_absolute_paths_in_findings(tmp_path):
    pkg = tmp_path / "pkg"; pkg.mkdir(); (pkg / "m.py").write_text("import os,sys\nx =1\n")
    out = tmp_path / "out"
    subprocess.run([sys.executable, str(SKILL/"scripts"/"quality_audit.py"),
                    "--root", str(tmp_path), "--out-dir", str(out), "--source-prefix", "pkg"],
                   text=True, capture_output=True, timeout=180, check=False)
    data = json.loads((out / "quality_findings.json").read_text())
    assert data, "expected some findings"
    assert all(not f["path"].startswith("/") for f in data), [f["path"] for f in data]
```
Add the analogous `test_dead_code_relpaths.py` (script `dead_code_audit.py`, findings
`dead-code_findings.json`, fixture with an unused import + unused function).

- [ ] **Step 2: Confirm fail** — run both → FAIL (absolute paths present).

- [ ] **Step 3: Add `_rel` and wrap the emission sites**

Add to both `quality_audit.py` and `dead_code_audit.py` (identical to duplication's helper):
```python
def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()
```
Then replace each `path=Path(<x>).as_posix()` emission with `path=_rel(<x>, root)`:
- quality `_ruff_lint` (line 63): `path=_rel(item.get("filename", ""), root)`
- quality `_ruff_format` (line 84): `path=_rel(path, root)` (and rename the loop var if it shadows)
- quality `_type_findings` (line 113): `path=_rel(m.group("path"), root)`
- dead-code `_vulture_findings` (line 77): `path=_rel(m.group("path"), root)`
- dead-code `_ruff_findings` (line 109): `path = _rel(item.get("filename", ""), root)`
Ensure `root` is in scope in each function (all already receive it).

- [ ] **Step 4: Verify** — both relpath tests pass; both skills' full suites pass; `npm run check` green.

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit skills/dead-code-audit
git commit -m "determinism: emit finding paths relative to --root (no absolute leaks)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 5: Adversarial corpus + hardening meta-test (after Tasks 2,3)

**Files:** `tests/fixtures/adversarial/**`; `tests/test_adversarial_hardening.py`

- [ ] **Step 1: Build the corpus**

```bash
mkdir -p tests/fixtures/adversarial/nested/deep
: > tests/fixtures/adversarial/empty.py
printf 'def broken(:\n    return\n' > tests/fixtures/adversarial/syntax_error.py
printf '\xef\xbb\xbfimport os\n' > tests/fixtures/adversarial/bom.py
printf 'import os\n' > tests/fixtures/adversarial/ok.py
printf 'import os\n' > tests/fixtures/adversarial/nested/deep/x.py
ln -sf ok.py tests/fixtures/adversarial/link.py
```

- [ ] **Step 2: Meta-test** — `tests/test_adversarial_hardening.py`:
```python
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "adversarial"
LEAVES = ["complexity-audit/scripts/complexity_audit.py","duplication-audit/scripts/duplication_audit.py",
          "dead-code-audit/scripts/dead_code_audit.py","structure-audit/scripts/structure_audit.py",
          "quality-audit/scripts/quality_audit.py"]
def test_every_leaf_survives_adversarial_inputs(tmp_path):
    for leaf in LEAVES:
        proc = subprocess.run([sys.executable, str(ROOT/"skills"/leaf), "--root", str(CORPUS),
                               "--out-dir", str(tmp_path/leaf.split("/")[0])],
                              text=True, capture_output=True, timeout=180)
        assert proc.returncode in (0,1,2), f"{leaf} rc={proc.returncode}"
        assert "Traceback (most recent call last)" not in proc.stderr, f"{leaf}:\n{proc.stderr}"
```

- [ ] **Step 3: Run** — `python3 -m pytest tests/test_adversarial_hardening.py -q` → PASS. If a leaf tracebacks, STOP and fix its guard.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/adversarial tests/test_adversarial_hardening.py
git commit -m "test: adversarial corpus + meta-test asserting leaves never crash

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 6: Per-tool idempotence tests (after Task 4)

Run each tool twice on its frozen `tests/fixtures/dirty` corpus; assert byte-identical findings.

**Files:** one `test_*_idempotent.py` per code-health skill + umbrella.

- [ ] **Step 1: Canonical pattern (complexity-audit)** — `skills/complexity-audit/tests/test_complexity_idempotent.py`:
```python
import subprocess, sys
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL/"scripts"/"complexity_audit.py"; DIRTY = SKILL/"tests"/"fixtures"/"dirty"; FINDINGS="complexity_findings.json"
def _run(out):
    subprocess.run([sys.executable,str(SCRIPT),"--root",str(DIRTY),"--out-dir",str(out),"--source-prefix","pkg"],
                   text=True,capture_output=True,timeout=180,check=False)
    return (out/FINDINGS).read_bytes()
def test_byte_identical_across_runs(tmp_path):
    assert _run(tmp_path/"a") == _run(tmp_path/"b")
```

- [ ] **Step 2: Apply with substitutions**

| skill | SCRIPT | FINDINGS | DIRTY | args |
|---|---|---|---|---|
| duplication | `duplication_audit.py` | `duplication_findings.json` | its `tests/fixtures/dirty` | `--source-prefix pkg` |
| dead-code | `dead_code_audit.py` | `dead-code_findings.json` | its `tests/fixtures/dirty` | `--source-prefix pkg` |
| structure | `structure_audit.py` | `structure_findings.json` | its `tests/fixtures/dirty` | `--source-prefix pkg` |
| quality | `quality_audit.py` | `quality_findings.json` | its `tests/fixtures/dirty` | `--source-prefix pkg` |
| umbrella | `code_health_pipeline.py` | `code_health_summary.json` | `skills/structure-audit/tests/fixtures/dirty` | `--source-prefix pkg` |

- [ ] **Step 3: Run all six** → pass. A failure means non-determinism — STOP and locate the volatile field.

- [ ] **Step 4: Commit**

```bash
git add skills/*/tests/test_*idempotent.py
git commit -m "test: per-tool idempotence (byte-identical findings across runs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 7: Segregate volatile metadata in test-audit

**Files:** `skills/test-audit-pipeline/scripts/audit_pipeline.py` (summary assembly); test `skills/test-audit-pipeline/tests/test_audit_pipeline_meta.py`

- [ ] **Step 1: Locate the summary-assembly site**

Read `audit_pipeline.py`; find the `now = datetime.now(timezone.utc)` use (~line 272), the
`json.dump(s)` that writes the summary, and any per-stage `runtime_ms`. Identify (or extract) a
pure `build_summary(stage_results, findings) -> dict`. Note its real signature for the test.

- [ ] **Step 2: Failing test** — `tests/test_audit_pipeline_meta.py`:
```python
import importlib.util
from pathlib import Path
SCRIPT = Path(__file__).resolve().parents[1]/"scripts"/"audit_pipeline.py"
spec = importlib.util.spec_from_file_location("audit_pipeline", SCRIPT)
ap = importlib.util.module_from_spec(spec); spec.loader.exec_module(ap)
def test_canonical_summary_has_no_wallclock_or_timing():
    summary = ap.build_summary({}, [])  # signature per Step 1
    canonical = {k:v for k,v in summary.items() if k != "meta"}
    blob = repr(canonical)
    assert "UTC" not in blob and "runtime_ms" not in blob and "generated_at" not in blob
    assert "generated_at" in summary["meta"]
```

- [ ] **Step 3: Confirm fail** — `cd skills/test-audit-pipeline && python3 -m pytest tests/test_audit_pipeline_meta.py -q` → FAIL.

- [ ] **Step 4: Segregate** — route `now` and any `runtime_ms` into a `meta` key:
`{"supervisor":..., "stages": <no runtime_ms>, "findings":..., "meta": {"generated_at": now, "runtimes_ms": {...}}}`.
The report may print the timestamp from `meta`; the canonical body must contain neither.

- [ ] **Step 5: Verify** — `cd skills/test-audit-pipeline && python3 -m pytest tests/ -q` → pass.

- [ ] **Step 6: Commit**

```bash
git add skills/test-audit-pipeline
git commit -m "determinism: segregate timestamps/runtimes into a meta block

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 8: Bulk remediation of auto-fixable findings (after Tasks 1-4)

Clear the auto-fixable LINT/FORMAT majority with `ruff` so the frozen baseline is small. Behavior
is guarded by every existing test + the Task 6 golden tests.

**Files:** all production scripts under `skills/*/scripts/*.py`, `shared/health_common.py`, `scripts/*.py`. **Never touch `tests/fixtures/**`.**

- [ ] **Step 1: Confirm green before**

Run: `npm run check` → pass. Capture the current full suite green: run each skill's tests.

- [ ] **Step 2: Auto-fix lint, then format (production scripts only)**

Run (repo root, venv active):
```bash
TARGETS=$(git ls-files 'skills/*/scripts/*.py' 'shared/*.py' 'scripts/*.py')
ruff check --fix --select E,W,F,B,SIM,UP --ignore F401,F811,F841,C901 $TARGETS
ruff format $TARGETS
```

- [ ] **Step 3: Re-vendor `health_common.py` if `shared/health_common.py` changed**

```bash
for d in complexity-audit duplication-audit dead-code-audit structure-audit quality-audit; do
  cp shared/health_common.py "skills/$d/scripts/health_common.py"
done
```
(Keeps the five copies byte-identical so `check:vendored` stays green.)

- [ ] **Step 4: Verify nothing broke**

Run: every skill's pytest suite + root `tests/` + `npm run check`. All must pass — including the
idempotence/golden tests (proving the reformat did not change any tool's output contract). If any
test fails, revert that file's reformat and STOP.

- [ ] **Step 5: Commit**

```bash
git add skills shared scripts
git commit -m "style: bulk ruff --fix + format on production scripts (own-dogfood cleanup)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 9: Self-audit harness + ratchet gate (LAST; freeze baseline post-bulk)

**Files:** Create `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/self_audit_baseline.json`, `scripts/self_audit_frozen.md`; modify `package.json`, `scripts/check_release.py`, `.gitignore`.

- [ ] **Step 1: `scripts/self_audit.py` (production-scoped, normalized snapshot)**

```python
#!/usr/bin/env python3
"""Run the code-health pipeline over this package's PRODUCTION code; emit a normalized snapshot."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT/"skills"/"code-health-audit-pipeline"/"scripts"/"code_health_pipeline.py"
SNAPSHOT = ROOT/"scripts"/"self_audit_snapshot.json"

def _prefixes() -> list[str]:
    pres = ["shared", "scripts"]
    for d in sorted((ROOT/"skills").iterdir()):
        if (d/"scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres

def run(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(PIPELINE), "--root", str(ROOT), "--out-dir", str(out_dir)]
    for p in _prefixes():
        cmd += ["--source-prefix", p]
    subprocess.run(cmd, text=True, capture_output=True, timeout=600, check=False)
    summary = json.loads((out_dir/"code_health_summary.json").read_text())
    return sorted(
        ({"leaf": f["leaf"], "path": f["path"], "symbol": f["location"]["symbol"],
          "metric": f["metric"]["name"]} for f in summary.get("findings", [])),
        key=lambda d: (d["path"], d["leaf"], d["metric"], d["symbol"]))

def main() -> int:
    findings = run(ROOT/".self_audit_out")
    SNAPSHOT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "count": len(findings)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Confirm scoping excludes tests**

Run: `python3 scripts/self_audit.py && python3 -c "import json;d=json.load(open('scripts/self_audit_snapshot.json'));assert not any('/tests/' in x['path'] for x in d), 'tests leaked';print('scoped ok, count',len(d))"`
Expected: `scoped ok, count <N>` with no `/tests/` paths and no absolute paths.

- [ ] **Step 3: Freeze the baseline (post-bulk)**

```bash
cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json
printf '# Frozen self-audit findings (Actionability Rule)\n\nEach entry: path :: leaf/metric :: reason.\n' > scripts/self_audit_frozen.md
```

- [ ] **Step 4: `scripts/check_self_audit.py`**

```python
#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present in the baseline (regressions)."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main() -> int:
    subprocess.run([sys.executable, str(ROOT/"scripts"/"self_audit.py")],
                   text=True, capture_output=True, timeout=600, check=False)
    current = json.loads((ROOT/"scripts"/"self_audit_snapshot.json").read_text())
    baseline = json.loads((ROOT/"scripts"/"self_audit_baseline.json").read_text())
    base = {tuple(sorted(d.items())) for d in baseline}
    new = [d for d in current if tuple(sorted(d.items())) not in base]
    if new:
        print(json.dumps({"status": "fail", "new_findings": new}, indent=2)); return 1
    print(json.dumps({"status": "pass", "count": len(current), "baseline": len(baseline)}, indent=2)); return 0
if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Wire the gate**

In `package.json`: add `"check:selfaudit": "python3 scripts/check_self_audit.py"` and append
`&& npm run check:selfaudit` to `check`. Add the three new `scripts/` files to the required-files
list in `scripts/check_release.py` (`check_package`). Add `.self_audit_out/` and
`scripts/self_audit_snapshot.json` to `.gitignore`.

- [ ] **Step 6: Verify** — `npm run check` → FOUR `"status": "pass"` blocks, the last
`check:selfaudit` with `count == baseline`.

- [ ] **Step 7: Commit**

```bash
git add scripts/self_audit.py scripts/check_self_audit.py scripts/self_audit_baseline.json scripts/self_audit_frozen.md package.json scripts/check_release.py .gitignore
git commit -m "feat: production-scoped self-audit harness + ratchet gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 10: test-audit advisory (one-shot, not gated)

- [ ] **Step 1:** Create `docs/self-audit/test-audit-advisory.md`:
```markdown
# Test-audit advisory (not a gate)

    python3 skills/test-audit-pipeline/scripts/audit_pipeline.py \
      --root . --python .venv/bin/python --suite tests --out-dir /tmp/ras-test-advisory

Advisory only; not part of `npm run check`. Surfaces weak/redundant tests in the package itself.
```

- [ ] **Step 2: Commit** — `git add docs/self-audit/test-audit-advisory.md && git commit -m "docs: test-audit advisory runbook (not gated)"`

---

# PHASE 1 — Convergence loop (PROTOCOL, orchestrator-driven)

**Precondition:** Phase 0 merged; `npm run check` green with four gates; baseline frozen.

**Round (repeat, cap 8 findings/round):**
1. `python3 scripts/self_audit.py`; read the ranked `code_health_summary.json`.
2. Select up to **8** top-ranked **ACTIONABLE** findings. *Actionable* = the finding's file is
   covered by behavior/golden tests (each code-health leaf, `shared/health_common.py`, the
   umbrella, and `scripts/` qualify; the `test-audit` scripts do NOT → freeze them).
3. One worker per finding, own worktree. The worker **either**:
   - **FIX** it structurally (reduce the flagged complexity/duplication/dead-code) with **no**
     change to the tool's output contract; **or**
   - **FREEZE** it: append a line to `scripts/self_audit_frozen.md`
     (`path :: leaf/metric :: reason`) — allowed only with a concrete reason (irreducible
     algorithm, intentional, etc.). Prefer FIX; freeze is the considered fallback.
4. **Accept** a result only if, in its worktree: `npm run check` is green AND the affected skill's
   full pytest suite (incl. idempotence/golden) passes AND the tool's fixture findings are
   unchanged. Otherwise discard.
5. Orchestrator merges accepted results; for frozen findings, the new lines went into
   `self_audit_frozen.md`; re-run `scripts/self_audit.py`; **ratchet the baseline** to the new
   snapshot (`cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json`); commit
   baseline + frozen log. Re-run `npm run check` → green.
6. Record the round's net change (fixed + frozen).

**Fixpoint / stop:**
- **Converged:** the actionable set is empty — every finding is fixed or justified-frozen.
- **Bounded:** at most **8 rounds**.
- **No-progress / oscillation:** a round that neither fixes nor freezes anything, or a repeated
  finding set → STOP and report.
- Every round ends green and committed; safe to stop at any round.

**Report:** per-round net change, final accepted-floor count, and `self_audit_frozen.md` (the
justification for every remaining finding).

---

## Definition of Done

1. `npm run check` green with FOUR gates incl. `check:selfaudit`; adversarial + idempotence +
   timeout + relpath tests pass.
2. All tool versions pinned `==`; jscpd lockfiled and invoked from `node_modules/.bin`; **every
   leaf emits only paths relative to `--root`**.
3. Every leaf exits in {0,1,2} with no traceback on the adversarial corpus; all `subprocess.run`
   carry `timeout=`.
4. Each code-health leaf + umbrella byte-identical across two runs; test-audit canonical artifact
   free of wall-clock/timing; `self_audit.py` reports no `/tests/` paths.
5. The loop reached an empty actionable set (every finding fixed or justified-frozen) or the
   8-round bound, green + committed each round; final `self_audit_baseline.json` +
   `self_audit_frozen.md` committed; run report produced.

## Out of scope (per spec)

Changing any tool's output contract; refactoring untested code (frozen instead); gating on the
test-audit pipeline; a unified top orchestrator; cross-repo work; fixing the `--exclude` no-op.
