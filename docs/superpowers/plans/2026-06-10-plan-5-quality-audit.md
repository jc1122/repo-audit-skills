# Plan 5 — quality-audit leaf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `quality-audit` leaf — deterministic lint, formatting-drift, and type-error detection emitting LINT / FORMAT / TYPE findings to the shared schema. This is the owned replacement for the external `python-code-quality` skill.

**Architecture:** `ruff check` (selected rules, with the codes other leaves own explicitly excluded), `ruff format --check` (formatting drift, reported never applied), and a type checker (default `mypy`, `ty` selectable). Advisory-only. Self-contained, following Plan 1's pattern.

**Tech Stack:** Python 3.10+, `ruff`, `mypy`, `pytest`.

**Prerequisite:** Plans 1–4 complete, `npm run check` green. Work in `/home/jakub/projects/code-health-skills`. Install tools: `pip install ruff mypy pytest`.

**Design note (deviation from spec §4):** The spec named `ty` as the default type checker. This plan defaults to `mypy` (stable, ubiquitous, byte-parseable line output), with `ty` selectable via `--config {"type_checker": "ty"}`. The non-overlap guarantee is unchanged.

**Non-overlap (spec §5):** `ruff check` runs with `--ignore F401,F811,F841,C901` so the codes owned by `dead-code-audit` (F401/F811/F841) and `complexity-audit` (C901) are never reported here.

---

## File Structure (this plan)

```
skills/quality-audit/
├─ SKILL.md
├─ LICENSE
├─ pyproject.toml
├─ scripts/{health_common.py, quality_audit.py}
├─ references/rubric.md
└─ tests/
   ├─ helpers.py
   ├─ fixtures/clean/pkg/clean.py
   ├─ fixtures/dirty/pkg/bad.py
   ├─ fixtures/dirty/pkg/messy.py
   ├─ test_quality_findings.py
   └─ test_quality_cli.py
```

Modified (registry appends): `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

---

## Task 1: Scaffold + vendor helper

- [ ] **Step 1: Create dirs and vendor the helper**

Run:
```bash
mkdir -p skills/quality-audit/scripts skills/quality-audit/references skills/quality-audit/tests/fixtures
cp shared/health_common.py skills/quality-audit/scripts/health_common.py
cp LICENSE skills/quality-audit/LICENSE
```

- [ ] **Step 2: Create `pyproject.toml`**

Create `skills/quality-audit/pyproject.toml`:
```toml
[project]
name = "quality-audit"
version = "0.1.0"
description = "Deterministic lint/format/type audit leaf (ruff + mypy)."
requires-python = ">=3.10"
dependencies = [
    "ruff>=0.6",
    "mypy>=1.10",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
ty = ["ty>=0.0.1"]
```

- [ ] **Step 3: Create `references/rubric.md`**

Create `skills/quality-audit/references/rubric.md`:
```markdown
# quality-audit Rubric

| Source | Detects | Severity | Signal |
|---|---|---|---|
| ruff check | lint rule violations | medium | LINT |
| ruff format --check | formatting drift | low | FORMAT |
| mypy / ty | type errors | high | TYPE |

ruff selection: `E,W,F,B,SIM,UP` with `--ignore F401,F811,F841,C901` (the codes owned by
dead-code-audit and complexity-audit), guaranteeing non-overlap. Type checker defaults to
`mypy`; set `--config {"type_checker": "ty"}` to use `ty`. Override the ruff selection via
`--config` keys `ruff_select` / `ruff_ignore`. Advisory only — never applies fixes or
reformats.
```

- [ ] **Step 4: Create `SKILL.md`**

Create `skills/quality-audit/SKILL.md`:
```markdown
---
name: quality-audit
version: 0.1.0
description: >
  Deterministic, advisory lint/format/type audit for Python. Uses ruff (lint, with
  dead-code and complexity codes excluded), ruff format --check (formatting drift,
  reported not applied), and a type checker (mypy by default, ty selectable) to emit
  LINT / FORMAT / TYPE findings to the shared code-health finding schema. Never mutates
  source.
---

# quality-audit

## Overview

A code-health leaf skill reporting lint violations, formatting drift, and type errors as
advisory findings. It never runs `ruff --fix` or reformats.

## Quick Start

```bash
python3 scripts/quality_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/quality
```

## Output

- `quality_findings.json` — sorted findings (shared schema).
- `quality_report.md` — summary grouped by signal.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Config

`--config` JSON keys: `type_checker` ("mypy"|"ty"), `ruff_select`, `ruff_ignore`. The
default ruff ignore excludes F401/F811/F841/C901 (owned by other leaves). Findings are
deterministic.
```

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit
git commit -m "feat: scaffold quality-audit skill"
```

---

## Task 2: Fixtures + helpers

- [ ] **Step 1: Create the clean fixture**

Create `skills/quality-audit/tests/fixtures/clean/pkg/clean.py`:
```python
def add(a: int, b: int) -> int:
    return a + b
```

Lint-clean, already formatted, type-clean.

- [ ] **Step 2: Create the dirty fixtures**

Create `skills/quality-audit/tests/fixtures/dirty/pkg/bad.py`:
```python
def bad(value: int) -> int:
    if value == None:
        value = 0
    return "not an int"
```

`== None` → ruff E711 (LINT); returning a `str` from `-> int` → mypy error (TYPE).

Create `skills/quality-audit/tests/fixtures/dirty/pkg/messy.py`:
```python
def messy( x ):
    y=x+1
    return  y
```

Bad spacing → `ruff format --check` reports "Would reformat" (FORMAT) and ruff check
flags whitespace rules (LINT).

- [ ] **Step 3: Create `helpers.py`**

Create `skills/quality-audit/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "quality_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("quality_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "quality_findings.json").read_text())
```

- [ ] **Step 4: Commit**

```bash
git add skills/quality-audit/tests
git commit -m "test: add quality-audit fixtures and helpers"
```

---

## Task 3: Analysis logic — TDD

**Files:** Create `skills/quality-audit/scripts/quality_audit.py`; test `tests/test_quality_findings.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/quality-audit/tests/test_quality_findings.py`:
```python
from helpers import FIXTURES, load_module

qa = load_module()
DEFAULTS = qa.DEFAULT_CONFIG


def test_clean_fixture_yields_no_findings():
    findings = qa.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], config=DEFAULTS)
    assert findings == []


def test_dirty_fixture_emits_lint_format_and_type():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    signals = {f.signal for f in findings}
    assert "LINT" in signals
    assert "FORMAT" in signals
    assert "TYPE" in signals


def test_owned_codes_are_never_reported():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    codes = {f.metric_name for f in findings if f.signal == "LINT"}
    assert codes.isdisjoint({"F401", "F811", "F841", "C901"})


def test_type_findings_are_high_severity():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    type_findings = [f for f in findings if f.signal == "TYPE"]
    assert type_findings and all(f.severity == "high" for f in type_findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/quality-audit && python3 -m pytest tests/test_quality_findings.py -v
```
Expected: FAIL — `quality_audit.py` does not exist.

- [ ] **Step 3: Write the analysis module**

Create `skills/quality-audit/scripts/quality_audit.py`:
```python
#!/usr/bin/env python3
"""quality-audit leaf: ruff lint + ruff format --check + mypy/ty → LINT/FORMAT/TYPE."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "quality"

DEFAULT_CONFIG = {
    "type_checker": "mypy",
    "ruff_select": "E,W,F,B,SIM,UP",
    "ruff_ignore": "F401,F811,F841,C901",
}

_TYPE_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s*error:\s*(?P<msg>.*?)(?:\s*\[(?P<code>[\w-]+)\])?$"
)


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _ruff_lint(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    cmd = ["ruff", "check", "--no-cache", "--output-format", "json",
           "--select", config["ruff_select"], "--ignore", config["ruff_ignore"], *rel_files]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(f"ruff produced unparseable output: {proc.stderr.strip()}") from exc
    owned = set(config["ruff_ignore"].split(","))
    findings: list[hc.Finding] = []
    for item in items:
        code = item.get("code") or "RUFF"
        if code in owned:
            continue
        loc = item.get("location") or {}
        row, col = int(loc.get("row", 1)), int(loc.get("column", 1))
        end_row = int((item.get("end_location") or {}).get("row", row))
        findings.append(hc.Finding(
            leaf=LEAF, signal="LINT", severity="medium",
            path=Path(item.get("filename", "")).as_posix(), line_start=row, line_end=end_row,
            symbol=f"{code}@{row}:{col}", metric_name=code, metric_value=0.0, metric_threshold=0.0,
            evidence_tool="ruff", evidence_raw=item.get("message", ""),
            confidence="high", suggested_action=item.get("message", f"Fix {code}"),
        ))
    return findings


def _ruff_format(root: Path, rel_files: list[str]) -> list[hc.Finding]:
    cmd = ["ruff", "format", "--check", *rel_files]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if not line.startswith("Would reformat:"):
            continue
        path = line.split("Would reformat:", 1)[1].strip()
        findings.append(hc.Finding(
            leaf=LEAF, signal="FORMAT", severity="low", path=Path(path).as_posix(),
            line_start=1, line_end=1, symbol=path, metric_name="format_drift",
            metric_value=0.0, metric_threshold=0.0, evidence_tool="ruff format",
            evidence_raw=line, confidence="high",
            suggested_action=f"Run the formatter on {path}",
        ))
    return findings


def _type_findings(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    checker = config.get("type_checker", "mypy")
    with tempfile.TemporaryDirectory() as cache:
        if checker == "ty":
            cmd = ["ty", "check", *rel_files]
        else:
            cmd = ["mypy", "--no-error-summary", "--no-color-output", "--ignore-missing-imports",
                   "--no-incremental", "--cache-dir", cache, *rel_files]
        try:
            proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
        except FileNotFoundError as exc:
            raise ToolError(f"{checker} is not installed") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        m = _TYPE_RE.match(line.strip())
        if not m:
            continue
        row = int(m.group("line"))
        code = m.group("code") or "type-error"
        findings.append(hc.Finding(
            leaf=LEAF, signal="TYPE", severity="high", path=Path(m.group("path")).as_posix(),
            line_start=row, line_end=row, symbol=f"{code}@{row}", metric_name=code,
            metric_value=0.0, metric_threshold=0.0, evidence_tool=checker,
            evidence_raw=m.group("msg"), confidence="high",
            suggested_action=m.group("msg"),
        ))
    return findings


def analyze_tree(root, source_prefixes, config) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    rel_files = [p.relative_to(root).as_posix() for p in files]
    findings = _ruff_lint(root, rel_files, config)
    findings += _ruff_format(root, rel_files)
    findings += _type_findings(root, rel_files, config)
    return hc.sort_findings(findings)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/quality-audit && python3 -m pytest tests/test_quality_findings.py -v
```
Expected: PASS (4 passed). If tools missing: `pip install ruff mypy`.

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit/scripts/quality_audit.py skills/quality-audit/tests/test_quality_findings.py
git commit -m "feat: add quality-audit analysis (ruff + mypy)"
```

---

## Task 4: CLI, report, exit codes — TDD

**Files:** Modify `quality_audit.py` (append); test `tests/test_quality_cli.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/quality-audit/tests/test_quality_cli.py`:
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


def test_dirty_exits_one_with_findings(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert {d["signal"] for d in data} >= {"LINT", "FORMAT", "TYPE"}
    assert (tmp_path / "quality_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "quality_findings.json").read_bytes() == (b / "quality_findings.json").read_bytes()


def test_missing_tool_exits_two(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--simulate-missing-tool")
    assert result.returncode == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/quality-audit && python3 -m pytest tests/test_quality_cli.py -v
```
Expected: FAIL — no CLI/`main` yet.

- [ ] **Step 3: Append CLI, report, and `main`**

Append to `skills/quality-audit/scripts/quality_audit.py`:
```python
def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# quality-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(f"- `{f.path}:{f.line_start}` {f.metric_name} — {f.evidence_raw} [{f.severity}]")
        lines.append("")
    return "\n".join(lines) + "\n"


def load_config(config_path: str | None) -> dict:
    config = dict(DEFAULT_CONFIG)
    if config_path:
        try:
            config.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic lint/format/type audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding config (type_checker, ruff_select, ruff_ignore).")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument("--simulate-missing-tool", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        if args.simulate_missing_tool:
            raise ToolError("simulated missing tool")
        config = load_config(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, config)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "quality_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/quality-audit && python3 -m pytest tests/ -v
```
Expected: PASS (all quality-audit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/quality-audit/scripts/quality_audit.py skills/quality-audit/tests/test_quality_cli.py
git commit -m "feat: add quality-audit CLI, report, and exit codes"
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
  "quality-audit",
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
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
    "structure-audit": ["scripts/structure_audit.py"],
    "quality-audit": ["scripts/quality_audit.py"],
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
]
```

- [ ] **Step 4: Run the full gate**

Run: `npm run check`
Expected: all checks pass; `check_release` lists all five leaves.

- [ ] **Step 5: Commit**

```bash
git add bin/install-code-health-skills.js scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "chore: register quality-audit in package machinery"
```

---

## Self-Review

- **Spec coverage:** §4 quality-audit (ruff lint, ruff format --check, type checker) — Tasks 1–4. §5 non-overlap (ignore F401/F811/F841/C901) — Task 3 + `test_owned_codes_are_never_reported`. §3 schema/exit/byte-stable — Tasks 3–4. §7 registration — Tasks 1, 5. ✔
- **Deviation logged:** default type checker `mypy` (ty selectable) — header note; non-overlap unchanged.
- **Placeholder scan:** none. `--simulate-missing-tool` is a documented test seam.
- **Type consistency:** `analyze_tree(root, source_prefixes, config)`, `DEFAULT_CONFIG` keys (`type_checker`, `ruff_select`, `ruff_ignore`), `LEAF="quality"`, and `hc.*` names match across analysis, CLI, and tests.
```
