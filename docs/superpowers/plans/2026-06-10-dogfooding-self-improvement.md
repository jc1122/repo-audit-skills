# Dogfooding Self-Improvement Run — Implementation Plan (Sub-project 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `repo-audit-skills` deterministic and hardened (Phase 0), then run a bounded, Opus-orchestrated convergence loop that refactors the package's own code against its own audit until it reaches a fixpoint (Phase 1).

**Architecture:** Phase 0 is concrete TDD tasks that build the safety net — version pinning, timeouts, guarded parsing, an adversarial corpus, per-tool idempotence tests, test-audit metadata segregation, and a ratchet self-audit gate. Tasks 1-3,5,6,8 are mutually independent (fan out across workers); Task 4 depends on 2+3; Task 7 is frozen last so the baseline reflects the hardened package. Phase 1 is a data-driven loop protocol (not a fixed task list) the orchestrator drives.

**Tech Stack:** Python (leaf tools + gate scripts), Node (jscpd, installer, release gate), pytest, npm.

**Spec:** `docs/superpowers/specs/2026-06-10-dogfooding-self-improvement-design.md`

**Environment:** activate the repo venv first — `. .venv/bin/activate` — and ensure `node >=18`. Run leaf tests from each skill dir (`cd skills/<leaf> && python3 -m pytest tests/ -v`); run root tests from the repo root.

**Pinned tool versions (this environment):** lizard 1.23.0, radon 6.0.1, vulture 2.16, ruff 0.15.5, mypy 2.1.0, jscpd 5.0.5.

---

## File map

**Phase 0 creates:**
- `package.json` devDependency `jscpd` + `package-lock.json` (Task 1)
- `tests/fixtures/adversarial/**` + `tests/test_adversarial_hardening.py` (Task 4)
- idempotence tests in each `skills/<leaf>/tests/` + `skills/code-health-audit-pipeline/tests/` (Task 5)
- `scripts/self_audit.py`, `scripts/self_audit_baseline.json`, `scripts/check_self_audit.py` (Task 7)
- `docs/self-audit/test-audit-advisory.md` + a make-style command (Task 8)

**Phase 0 modifies:**
- `skills/*/pyproject.toml` — `==` pins (Task 1)
- `skills/duplication-audit/scripts/duplication_audit.py` — local jscpd binary (Task 1)
- the eight `subprocess.run` sites — timeouts (Task 2)
- `skills/structure-audit/scripts/structure_audit.py` — guarded `ast.parse` (Task 3)
- `skills/test-audit-pipeline/scripts/audit_pipeline.py` (+ triage) — metadata segregation (Task 6)
- `package.json` scripts + `scripts/check_release.py` REQUIRED files — wire `check:selfaudit` (Task 7)

**Not touched:** the migrated test-audit skills' analysis logic (lift-and-shift; only the
report serialization in Task 6 changes), any tool's output contract (golden tests enforce this).

---

# PHASE 0 — Safety net

## Task 1: Pin tool versions (determinism)

**Files:**
- Modify: `skills/complexity-audit/pyproject.toml`, `skills/duplication-audit/pyproject.toml`, `skills/dead-code-audit/pyproject.toml`, `skills/quality-audit/pyproject.toml`, `skills/structure-audit/pyproject.toml`
- Create: root `package.json` devDependency + `package-lock.json`
- Modify: `skills/duplication-audit/scripts/duplication_audit.py:45-53`

- [ ] **Step 1: Pin Python tool versions to `==`**

In each leaf `pyproject.toml`, change the `dependencies` `>=` specifiers to `==` at the pinned
versions. Example for `skills/complexity-audit/pyproject.toml`:
```toml
dependencies = [
    "radon==6.0.1",
    "lizard==1.23.0",
]
```
Apply the matching pins per skill: duplication-audit has no Python tool dep (jscpd is Node);
dead-code-audit → `vulture==2.16`, `ruff==0.15.5`; quality-audit → `ruff==0.15.5`,
`mypy==2.1.0`; structure-audit → none (stdlib only). Pin any `dev` extras' `ruff`/`pytest`
the same way if present.

- [ ] **Step 2: Add a pinned, lockfiled jscpd**

Run:
```bash
npm install --save-dev jscpd
```
This writes `jscpd` into the root `package.json` `devDependencies` and records the exact
resolved version in `package-lock.json`. Commit both — the lockfile is the determinism anchor.

- [ ] **Step 3: Make duplication-audit invoke the local jscpd binary (failing check first)**

Run the existing duplication tests to confirm the current `npx --yes` path works:
`cd skills/duplication-audit && python3 -m pytest tests/ -q` → expect pass. Then change the
command builder in `skills/duplication-audit/scripts/duplication_audit.py` (`_run_jscpd`, line
~45) from the `npx --yes jscpd` invocation to the repo-local binary:
```python
    repo_root = Path(__file__).resolve().parents[3]  # skills/<leaf>/scripts -> repo root
    jscpd_bin = repo_root / "node_modules" / ".bin" / "jscpd"
    cmd = [
        str(jscpd_bin), "--silent",
        "--reporters", "json", "--output", str(out_dir),
        "--min-tokens", str(thresholds["min_tokens"]),
        "--min-lines", str(thresholds["min_lines"]),
        *rel_files,
    ]
```
Keep the existing `FileNotFoundError -> ToolError("...jscpd...")` handling; update its message to
mention the local binary.

- [ ] **Step 4: Verify duplication still works against the pinned binary**

Run: `cd skills/duplication-audit && python3 -m pytest tests/ -q`
Expected: pass (same clone findings as before; behavior unchanged).

- [ ] **Step 5: Verify the package gate is still green**

Run (repo root): `npm run check`
Expected: three `"status": "pass"` blocks.

- [ ] **Step 6: Commit**

```bash
git add skills/*/pyproject.toml package.json package-lock.json skills/duplication-audit/scripts/duplication_audit.py
git commit -m "build: pin all audit tool versions and lockfile jscpd (determinism)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 2: Add subprocess timeouts (hardening)

Eight `subprocess.run` sites lack timeouts. Map a timeout to the existing error path so a hung
tool yields a clean `EXIT_ERROR` (2) instead of hanging.

**Files:**
- Modify: `skills/quality-audit/scripts/quality_audit.py:45,74,102`
- Modify: `skills/complexity-audit/scripts/complexity_audit.py:93`
- Modify: `skills/duplication-audit/scripts/duplication_audit.py:55`
- Modify: `skills/dead-code-audit/scripts/dead_code_audit.py:62,93`
- Modify: `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py:104`

- [ ] **Step 1: Write a failing timeout test (quality-audit as the representative)**

Create `skills/quality-audit/tests/test_quality_timeout.py`:
```python
import subprocess, sys, json, pathlib
import quality_audit as qa  # sys.path is set by conftest/helpers as in existing tests

def test_timeout_maps_to_exit_error(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="ruff", timeout=1)
    monkeypatch.setattr(qa.subprocess, "run", boom)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("x=1\n")
    rc = qa.main(["--root", str(tmp_path), "--out-dir", str(tmp_path/"out"), "--source-prefix", "pkg"])
    assert rc == qa.hc.EXIT_ERROR
```
(Match the import style of the skill's existing tests — see `skills/quality-audit/tests/helpers.py`.)

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd skills/quality-audit && python3 -m pytest tests/test_quality_timeout.py -q`
Expected: FAIL — `TimeoutExpired` currently propagates, not mapped to `EXIT_ERROR`.

- [ ] **Step 3: Add a timeout constant + handling at each site**

In each affected script, add near the top (after imports):
```python
TOOL_TIMEOUT = 120  # seconds; a tool exceeding this is treated as a hard error
```
Then add `timeout=TOOL_TIMEOUT` to each `subprocess.run(...)` call, and convert a timeout to the
script's error path. In the leaf scripts, wrap the call so `TimeoutExpired` raises the local
`ToolError` (already mapped to `EXIT_ERROR` by `main`). Pattern (quality-audit `_ruff_lint`):
```python
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True,
                              check=False, timeout=TOOL_TIMEOUT)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"ruff timed out after {TOOL_TIMEOUT}s") from exc
```
Apply the same `except subprocess.TimeoutExpired -> ToolError(...)` to the other leaf sites
(quality 74/102, complexity 93, duplication 55, dead-code 62/93). For the umbrella
(`code_health_pipeline.py:104`, inside `_run_one`), add `timeout=TOOL_TIMEOUT` and:
```python
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=TOOL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return leaf["name"], 2, []
```

- [ ] **Step 4: Confirm the timeout test passes and suites stay green**

Run:
```bash
cd skills/quality-audit && python3 -m pytest tests/ -q
cd ../complexity-audit && python3 -m pytest tests/ -q
cd ../duplication-audit && python3 -m pytest tests/ -q
cd ../dead-code-audit && python3 -m pytest tests/ -q
cd ../code-health-audit-pipeline && python3 -m pytest tests/ -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit skills/complexity-audit/scripts skills/duplication-audit/scripts \
        skills/dead-code-audit/scripts skills/code-health-audit-pipeline/scripts
git commit -m "harden: add subprocess timeouts mapped to EXIT_ERROR

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 3: Guard `ast.parse` in structure-audit (hardening)

**Files:**
- Create: `skills/structure-audit/tests/fixtures/broken/pkg/syntax_error.py`
- Modify: `skills/structure-audit/scripts/structure_audit.py:57-71` (`_imported_names`) and its caller in `build_graph`
- Test: `skills/structure-audit/tests/test_structure_hardening.py`

- [ ] **Step 1: Create an adversarial fixture**

`skills/structure-audit/tests/fixtures/broken/pkg/syntax_error.py`:
```python
def broken(:
    return
```

- [ ] **Step 2: Write the failing test**

`skills/structure-audit/tests/test_structure_hardening.py`:
```python
import structure_audit as sa  # per the skill's existing test import style

def test_syntax_error_file_is_skipped_not_raised(tmp_path):
    pkg = tmp_path / "pkg"; pkg.mkdir()
    (pkg / "ok.py").write_text("import os\n")
    (pkg / "bad.py").write_text("def broken(:\n    return\n")
    findings = sa.analyze_tree(str(tmp_path), ["pkg"], dict(sa.DEFAULT_THRESHOLDS))
    assert isinstance(findings, list)  # no exception; bad.py skipped
```

- [ ] **Step 3: Run it, confirm it fails**

Run: `cd skills/structure-audit && python3 -m pytest tests/test_structure_hardening.py -q`
Expected: FAIL — `ast.parse` raises `SyntaxError`.

- [ ] **Step 4: Guard the parse**

In `skills/structure-audit/scripts/structure_audit.py`, change `_imported_names` (line ~57) to
return `[]` on a parse/read failure rather than raising:
```python
def _imported_names(path: Path, current_module: str, is_pkg: bool) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []  # unparseable file: skip, never crash the audit
    names: list[str] = []
    ...
```
(Leave the rest of the function unchanged.)

- [ ] **Step 5: Confirm pass + suite green**

Run: `cd skills/structure-audit && python3 -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/structure-audit
git commit -m "harden: skip unparseable files in structure-audit instead of crashing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 4: Adversarial corpus + hardening meta-test (depends on Tasks 2,3)

**Files:**
- Create: `tests/fixtures/adversarial/` with `empty.py`, `syntax_error.py`, `bom.py`, `nested/deep/x.py`, and a symlink `link.py -> ok.py`, plus `ok.py`
- Create: `tests/test_adversarial_hardening.py`

- [ ] **Step 1: Build the corpus**

Run:
```bash
mkdir -p tests/fixtures/adversarial/nested/deep
: > tests/fixtures/adversarial/empty.py
printf 'def broken(:\n    return\n' > tests/fixtures/adversarial/syntax_error.py
printf '\xef\xbb\xbfimport os\n' > tests/fixtures/adversarial/bom.py
printf 'import os\n' > tests/fixtures/adversarial/ok.py
printf 'import os\n' > tests/fixtures/adversarial/nested/deep/x.py
ln -sf ok.py tests/fixtures/adversarial/link.py
```

- [ ] **Step 2: Write the meta-test**

`tests/test_adversarial_hardening.py`:
```python
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "adversarial"
LEAVES = [
    "complexity-audit/scripts/complexity_audit.py",
    "duplication-audit/scripts/duplication_audit.py",
    "dead-code-audit/scripts/dead_code_audit.py",
    "structure-audit/scripts/structure_audit.py",
    "quality-audit/scripts/quality_audit.py",
]

def test_every_leaf_survives_adversarial_inputs(tmp_path):
    for leaf in LEAVES:
        out = tmp_path / leaf.split("/")[0]
        proc = subprocess.run(
            [sys.executable, str(ROOT / "skills" / leaf),
             "--root", str(CORPUS), "--out-dir", str(out)],
            text=True, capture_output=True, timeout=180,
        )
        assert proc.returncode in (0, 1, 2), f"{leaf} returncode={proc.returncode}"
        assert "Traceback (most recent call last)" not in proc.stderr, f"{leaf} crashed:\n{proc.stderr}"
```

- [ ] **Step 3: Run it**

Run (repo root, venv active): `python3 -m pytest tests/test_adversarial_hardening.py -q`
Expected: PASS (Tasks 2+3 ensure no leaf tracebacks; exit codes are in {0,1,2}). If a leaf
tracebacks, STOP and fix that leaf's guard before continuing.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/adversarial tests/test_adversarial_hardening.py
git commit -m "test: adversarial corpus + meta-test asserting leaves never crash

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 5: Idempotence (golden) tests per tool (determinism)

Prove each tool is deterministic: two runs on a frozen fixture produce byte-identical findings
JSON. Reuse each skill's existing `tests/fixtures/dirty` corpus.

**Files (one test file per skill):**
- `skills/complexity-audit/tests/test_complexity_idempotent.py`
- `skills/duplication-audit/tests/test_duplication_idempotent.py`
- `skills/dead-code-audit/tests/test_dead_code_idempotent.py`
- `skills/structure-audit/tests/test_structure_idempotent.py`
- `skills/quality-audit/tests/test_quality_idempotent.py`
- `skills/code-health-audit-pipeline/tests/test_pipeline_idempotent.py`

- [ ] **Step 1: Write the idempotence test (canonical pattern, complexity-audit shown)**

`skills/complexity-audit/tests/test_complexity_idempotent.py`:
```python
import subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "complexity_audit.py"
DIRTY = SKILL / "tests" / "fixtures" / "dirty"
FINDINGS = "complexity_findings.json"

def _run(out):
    subprocess.run([sys.executable, str(SCRIPT), "--root", str(DIRTY),
                    "--out-dir", str(out), "--source-prefix", "pkg"],
                   text=True, capture_output=True, timeout=180, check=False)
    return (out / FINDINGS).read_bytes()

def test_findings_are_byte_identical_across_runs(tmp_path):
    a = _run(tmp_path / "a"); b = _run(tmp_path / "b")
    assert a == b
```

- [ ] **Step 2: Apply the same pattern to the other five**

Use the identical structure with these substitutions (SCRIPT name, FINDINGS file, and the
umbrella's args). The findings filenames come from each leaf's `LEAF` constant; the umbrella
writes `code_health_summary.json`:

| test file | SCRIPT | FINDINGS / artifact | extra args |
|---|---|---|---|
| duplication | `duplication_audit.py` | `duplication_findings.json` | `--source-prefix pkg` |
| dead-code | `dead_code_audit.py` | `dead-code_findings.json` | `--source-prefix pkg` |
| structure | `structure_audit.py` | `structure_findings.json` | `--source-prefix pkg` |
| quality | `quality_audit.py` | `quality_findings.json` | `--source-prefix pkg` |
| umbrella | `code_health_pipeline.py` | `code_health_summary.json` | `--source-prefix pkg` |

For the umbrella, point `DIRTY` at `skills/structure-audit/tests/fixtures/dirty` (a fixture that
yields findings) and read `code_health_summary.json`. The summary embeds ranked findings; assert
byte-identical across two runs.

- [ ] **Step 3: Run all six**

Run each: `cd skills/<skill> && python3 -m pytest tests/test_*idempotent.py -q`
Expected: all pass. A failure means non-determinism — STOP and locate the volatile field
(unsorted output, embedded path absolute vs relative, timing) before continuing.

- [ ] **Step 4: Commit**

```bash
git add skills/*/tests/test_*idempotent.py
git commit -m "test: per-tool idempotence (byte-identical findings across runs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 6: Segregate volatile metadata in test-audit (determinism)

Move wall-clock + timing fields out of the canonical artifact into a `meta` block.

**Files:**
- Modify: `skills/test-audit-pipeline/scripts/audit_pipeline.py:272` (and the report/summary assembly that embeds `now` and any `runtime_ms`)
- Test: `skills/test-audit-pipeline/tests/test_audit_pipeline_meta.py` (new `tests/` dir)

- [ ] **Step 1: Locate the summary-assembly site and define the target function**

Read `skills/test-audit-pipeline/scripts/audit_pipeline.py`. Find where the emitted summary
JSON is assembled — search for the `now = datetime.now(timezone.utc)` use (line ~272), the
`json.dump`/`json.dumps` that writes the summary, and any place a per-stage `runtime_ms` is put
into output. Identify (or, if assembly is inline, extract) a pure function
`build_summary(stage_results: dict, findings: list) -> dict` that returns the full summary dict.
Note its real signature — the test in Step 2 must call it as it actually exists.

- [ ] **Step 2: Write the failing serialization test**

`skills/test-audit-pipeline/tests/test_audit_pipeline_meta.py` (adjust the `build_summary(...)`
call to the signature confirmed in Step 1):
```python
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_pipeline.py"
spec = importlib.util.spec_from_file_location("audit_pipeline", SCRIPT)
ap = importlib.util.module_from_spec(spec); spec.loader.exec_module(ap)

def test_canonical_summary_has_no_wallclock_or_timing():
    summary = ap.build_summary({}, [])  # signature per Step 1
    canonical = {k: v for k, v in summary.items() if k != "meta"}
    blob = repr(canonical)
    assert "UTC" not in blob and "runtime_ms" not in blob and "generated_at" not in blob
    assert "generated_at" in summary["meta"]
```

- [ ] **Step 3: Run it, confirm it fails**

Run: `cd skills/test-audit-pipeline && python3 -m pytest tests/test_audit_pipeline_meta.py -q`
Expected: FAIL (timestamp currently embedded in the canonical body, or no `meta` block).

- [ ] **Step 4: Segregate metadata**

Refactor `build_summary` so the wall-clock `now` and any per-stage `runtime_ms` go into a
dedicated `meta` key, leaving the findings/scores body free of wall-clock and timing:
`{"supervisor": ..., "stages": <without runtime_ms>, "findings": ..., "meta": {"generated_at": now, "runtimes_ms": {...}}}`.
The human-readable report may still *print* the timestamp by reading it from `meta`, but the
canonical JSON body (everything outside `meta`) must contain neither timestamps nor runtimes.

- [ ] **Step 5: Confirm pass**

Run: `cd skills/test-audit-pipeline && python3 -m pytest tests/ -q`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add skills/test-audit-pipeline
git commit -m "determinism: segregate timestamps/runtimes into a meta block

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 7: Self-audit harness + ratchet gate (freeze baseline LAST)

Run only after Tasks 1-6 are merged, so the baseline reflects the pinned/hardened/deterministic
package.

**Files:**
- Create: `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/self_audit_baseline.json`
- Modify: `package.json` (scripts), `scripts/check_release.py` (required files list), `README.md`

- [ ] **Step 1: Write `scripts/self_audit.py`**

```python
#!/usr/bin/env python3
"""Run the code-health pipeline over this package's own source; emit a normalized snapshot."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "skills" / "code-health-audit-pipeline" / "scripts" / "code_health_pipeline.py"
SNAPSHOT = ROOT / "scripts" / "self_audit_snapshot.json"

def run(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(PIPELINE), "--root", str(ROOT),
                    "--source-prefix", "skills", "--source-prefix", "shared",
                    "--source-prefix", "scripts", "--out-dir", str(out_dir)],
                   text=True, capture_output=True, timeout=600, check=False)
    summary = json.loads((out_dir / "code_health_summary.json").read_text())
    # normalized, comparable finding identities (drop volatile ranking score)
    return sorted(
        {"leaf": f["leaf"], "path": f["path"], "symbol": f["location"]["symbol"],
         "metric": f["metric"]["name"]} for f in summary.get("findings", [])
        , key=lambda d: (d["path"], d["leaf"], d["metric"], d["symbol"]))

def main() -> int:
    findings = run(ROOT / ".self_audit_out")
    SNAPSHOT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "count": len(findings)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Freeze the initial baseline**

Run:
```bash
python3 scripts/self_audit.py
cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json
```
This captures the current self-audit findings as the accepted floor.

- [ ] **Step 3: Write `scripts/check_self_audit.py`**

```python
#!/usr/bin/env python3
"""Fail if the current self-audit has findings NOT present in the baseline (regressions)."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "self_audit.py")],
                   text=True, capture_output=True, timeout=600, check=False)
    current = json.loads((ROOT / "scripts" / "self_audit_snapshot.json").read_text())
    baseline = json.loads((ROOT / "scripts" / "self_audit_baseline.json").read_text())
    base_set = {tuple(sorted(d.items())) for d in baseline}
    new = [d for d in current if tuple(sorted(d.items())) not in base_set]
    if new:
        print(json.dumps({"status": "fail", "new_findings": new}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "count": len(current), "baseline": len(baseline)}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Wire the gate into `npm run check`**

In `package.json`, add `"check:selfaudit": "python3 scripts/check_self_audit.py"` and append it
to `check`:
```json
    "check": "npm run check:vendored && npm run check:fixtures && npm run check:release && npm run check:selfaudit",
    "check:selfaudit": "python3 scripts/check_self_audit.py",
```
Add `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/self_audit_baseline.json`
to the required-files list in `scripts/check_release.py` (`check_package`). Add `.self_audit_out/`
and `scripts/self_audit_snapshot.json` to `.gitignore`.

- [ ] **Step 5: Verify the full gate is green**

Run: `npm run check`
Expected: four `"status": "pass"` blocks, the last being `check:selfaudit` with
`count == baseline`.

- [ ] **Step 6: Commit**

```bash
git add scripts/self_audit.py scripts/check_self_audit.py scripts/self_audit_baseline.json \
        package.json scripts/check_release.py .gitignore README.md
git commit -m "feat: self-audit harness + ratchet gate (check:selfaudit)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

## Task 8: test-audit advisory (one-shot, not gated)

**Files:**
- Create: `docs/self-audit/test-audit-advisory.md`

- [ ] **Step 1: Document the advisory command**

Create `docs/self-audit/test-audit-advisory.md` describing how to run the test-audit pipeline
over the package's own tests and where the report lands:
```markdown
# Test-audit advisory (not a gate)

Run the test-audit pipeline over this package's own tests for a test-quality/redundancy signal:

    python3 skills/test-audit-pipeline/scripts/audit_pipeline.py \
      --root . --python .venv/bin/python --suite tests --out-dir /tmp/ras-test-advisory

This is advisory only; it is not part of `npm run check`. Use it to spot weak or redundant
tests in the package itself.
```

- [ ] **Step 2: Commit**

```bash
git add docs/self-audit/test-audit-advisory.md
git commit -m "docs: test-audit advisory runbook (not gated)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE 1 — Convergence loop (PROTOCOL, not fixed tasks)

Phase 1 is data-driven: the work each round depends on what the self-audit reports, so it is a
loop the **orchestrator** drives, not a static task list. The orchestrator prompt
(`docs/superpowers/DOGFOOD-ORCHESTRATOR-PROMPT.md`) encodes this; the protocol is recorded here
as the source of truth.

**Precondition:** Phase 0 fully merged; `npm run check` green including `check:selfaudit`;
baseline committed.

**Round algorithm (repeat):**
1. `python3 scripts/self_audit.py` → current findings (also read the ranked
   `code_health_summary.json` for ordering).
2. Select the top-ranked **ACTIONABLE** findings, capped at **4 per round**. *Actionable* =
   the finding's file is covered by behavior/golden tests that would catch a regression
   (every `skills/<code-health-leaf>/`, `shared/health_common.py`, the umbrella, and
   `scripts/` are covered; the test-audit `scripts/` are NOT — those findings are frozen).
3. Dispatch one worker per selected finding, each in its own git worktree, to fix it
   **structurally** (reduce the flagged complexity/duplication/dead-code) without changing any
   tool's output contract.
4. **Accept criterion (per worker):** the change is accepted only if, in its worktree,
   `npm run check` is green AND the affected skill's full pytest suite (incl. its idempotence +
   golden tests) passes AND the tool's findings on its fixtures are unchanged. Otherwise discard.
5. Orchestrator merges accepted fixes (disjoint files → clean), re-runs `scripts/self_audit.py`,
   and **ratchets the baseline down**: `cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json`;
   commit the new baseline. Re-run `npm run check` → must be green.
6. Record this round's **net reduction** (baseline count before − after).

**Stop conditions (fixpoint at ratchet floor):**
- **Converged:** a round yields **zero accepted reductions** while gates are green, idempotence
  holds, and the adversarial corpus is clean. Freeze the current baseline as final.
- **Bounded:** at most **6 rounds**.
- **No-progress / oscillation:** if a round's net reduction is zero, or the finding set repeats a
  prior round, stop and report — do not thrash.
- Every round ends green and committed, so the run is safe to stop at any point.

**Report at end:** per-round net reductions, the final accepted-floor count, and a one-line
justification for each remaining (frozen) finding (e.g. "irreducible cyclomatic complexity in
Tarjan SCC", "test-audit script — no behavior tests, frozen by Actionability Rule").

---

## Definition of Done

1. `npm run check` green with **four** gates incl. `check:selfaudit`; adversarial + idempotence
   + timeout tests pass.
2. All tool versions pinned `==`; jscpd lockfiled and invoked from `node_modules/.bin`.
3. Every leaf exits in {0,1,2} with no traceback across the adversarial corpus; all
   `subprocess.run` calls carry `timeout=`.
4. Each code-health leaf + umbrella is byte-identical across two runs; test-audit canonical
   artifact carries no wall-clock/timing fields.
5. The convergence loop reached a fixpoint (or the 6-round bound) with a green, committed tree
   each round; final `self_audit_baseline.json` committed; run report produced.

## Out of scope (per spec)

Changing any tool's output contract; refactoring code not covered by tests (frozen into
baseline); gating on the test-audit pipeline; a unified top orchestrator; cross-repo work.
