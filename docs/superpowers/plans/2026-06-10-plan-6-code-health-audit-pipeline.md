# Plan 6 — code-health-audit-pipeline umbrella Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `code-health-audit-pipeline` umbrella skill that discovers the leaf skills from a registry, runs them in parallel, merges and ranks their findings, and emits a supervisor decision with exit codes 0/1/2.

**Architecture:** A deterministic Python orchestrator (`code_health_pipeline.py`) reads `leaf_registry.json` (the OCP hinge: leaf → script → languages), runs the language-matching leaves in parallel (`ThreadPoolExecutor`) into isolated per-leaf out-dirs, collects each leaf's `*_findings.json`, merges + dedupes by `(path, line, metric)`, ranks by `severity × confidence ÷ effort` (effort derived heuristically from the finding's signal), and decides PASS / ADVISE / GATE. Pure logic (merge/rank/decide) is separated from subprocess orchestration so it is tested against **stubbed** leaf outputs without any real tools.

**Tech Stack:** Python 3.10+ (stdlib only), `pytest`.

**Prerequisite:** Plans 1–5 complete, `npm run check` green. Work in `/home/jakub/projects/code-health-skills`.

**Design decision (spec §6 `effort`):** The leaf `Finding` schema has no `effort` field. Rather than extend the frozen leaf schema, the umbrella derives effort from the finding's `signal` via a fixed map (DELETE/LINT/FORMAT cheap → RESTRUCTURE/DECOMPOSE expensive). Leaf contract unchanged.

---

## File Structure (this plan)

```
skills/code-health-audit-pipeline/
├─ SKILL.md
├─ LICENSE
├─ pyproject.toml
├─ scripts/
│  ├─ code_health_pipeline.py
│  └─ leaf_registry.json
├─ references/
│  ├─ finding-schema.json
│  ├─ rule-ownership.md
│  └─ prioritization.md
└─ tests/
   ├─ helpers.py
   ├─ fixtures/stub_leaf.py
   ├─ fixtures/empty_leaf.py
   ├─ fixtures/error_leaf.py
   ├─ test_pipeline_logic.py
   └─ test_pipeline_run.py
```

Modified (registry appends): `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

---

## Task 1: Scaffold the umbrella + references + registry

- [ ] **Step 1: Create dirs, LICENSE, pyproject**

Run:
```bash
mkdir -p skills/code-health-audit-pipeline/scripts skills/code-health-audit-pipeline/references skills/code-health-audit-pipeline/tests/fixtures
cp LICENSE skills/code-health-audit-pipeline/LICENSE
```

Create `skills/code-health-audit-pipeline/pyproject.toml`:
```toml
[project]
name = "code-health-audit-pipeline"
version = "0.1.0"
description = "Umbrella that runs the code-health leaves, merges/ranks findings, and emits a supervisor decision."
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```

- [ ] **Step 2: Create `scripts/leaf_registry.json`**

Create `skills/code-health-audit-pipeline/scripts/leaf_registry.json`:
```json
{
  "leaves": [
    {"name": "complexity", "skill": "complexity-audit", "script": "complexity-audit/scripts/complexity_audit.py", "languages": ["python"], "findings_file": "complexity_findings.json"},
    {"name": "duplication", "skill": "duplication-audit", "script": "duplication-audit/scripts/duplication_audit.py", "languages": ["python"], "findings_file": "duplication_findings.json"},
    {"name": "dead-code", "skill": "dead-code-audit", "script": "dead-code-audit/scripts/dead_code_audit.py", "languages": ["python"], "findings_file": "dead-code_findings.json"},
    {"name": "structure", "skill": "structure-audit", "script": "structure-audit/scripts/structure_audit.py", "languages": ["python"], "findings_file": "structure_findings.json"},
    {"name": "quality", "skill": "quality-audit", "script": "quality-audit/scripts/quality_audit.py", "languages": ["python"], "findings_file": "quality_findings.json"}
  ]
}
```

- [ ] **Step 3: Create `references/finding-schema.json`**

Create `skills/code-health-audit-pipeline/references/finding-schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Code Health Finding",
  "type": "object",
  "required": ["id", "leaf", "signal", "severity", "path", "location", "metric", "evidence", "confidence", "suggested_action"],
  "properties": {
    "id": {"type": "string"},
    "leaf": {"type": "string"},
    "signal": {"enum": ["SIMPLIFY", "DECOMPOSE", "EXTRACT", "MERGE", "DELETE", "RESTRUCTURE", "LINT", "FORMAT", "TYPE"]},
    "severity": {"enum": ["info", "low", "medium", "high"]},
    "path": {"type": "string"},
    "location": {"type": "object", "required": ["line_start", "line_end", "symbol"]},
    "metric": {"type": "object", "required": ["name", "value", "threshold"]},
    "evidence": {"type": "object", "required": ["tool", "raw"]},
    "confidence": {"enum": ["low", "medium", "high"]},
    "suggested_action": {"type": "string"}
  }
}
```

- [ ] **Step 4: Create `references/rule-ownership.md`**

Create `skills/code-health-audit-pipeline/references/rule-ownership.md`:
```markdown
# Rule Ownership (non-overlap contract)

Canonical source of truth. No tool/rule is counted by two leaves. The umbrella's
`(path, line, metric)` dedupe is only a backstop.

| Leaf | Owns | Signals |
|---|---|---|
| dead-code-audit | vulture (function/class/method/property), ruff F401/F811/F841 | DELETE |
| complexity-audit | radon mi, lizard (cc/nloc/params), ruff C901 | SIMPLIFY, DECOMPOSE |
| duplication-audit | jscpd | EXTRACT, MERGE |
| structure-audit | ast import graph (cycles, fan-in/out, layers) | RESTRUCTURE |
| quality-audit | ruff (all EXCEPT F401/F811/F841/C901), ruff format, mypy/ty | LINT, FORMAT, TYPE |
```

- [ ] **Step 5: Create `references/prioritization.md`**

Create `skills/code-health-audit-pipeline/references/prioritization.md`:
```markdown
# Prioritization

Each finding is scored `severity_weight × confidence_weight ÷ effort`, ranked descending.

- severity_weight: info 0, low 1, medium 2, high 4
- confidence_weight: low 1, medium 2, high 3
- effort (by signal): DELETE/LINT/FORMAT 1, TYPE/SIMPLIFY/MERGE 2, EXTRACT/DECOMPOSE 3,
  RESTRUCTURE 4

Ties break by `(path, line_start, signal, metric)` for determinism.

## Supervisor decision and exit codes

- `0` PASS — no findings above `info`, no gate breached.
- `1` ADVISE — advisory findings present, no gate breached.
- `2` GATE — a configured hard gate breached: any leaf errored, an import cycle is present,
  type errors exceed `max_type_errors`, or high-severity findings exceed
  `max_high_severity`. Defaults gate on leaf error and import cycle only.
```

- [ ] **Step 6: Create `SKILL.md`**

Create `skills/code-health-audit-pipeline/SKILL.md`:
```markdown
---
name: code-health-audit-pipeline
version: 0.1.0
description: >
  Umbrella that runs the code-health leaf skills (complexity, duplication, dead-code,
  structure, quality) in parallel, merges and ranks their findings into one report, and
  emits a supervisor decision with exit codes 0/1/2. Reads a leaf registry so new
  language leaves plug in without changing the orchestrator. Advisory only.
---

# code-health-audit-pipeline

## Overview

Runs the code-health leaves once, deterministically, and produces a single ranked
backlog plus a machine-readable summary with a supervisor decision.

## Quick Start

```bash
python3 scripts/code_health_pipeline.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/code-health
```

## Output

```
out-dir/
├─ code_health_report.md       # ranked backlog grouped by signal
├─ code_health_summary.json    # supervisor decision + exit_code + per-leaf rollup + findings
├─ complexity/complexity_findings.json
├─ duplication/duplication_findings.json
├─ dead-code/dead-code_findings.json
├─ structure/structure_findings.json
└─ quality/quality_findings.json
```

## Exit Codes

- `0` PASS, `1` ADVISE (findings present), `2` GATE (hard gate breached, including any
  leaf erroring).

## Configuration

- `--languages python` (default) — filters which leaves run via the registry.
- `--registry PATH` — override the leaf registry.
- `--leaf-script name=PATH` — override a single leaf's script path (repeatable).
- `--config PATH` — JSON gate overrides (`max_type_errors`, `max_high_severity`,
  `gate_on_import_cycle`, `gate_on_leaf_error`).

See `references/prioritization.md`, `references/rule-ownership.md`,
`references/finding-schema.json`.
```

- [ ] **Step 7: Commit**

```bash
git add skills/code-health-audit-pipeline
git commit -m "feat: scaffold code-health-audit-pipeline umbrella (registry, references)"
```

---

## Task 2: Core merge / rank / decide logic — TDD

**Files:** Create `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`; test `tests/test_pipeline_logic.py`.

- [ ] **Step 1: Create `tests/helpers.py`**

Create `skills/code-health-audit-pipeline/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "code_health_pipeline.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("code_health_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def finding(**kw):
    base = {
        "id": "x", "leaf": "complexity", "signal": "DELETE", "severity": "high",
        "path": "pkg/a.py", "location": {"line_start": 1, "line_end": 1, "symbol": "f"},
        "metric": {"name": "m", "value": 0, "threshold": 0},
        "evidence": {"tool": "t", "raw": ""}, "confidence": "high", "suggested_action": "y",
    }
    base.update(kw)
    return base
```

- [ ] **Step 2: Write the failing test**

Create `skills/code-health-audit-pipeline/tests/test_pipeline_logic.py`:
```python
from helpers import finding, load_module

ch = load_module()


def test_merge_dedupes_by_path_line_metric():
    a = finding(leaf="quality")
    b = finding(leaf="dead-code")  # same path/line/metric → duplicate
    merged = ch.merge_and_dedupe([a, b])
    assert len(merged) == 1


def test_rank_orders_by_score_desc():
    cheap_high = finding(signal="DELETE", severity="high", confidence="high",
                         path="pkg/a.py", metric={"name": "m1", "value": 0, "threshold": 0})
    costly_low = finding(signal="RESTRUCTURE", severity="low", confidence="low",
                         path="pkg/b.py", metric={"name": "m2", "value": 0, "threshold": 0})
    ranked = ch.rank([costly_low, cheap_high])
    assert ranked[0]["signal"] == "DELETE"


def test_decide_pass_when_no_findings():
    decision, code = ch.decide([], {"complexity": 0}, ch.DEFAULT_GATE)
    assert (decision, code) == ("PASS", 0)


def test_decide_advise_when_findings_no_gate():
    f = finding(signal="LINT", severity="low", metric={"name": "E711", "value": 0, "threshold": 0})
    decision, code = ch.decide([f], {"quality": 1}, ch.DEFAULT_GATE)
    assert (decision, code) == ("ADVISE", 1)


def test_decide_gate_on_errored_leaf():
    decision, code = ch.decide([], {"quality": 2}, ch.DEFAULT_GATE)
    assert (decision, code) == ("GATE", 2)


def test_decide_gate_on_import_cycle():
    f = finding(signal="RESTRUCTURE", metric={"name": "import_cycle_size", "value": 2, "threshold": 1})
    decision, code = ch.decide([f], {"structure": 1}, ch.DEFAULT_GATE)
    assert (decision, code) == ("GATE", 2)
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/test_pipeline_logic.py -v
```
Expected: FAIL — `code_health_pipeline.py` does not exist.

- [ ] **Step 4: Write the pipeline logic module**

Create `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`:
```python
#!/usr/bin/env python3
"""code-health-audit-pipeline: discover leaves, run in parallel, merge/rank/decide."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parents[1]  # <skills_root>/code-health-audit-pipeline/scripts -> skills root
DEFAULT_REGISTRY = HERE / "leaf_registry.json"

SEVERITY_WEIGHT = {"info": 0, "low": 1, "medium": 2, "high": 4}
CONFIDENCE_WEIGHT = {"low": 1, "medium": 2, "high": 3}
EFFORT = {
    "DELETE": 1, "LINT": 1, "FORMAT": 1,
    "TYPE": 2, "SIMPLIFY": 2, "MERGE": 2,
    "EXTRACT": 3, "DECOMPOSE": 3, "RESTRUCTURE": 4,
}

DEFAULT_GATE = {
    "gate_on_leaf_error": True,
    "gate_on_import_cycle": True,
    "max_type_errors": 1_000_000,
    "max_high_severity": 1_000_000,
}


def _dedupe_key(f: dict) -> tuple:
    return (f.get("path"), f.get("location", {}).get("line_start"), f.get("metric", {}).get("name"))


def merge_and_dedupe(findings: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for f in sorted(findings, key=_sort_key):
        seen.setdefault(_dedupe_key(f), f)
    return list(seen.values())


def _sort_key(f: dict) -> tuple:
    loc = f.get("location", {})
    return (f.get("path", ""), loc.get("line_start", 0), f.get("signal", ""), f.get("metric", {}).get("name", ""))


def score(f: dict) -> float:
    sev = SEVERITY_WEIGHT.get(f.get("severity"), 0)
    conf = CONFIDENCE_WEIGHT.get(f.get("confidence"), 1)
    effort = EFFORT.get(f.get("signal"), 2)
    return (sev * conf) / effort


def rank(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=lambda f: (-score(f), _sort_key(f)))


def decide(findings: list[dict], leaf_exit: dict[str, int], gate: dict) -> tuple[str, int]:
    errored = [n for n, code in leaf_exit.items() if code == 2]
    has_cycle = any(f.get("metric", {}).get("name") == "import_cycle_size" for f in findings)
    type_errors = sum(1 for f in findings if f.get("signal") == "TYPE")
    high = sum(1 for f in findings if f.get("severity") == "high")
    gated = (
        (gate["gate_on_leaf_error"] and errored)
        or (gate["gate_on_import_cycle"] and has_cycle)
        or type_errors > gate["max_type_errors"]
        or high > gate["max_high_severity"]
    )
    if gated:
        return "GATE", 2
    if findings:
        return "ADVISE", 1
    return "PASS", 0
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/test_pipeline_logic.py -v
```
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add skills/code-health-audit-pipeline/scripts/code_health_pipeline.py skills/code-health-audit-pipeline/tests/helpers.py skills/code-health-audit-pipeline/tests/test_pipeline_logic.py
git commit -m "feat: add umbrella merge/rank/decide logic"
```

---

## Task 3: Leaf discovery, parallel run, collect — TDD (stub leaves)

**Files:** Modify `code_health_pipeline.py` (append); create stub leaf fixtures; test `tests/test_pipeline_run.py`.

- [ ] **Step 1: Create stub leaf fixtures**

Create `skills/code-health-audit-pipeline/tests/fixtures/stub_leaf.py`:
```python
import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--root")
p.add_argument("--out-dir")
p.add_argument("--source-prefix", action="append", default=[])
a = p.parse_args()
out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)
findings = [{
    "id": "stub1", "leaf": "stub", "signal": "DELETE", "severity": "high",
    "path": "pkg/a.py", "location": {"line_start": 1, "line_end": 1, "symbol": "f"},
    "metric": {"name": "m", "value": 0, "threshold": 0},
    "evidence": {"tool": "stub", "raw": ""}, "confidence": "high", "suggested_action": "y",
}]
(out / "stub_findings.json").write_text(json.dumps(findings))
sys.exit(1)
```

Create `skills/code-health-audit-pipeline/tests/fixtures/empty_leaf.py`:
```python
import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--root")
p.add_argument("--out-dir")
p.add_argument("--source-prefix", action="append", default=[])
a = p.parse_args()
out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)
(out / "empty_findings.json").write_text("[]")
sys.exit(0)
```

Create `skills/code-health-audit-pipeline/tests/fixtures/error_leaf.py`:
```python
import json
import sys

print(json.dumps({"status": "error", "message": "simulated"}))
sys.exit(2)
```

- [ ] **Step 2: Write the failing test**

Create `skills/code-health-audit-pipeline/tests/test_pipeline_run.py`:
```python
import json
from pathlib import Path

from helpers import FIXTURES, load_module

ch = load_module()


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


def test_select_leaves_filters_by_language():
    leaves = [
        {"name": "py", "skill": "py", "script": "x", "languages": ["python"], "findings_file": "py_findings.json"},
        {"name": "c", "skill": "c", "script": "x", "languages": ["c"], "findings_file": "c_findings.json"},
    ]
    selected = ch.select_leaves(leaves, ["python"])
    assert [s["name"] for s in selected] == ["py"]


def test_run_leaves_collects_findings_and_exits(tmp_path):
    leaves = [
        {"name": "stub", "skill": "stub", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "stub_findings.json"},
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
    ]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=["pkg/"],
                                        out_dir=out, overrides={})
    assert leaf_exit == {"stub": 1, "empty": 0}
    assert len(findings) == 1
    assert (out / "stub" / "stub_findings.json").exists()
    assert (out / "empty" / "empty_findings.json").exists()


def test_errored_leaf_recorded(tmp_path):
    leaves = [{"name": "err", "skill": "err", "script": str(FIXTURES / "error_leaf.py"),
               "languages": ["python"], "findings_file": "err_findings.json"}]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=[],
                                        out_dir=out, overrides={})
    assert leaf_exit == {"err": 2}
    assert findings == []


def test_override_replaces_script(tmp_path):
    leaves = [{"name": "stub", "skill": "stub", "script": "does/not/exist.py",
               "languages": ["python"], "findings_file": "stub_findings.json"}]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=[],
                                        out_dir=out, overrides={"stub": str(FIXTURES / "stub_leaf.py")})
    assert leaf_exit == {"stub": 1}
    assert len(findings) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/test_pipeline_run.py -v
```
Expected: FAIL — `select_leaves`/`run_leaves` not defined.

- [ ] **Step 4: Append discovery + run + collect**

Append to `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`:
```python
def load_registry(registry_path: Path) -> list[dict]:
    data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    return data.get("leaves", [])


def select_leaves(leaves: list[dict], languages: list[str]) -> list[dict]:
    wanted = set(languages)
    return [leaf for leaf in leaves if wanted & set(leaf.get("languages", []))]


def _resolve_script(leaf: dict, overrides: dict[str, str]) -> Path:
    if leaf["name"] in overrides:
        return Path(overrides[leaf["name"]])
    script = leaf["script"]
    p = Path(script)
    return p if p.is_absolute() else SKILLS_ROOT / script


def _run_one(leaf: dict, root: str, source_prefixes: list[str], out_dir: Path, overrides: dict[str, str]):
    script = _resolve_script(leaf, overrides)
    leaf_out = out_dir / leaf["name"]
    cmd = [sys.executable, str(script), "--root", root, "--out-dir", str(leaf_out)]
    for pre in source_prefixes:
        cmd += ["--source-prefix", pre]
    if not script.exists():
        return leaf["name"], 2, []
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    findings_path = leaf_out / leaf["findings_file"]
    findings: list[dict] = []
    if proc.returncode != 2 and findings_path.exists():
        try:
            findings = json.loads(findings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return leaf["name"], 2, []
    return leaf["name"], proc.returncode, findings


def run_leaves(leaves: list[dict], root: str, source_prefixes: list[str], out_dir: Path,
               overrides: dict[str, str]):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    leaf_exit: dict[str, int] = {}
    all_findings: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, len(leaves))) as pool:
        results = list(pool.map(
            lambda leaf: _run_one(leaf, root, source_prefixes, out_dir, overrides), leaves
        ))
    for name, code, findings in results:
        leaf_exit[name] = code
        all_findings.extend(findings)
    return all_findings, leaf_exit
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/test_pipeline_run.py -v
```
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add skills/code-health-audit-pipeline/scripts/code_health_pipeline.py skills/code-health-audit-pipeline/tests/fixtures skills/code-health-audit-pipeline/tests/test_pipeline_run.py
git commit -m "feat: add umbrella leaf discovery, parallel run, and collection"
```

---

## Task 4: CLI, report, summary, exit codes — TDD

**Files:** Modify `code_health_pipeline.py` (append); test `tests/test_pipeline_cli.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/code-health-audit-pipeline/tests/test_pipeline_cli.py`:
```python
import json
from pathlib import Path

from helpers import FIXTURES, run_cli


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--registry" in result.stdout


def test_advise_run_writes_summary_and_report(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "stub", "skill": "stub", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "stub_findings.json"},
    ])
    out = tmp_path / "out"
    # stub emits one high DELETE finding (no gate) -> ADVISE / exit 1
    result = run_cli("--root", str(tmp_path), "--source-prefix", "pkg/",
                     "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 1
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "ADVISE"
    assert summary["exit_code"] == 1
    assert summary["leaves"]["stub"]["exit"] == 1
    assert (out / "code_health_report.md").exists()


def test_gate_on_errored_leaf_exits_two(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "err", "skill": "err", "script": str(FIXTURES / "error_leaf.py"),
         "languages": ["python"], "findings_file": "err_findings.json"},
    ])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 2
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "GATE"


def test_pass_when_empty(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
    ])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 0
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "PASS"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/test_pipeline_cli.py -v
```
Expected: FAIL — no CLI/`main` yet.

- [ ] **Step 3: Append report, summary, CLI, and `main`**

Append to `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`:
```python
def build_summary(ranked: list[dict], leaf_exit: dict[str, int], decision: str, code: int) -> dict:
    by_signal: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for f in ranked:
        by_signal[f["signal"]] = by_signal.get(f["signal"], 0) + 1
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    status = {0: "clean", 1: "findings", 2: "errored"}
    leaves = {}
    for name, exit_code in sorted(leaf_exit.items()):
        count = sum(1 for f in ranked if f.get("leaf") == name)
        leaves[name] = {"exit": exit_code, "status": status.get(exit_code, "unknown"), "count": count}
    return {
        "supervisor": decision,
        "exit_code": code,
        "leaves": leaves,
        "totals": {"count": len(ranked), "by_signal": by_signal, "by_severity": by_severity},
        "findings": ranked,
    }


def render_report(ranked: list[dict], decision: str) -> str:
    lines = [f"# code-health-audit-pipeline report — {decision}", ""]
    if not ranked:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[dict]] = {}
    for f in ranked:
        by_signal.setdefault(f["signal"], []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            loc = f["location"]
            lines.append(f"- `{f['path']}:{loc['line_start']}` {loc['symbol']} "
                         f"[{f['severity']}/{f['leaf']}] — {f['suggested_action']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def load_gate(config_path: str | None) -> dict:
    gate = dict(DEFAULT_GATE)
    if config_path:
        try:
            gate.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid --config: {exc}")
    return gate


def _parse_overrides(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"--leaf-script must be name=PATH, got {item!r}")
        name, path = item.split("=", 1)
        overrides[name] = path
    return overrides


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run code-health leaves, merge/rank, decide.")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root. Repeatable.")
    parser.add_argument("--out-dir")
    parser.add_argument("--languages", default="python", help="Comma-separated languages to select leaves.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Leaf registry JSON.")
    parser.add_argument("--leaf-script", action="append", default=[], help="Override: name=PATH. Repeatable.")
    parser.add_argument("--config", help="JSON gate overrides.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return 2
    gate = load_gate(args.config)
    overrides = _parse_overrides(args.leaf_script)
    leaves = select_leaves(load_registry(Path(args.registry)), args.languages.split(","))
    out_dir = Path(args.out_dir)
    findings, leaf_exit = run_leaves(leaves, args.root, args.source_prefixes, out_dir, overrides)
    ranked = rank(merge_and_dedupe(findings))
    decision, code = decide(ranked, leaf_exit, gate)
    summary = build_summary(ranked, leaf_exit, decision, code)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "code_health_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "code_health_report.md").write_text(render_report(ranked, decision), encoding="utf-8")
    print(json.dumps({"status": "ok", "supervisor": decision, "findings": len(ranked)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/code-health-audit-pipeline && python3 -m pytest tests/ -v
```
Expected: PASS (all umbrella tests).

- [ ] **Step 5: Commit**

```bash
git add skills/code-health-audit-pipeline/scripts/code_health_pipeline.py skills/code-health-audit-pipeline/tests/test_pipeline_cli.py
git commit -m "feat: add umbrella CLI, report, summary, and exit codes"
```

---

## Task 5: Register + green gate + end-to-end against real leaves

**Files:** Modify `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

- [ ] **Step 1: Installer `skills[]`**

In `bin/install-code-health-skills.js`:
```javascript
const skills = [
  "complexity-audit",
  "duplication-audit",
  "dead-code-audit",
  "structure-audit",
  "quality-audit",
  "code-health-audit-pipeline",
];
```

- [ ] **Step 2: `check_release.py`**

```python
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
    "dead-code-audit": "dead-code-audit",
    "structure-audit": "structure-audit",
    "quality-audit": "quality-audit",
    "code-health-audit-pipeline": "code-health-audit-pipeline",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
    "structure-audit": ["scripts/structure_audit.py"],
    "quality-audit": ["scripts/quality_audit.py"],
    "code-health-audit-pipeline": ["scripts/code_health_pipeline.py"],
}
```

- [ ] **Step 3: `check_skill_fixtures.py`**

```python
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
    ["python3", "skills/dead-code-audit/scripts/dead_code_audit.py", "--help"],
    ["python3", "skills/structure-audit/scripts/structure_audit.py", "--help"],
    ["python3", "skills/quality-audit/scripts/quality_audit.py", "--help"],
    ["python3", "skills/code-health-audit-pipeline/scripts/code_health_pipeline.py", "--help"],
]
```

- [ ] **Step 4: Run the full gate**

Run: `npm run check`
Expected: all checks pass; `check_release` lists all six skills.

- [ ] **Step 5: End-to-end against a real installed copy (all five real leaves)**

This proves the umbrella wires to the real leaves via the registry. Requires the leaf
tools installed (`pip install lizard radon vulture ruff mypy`; Node for jscpd).

Run:
```bash
node bin/install-code-health-skills.js --dest /tmp/che-e2e --force
python3 /tmp/che-e2e/code-health-audit-pipeline/scripts/code_health_pipeline.py \
  --root skills/structure-audit/tests/fixtures/dirty \
  --source-prefix pkg/ \
  --out-dir /tmp/che-e2e-out
cat /tmp/che-e2e-out/code_health_summary.json
```
Expected: exit code `2` (the structure leaf finds the planted import cycle → GATE);
`code_health_summary.json` shows `"supervisor": "GATE"` and a `structure` leaf entry with
findings. (If some leaf tools are not installed, those leaves report `exit: 2` and the run
still GATEs — confirming the errored-leaf path end-to-end.)

- [ ] **Step 6: Commit**

```bash
git add bin/install-code-health-skills.js scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "chore: register code-health-audit-pipeline and finish the package"
```

---

## Self-Review

- **Spec coverage:** §2 umbrella + `leaf_registry.json` (OCP) — Task 1, 3. §3 `finding-schema.json` — Task 1. §5 `rule-ownership.md` — Task 1. §6 parallel run, merge/dedupe, rank, supervisor + 0/1/2, GATE-on-errored-leaf — Tasks 2–4. §10 OCP (language filter via registry) — `select_leaves` + `test_select_leaves_filters_by_language`. §7 registration + gate — Task 5. ✔
- **Decision logged:** `effort` derived from `signal` in the umbrella (header note); leaf schema unchanged.
- **Placeholder scan:** none. Stub/empty/error leaf fixtures are real, runnable test doubles.
- **Type consistency:** `merge_and_dedupe`, `rank`, `score`, `decide(findings, leaf_exit, gate)`, `DEFAULT_GATE`, `select_leaves(leaves, languages)`, `run_leaves(leaves, root, source_prefixes, out_dir, overrides)`, `build_summary`, `render_report` names and signatures match across the module, the CLI, and all three test files. Registry entry keys (`name`, `skill`, `script`, `languages`, `findings_file`) match between `leaf_registry.json`, `_run_one`, and the tests.

## Plan set complete

With Plans 1–6 implemented, `code-health-skills` is a complete, installable package: five
deterministic advisory leaves + the umbrella, all green under `npm run check`. Top
orchestrator integration remains deferred (spec §8) for a later cycle.
```
