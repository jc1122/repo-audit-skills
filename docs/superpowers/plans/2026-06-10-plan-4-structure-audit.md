# Plan 4 — structure-audit leaf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `structure-audit` leaf — deterministic import-graph analysis emitting RESTRUCTURE findings (import cycles, god-modules, optional layering violations) to the shared schema.

**Architecture:** Builds the internal import graph with the stdlib `ast` module (parse each file's imports, resolve to internal modules), enumerates cycles with an iterative **Tarjan SCC**, and computes fan-in/fan-out per module. Self-contained, zero external analysis dependency, byte-deterministic.

**Tech Stack:** Python 3.10+ (stdlib only for analysis), `pytest`.

**Prerequisite:** Plans 1–3 complete, `npm run check` green. Work in `/home/jakub/projects/code-health-skills`.

**Design note (deviation from spec §4):** The spec named `grimp`. This plan uses the stdlib `ast` import graph + Tarjan instead — no third-party dependency, no API-version risk, and fully deterministic cycle enumeration. The spec's intent (import-graph → RESTRUCTURE) is preserved; only the tool is refined.

---

## File Structure (this plan)

```
skills/structure-audit/
├─ SKILL.md
├─ LICENSE
├─ pyproject.toml
├─ scripts/{health_common.py, structure_audit.py}
├─ references/rubric.md
└─ tests/
   ├─ helpers.py
   ├─ fixtures/clean/pkg/{__init__.py,base.py,use.py}
   ├─ fixtures/dirty/pkg/{__init__.py,a.py,b.py,hub.py}
   ├─ test_structure_findings.py
   └─ test_structure_cli.py
```

Modified (registry appends): `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

---

## Task 1: Scaffold + vendor helper

- [ ] **Step 1: Create dirs and vendor the helper**

Run:
```bash
mkdir -p skills/structure-audit/scripts skills/structure-audit/references skills/structure-audit/tests/fixtures
cp shared/health_common.py skills/structure-audit/scripts/health_common.py
cp LICENSE skills/structure-audit/LICENSE
```

- [ ] **Step 2: Create `pyproject.toml`**

Create `skills/structure-audit/pyproject.toml`:
```toml
[project]
name = "structure-audit"
version = "0.1.0"
description = "Deterministic import-structure audit leaf (ast import graph + Tarjan SCC)."
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```

- [ ] **Step 3: Create `references/rubric.md`**

Create `skills/structure-audit/references/rubric.md`:
```markdown
# structure-audit Rubric

Import graph built from stdlib `ast`. Cycles via Tarjan strongly-connected components.

| Condition | Default threshold | Severity | Signal |
|---|---|---|---|
| Import cycle (SCC size > 1) | n/a | high | RESTRUCTURE |
| Module fan-out (internal imports) | > 20 | medium | RESTRUCTURE |
| Module fan-in (imported-by count) | > 20 | medium | RESTRUCTURE |
| Layering violation (`--layers`) | n/a | high | RESTRUCTURE |

Overrides via `--config` (keys `max_fan_out`, `max_fan_in`, `layers`). `layers` is an
ordered list of dotted module prefixes, top-to-bottom; a lower-layer module importing a
higher-layer module is a violation. Confidence is `high`. Never mutates source.
```

- [ ] **Step 4: Create `SKILL.md`**

Create `skills/structure-audit/SKILL.md`:
```markdown
---
name: structure-audit
version: 0.1.0
description: >
  Deterministic, advisory import-structure audit for Python. Builds the internal
  import graph (stdlib ast), enumerates import cycles (Tarjan SCC), and flags
  god-modules by fan-in/fan-out, emitting RESTRUCTURE findings to the shared
  code-health finding schema. Never mutates source.
---

# structure-audit

## Overview

A code-health leaf skill reporting import cycles, god-modules, and optional layering
violations as advisory RESTRUCTURE findings.

## Quick Start

```bash
python3 scripts/structure_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/structure
```

## Output

- `structure_findings.json` — sorted findings (shared schema).
- `structure_report.md` — summary.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` config error.

## Config

`--config` JSON keys: `max_fan_out`, `max_fan_in`, `layers` (ordered top→bottom prefix
list). See `references/rubric.md`. Findings are deterministic.
```

- [ ] **Step 5: Commit**

```bash
git add skills/structure-audit
git commit -m "feat: scaffold structure-audit skill"
```

---

## Task 2: Fixtures + helpers

- [ ] **Step 1: Create the clean fixture (linear, no cycle)**

Run:
```bash
mkdir -p skills/structure-audit/tests/fixtures/clean/pkg skills/structure-audit/tests/fixtures/dirty/pkg
: > skills/structure-audit/tests/fixtures/clean/pkg/__init__.py
: > skills/structure-audit/tests/fixtures/dirty/pkg/__init__.py
```

Create `skills/structure-audit/tests/fixtures/clean/pkg/base.py`:
```python
VALUE = 1
```

Create `skills/structure-audit/tests/fixtures/clean/pkg/use.py`:
```python
from pkg import base


def show():
    return base.VALUE
```

- [ ] **Step 2: Create the dirty fixture (cycle a↔b + a hub)**

Create `skills/structure-audit/tests/fixtures/dirty/pkg/a.py`:
```python
from pkg import b


def call_b():
    return b.value()
```

Create `skills/structure-audit/tests/fixtures/dirty/pkg/b.py`:
```python
from pkg import a


def value():
    return a.call_b()
```

Create `skills/structure-audit/tests/fixtures/dirty/pkg/hub.py`:
```python
from pkg import a
from pkg import b


def both():
    return a.call_b() + b.value()
```

Expected: import cycle `{pkg.a, pkg.b}` → RESTRUCTURE; `pkg.hub` has fan-out 2.

- [ ] **Step 3: Create `helpers.py`**

Create `skills/structure-audit/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "structure_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("structure_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "structure_findings.json").read_text())
```

- [ ] **Step 4: Commit**

```bash
git add skills/structure-audit/tests
git commit -m "test: add structure-audit fixtures and helpers"
```

---

## Task 3: Import graph + Tarjan + findings — TDD

**Files:** Create `skills/structure-audit/scripts/structure_audit.py`; test `tests/test_structure_findings.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/structure-audit/tests/test_structure_findings.py`:
```python
from helpers import FIXTURES, load_module

sa = load_module()
DEFAULTS = sa.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = sa.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_detects_import_cycle():
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    cycles = [f for f in findings if f.metric_name == "import_cycle_size"]
    assert cycles, "expected an import cycle finding"
    assert cycles[0].signal == "RESTRUCTURE"
    assert cycles[0].severity == "high"
    assert "pkg.a" in cycles[0].symbol and "pkg.b" in cycles[0].symbol


def test_fan_out_is_flagged_with_low_threshold():
    thresholds = dict(DEFAULTS, max_fan_out=1)
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=thresholds)
    fan = [f for f in findings if f.metric_name == "fan_out" and f.symbol == "pkg.hub"]
    assert fan and fan[0].metric_value == 2


def test_tarjan_finds_two_node_scc():
    edges = {"x": ["y"], "y": ["x"], "z": []}
    sccs = sa._strongly_connected_components(sorted(edges), edges)
    multi = [c for c in sccs if len(c) > 1]
    assert multi == [["x", "y"]]


def test_layers_violation_detected():
    # pkg.b (treated as "low") imports pkg.a (treated as "high") -> violation
    thresholds = dict(DEFAULTS, layers=["pkg.a", "pkg.b"])
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=thresholds)
    violations = [f for f in findings if f.metric_name == "layer_violation"]
    assert any("pkg.b" in v.symbol and "pkg.a" in v.symbol for v in violations)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/structure-audit && python3 -m pytest tests/test_structure_findings.py -v
```
Expected: FAIL — `structure_audit.py` does not exist.

- [ ] **Step 3: Write the analysis module**

Create `skills/structure-audit/scripts/structure_audit.py`:
```python
#!/usr/bin/env python3
"""structure-audit leaf: ast import graph + Tarjan SCC → RESTRUCTURE findings."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "structure"

DEFAULT_THRESHOLDS = {
    "max_fan_out": 20,
    "max_fan_in": 20,
    "layers": [],
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_base(node: ast.ImportFrom, current_module: str, is_pkg: bool) -> str:
    if node.level == 0:
        return node.module or ""
    package = current_module if is_pkg else ".".join(current_module.split(".")[:-1])
    pkg_parts = package.split(".") if package else []
    drop = node.level - 1
    if drop:
        pkg_parts = pkg_parts[: len(pkg_parts) - drop] if drop <= len(pkg_parts) else []
    base = ".".join(pkg_parts)
    if node.module:
        base = f"{base}.{node.module}" if base else node.module
    return base


def _imported_names(path: Path, current_module: str, is_pkg: bool) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_base(node, current_module, is_pkg)
            for alias in node.names:
                if alias.name == "*":
                    if base:
                        names.append(base)
                else:
                    names.append(f"{base}.{alias.name}" if base else alias.name)
    return names


def _resolve_to_internal(name: str, module_set: set[str]) -> str | None:
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in module_set:
            return cand
    return None


def build_graph(root: Path, files: list[Path]):
    module_file: dict[str, str] = {}
    is_pkg: dict[str, bool] = {}
    for p in files:
        mod = _module_name(p, root)
        if mod:
            module_file[mod] = p.relative_to(root).as_posix()
            is_pkg[mod] = p.name == "__init__.py"
    module_set = set(module_file)
    edges: dict[str, set[str]] = {m: set() for m in module_set}
    for p in files:
        src = _module_name(p, root)
        if not src:
            continue
        for target in _imported_names(p, src, is_pkg.get(src, False)):
            dst = _resolve_to_internal(target, module_set)
            if dst and dst != src:
                edges[src].add(dst)
    return module_file, {m: sorted(s) for m, s in edges.items()}


def _strongly_connected_components(nodes, edges):
    index_counter = [0]
    stack: list[str] = []
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []
    for root_node in nodes:
        if root_node in index:
            continue
        work = [(root_node, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = index_counter[0]
                lowlink[node] = index_counter[0]
                index_counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            recurse = False
            succs = edges.get(node, [])
            for i in range(pi, len(succs)):
                w = succs[i]
                if w not in index:
                    work[-1] = (node, i + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                if on_stack.get(w):
                    lowlink[node] = min(lowlink[node], index[w])
            if recurse:
                continue
            if lowlink[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == node:
                        break
                result.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
    return result


def _layer_of(module: str, layers: list[str]) -> int | None:
    best_idx, best_len = None, -1
    for idx, prefix in enumerate(layers):
        if (module == prefix or module.startswith(prefix + ".")) and len(prefix) > best_len:
            best_idx, best_len = idx, len(prefix)
    return best_idx


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    module_file, edges = build_graph(root, files)
    nodes = sorted(module_file)
    findings: list[hc.Finding] = []

    # Cycles
    for comp in _strongly_connected_components(nodes, edges):
        is_cycle = len(comp) > 1 or (len(comp) == 1 and comp[0] in edges.get(comp[0], []))
        if not is_cycle:
            continue
        members = sorted(comp)
        first = members[0]
        findings.append(hc.Finding(
            leaf=LEAF, signal="RESTRUCTURE", severity="high", path=module_file[first],
            line_start=1, line_end=1, symbol="cycle:" + "|".join(members),
            metric_name="import_cycle_size", metric_value=float(len(members)), metric_threshold=1.0,
            evidence_tool="ast", evidence_raw="import cycle: " + " -> ".join(members),
            confidence="high",
            suggested_action="Break the import cycle among: " + ", ".join(members),
        ))

    # Fan-in / fan-out
    in_degree = {m: 0 for m in nodes}
    for src in nodes:
        for dst in edges.get(src, []):
            in_degree[dst] = in_degree.get(dst, 0) + 1
    for m in nodes:
        out_deg = len(edges.get(m, []))
        if out_deg > thresholds["max_fan_out"]:
            findings.append(hc.Finding(
                leaf=LEAF, signal="RESTRUCTURE", severity="medium", path=module_file[m],
                line_start=1, line_end=1, symbol=m, metric_name="fan_out",
                metric_value=float(out_deg), metric_threshold=float(thresholds["max_fan_out"]),
                evidence_tool="ast", evidence_raw=f"{m} imports {out_deg} internal modules",
                confidence="high", suggested_action=f"Reduce coupling: {m} imports {out_deg} modules",
            ))
        if in_degree.get(m, 0) > thresholds["max_fan_in"]:
            findings.append(hc.Finding(
                leaf=LEAF, signal="RESTRUCTURE", severity="medium", path=module_file[m],
                line_start=1, line_end=1, symbol=m, metric_name="fan_in",
                metric_value=float(in_degree[m]), metric_threshold=float(thresholds["max_fan_in"]),
                evidence_tool="ast", evidence_raw=f"{m} is imported by {in_degree[m]} modules",
                confidence="high", suggested_action=f"Split god-module: {m} is imported by {in_degree[m]} modules",
            ))

    # Layering
    layers = thresholds.get("layers") or []
    if layers:
        for src in nodes:
            src_layer = _layer_of(src, layers)
            if src_layer is None:
                continue
            for dst in edges.get(src, []):
                dst_layer = _layer_of(dst, layers)
                if dst_layer is None:
                    continue
                if src_layer > dst_layer:  # lower layer importing higher layer
                    findings.append(hc.Finding(
                        leaf=LEAF, signal="RESTRUCTURE", severity="high", path=module_file[src],
                        line_start=1, line_end=1, symbol=f"{src}->{dst}", metric_name="layer_violation",
                        metric_value=float(src_layer - dst_layer), metric_threshold=0.0,
                        evidence_tool="ast", evidence_raw=f"{src} (layer {src_layer}) imports {dst} (layer {dst_layer})",
                        confidence="high",
                        suggested_action=f"Layering violation: {src} must not import {dst}",
                    ))

    return hc.sort_findings(findings)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/structure-audit && python3 -m pytest tests/test_structure_findings.py -v
```
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add skills/structure-audit/scripts/structure_audit.py skills/structure-audit/tests/test_structure_findings.py
git commit -m "feat: add structure-audit analysis (ast graph + Tarjan)"
```

---

## Task 4: CLI, report, exit codes — TDD

**Files:** Modify `structure_audit.py` (append); test `tests/test_structure_cli.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/structure-audit/tests/test_structure_cli.py`:
```python
from helpers import FIXTURES, read_findings, run_cli


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--source-prefix" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli("--root", str(FIXTURES / "clean"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_dirty_exits_one_with_cycle(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert any(d["metric"]["name"] == "import_cycle_size" for d in data)
    assert (tmp_path / "structure_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "structure_findings.json").read_bytes() == (b / "structure_findings.json").read_bytes()


def test_bad_config_exits_two(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--config", str(bad))
    assert result.returncode == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/structure-audit && python3 -m pytest tests/test_structure_cli.py -v
```
Expected: FAIL — no CLI/`main` yet.

- [ ] **Step 3: Append CLI, report, and `main`**

Append to `skills/structure-audit/scripts/structure_audit.py`:
```python
def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# structure-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## RESTRUCTURE ({len(findings)})")
    for f in findings:
        lines.append(f"- `{f.path}` {f.symbol} — {f.metric_name}={f.metric_value:g} [{f.severity}]")
    lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic import-structure audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds (max_fan_out, max_fan_in, layers).")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "structure_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/structure-audit && python3 -m pytest tests/ -v
```
Expected: PASS (all structure-audit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/structure-audit/scripts/structure_audit.py skills/structure-audit/tests/test_structure_cli.py
git commit -m "feat: add structure-audit CLI, report, and exit codes"
```

---

## Task 5: Register in package machinery + green the gate

- [ ] **Step 1: Installer `skills[]`**

In `bin/install-code-health-skills.js`:
```javascript
const skills = [
  "complexity-audit",
  "duplication-audit",
  "dead-code-audit",
  "structure-audit",
];
```

- [ ] **Step 2: `check_release.py`**

```python
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
    "dead-code-audit": "dead-code-audit",
    "structure-audit": "structure-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
    "structure-audit": ["scripts/structure_audit.py"],
}
```

- [ ] **Step 3: `check_skill_fixtures.py`**

```python
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
    ["python3", "skills/dead-code-audit/scripts/dead_code_audit.py", "--help"],
    ["python3", "skills/structure-audit/scripts/structure_audit.py", "--help"],
]
```

- [ ] **Step 4: Run the full gate**

Run: `npm run check`
Expected: all checks pass; `check_release` lists four skills.

- [ ] **Step 5: Commit**

```bash
git add bin/install-code-health-skills.js scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "chore: register structure-audit in package machinery"
```

---

## Self-Review

- **Spec coverage:** §4 structure-audit (import graph, cycles, fan-in/out, layering) — Tasks 1–4. §3 schema/exit/byte-stable — Tasks 3–4. §7 registration — Tasks 1, 5. ✔
- **Deviation logged:** `grimp` → stdlib `ast` + Tarjan (header note). Same signal, fewer dependencies, more deterministic.
- **Placeholder scan:** none.
- **Type consistency:** `analyze_tree(root, source_prefixes, thresholds)`, `DEFAULT_THRESHOLDS` keys (`max_fan_out`, `max_fan_in`, `layers`), `_strongly_connected_components(nodes, edges)`, `LEAF="structure"`, and `hc.*` names match across analysis, CLI, and tests.
```
