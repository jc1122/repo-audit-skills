# Plan 3 — dead-code-audit leaf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `dead-code-audit` leaf — deterministic dead/unused-code detection emitting DELETE findings to the shared schema.

**Architecture:** `vulture` finds unused functions/classes/methods/properties (with a confidence %); `ruff check` (restricted to exactly F401/F811/F841) finds unused imports, redefinitions, and unused locals. Non-overlap within the leaf: vulture is parsed only for definition types ruff does not own; imports/redefinitions/locals come from ruff. Self-contained leaf following Plan 1's pattern.

**Tech Stack:** Python 3.10+, `vulture`, `ruff`, `pytest`.

**Prerequisite:** Plans 1–2 complete, `npm run check` green. Work in `/home/jakub/projects/code-health-skills`. Install tools: `pip install vulture ruff pytest`.

---

## File Structure (this plan)

```
skills/dead-code-audit/
├─ SKILL.md
├─ LICENSE
├─ pyproject.toml
├─ scripts/{health_common.py, dead_code_audit.py}
├─ references/rubric.md
└─ tests/
   ├─ helpers.py
   ├─ fixtures/clean/pkg/clean.py
   ├─ fixtures/dirty/pkg/dirty.py
   ├─ test_dead_code_findings.py
   └─ test_dead_code_cli.py
```

Modified (registry appends): `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

---

## Task 1: Scaffold + vendor helper

**Files:** Create `skills/dead-code-audit/{SKILL.md,LICENSE,pyproject.toml,references/rubric.md}`, vendor `scripts/health_common.py`.

- [ ] **Step 1: Create dirs and vendor the helper**

Run:
```bash
mkdir -p skills/dead-code-audit/scripts skills/dead-code-audit/references skills/dead-code-audit/tests/fixtures
cp shared/health_common.py skills/dead-code-audit/scripts/health_common.py
cp LICENSE skills/dead-code-audit/LICENSE
```

- [ ] **Step 2: Create `pyproject.toml`**

Create `skills/dead-code-audit/pyproject.toml`:
```toml
[project]
name = "dead-code-audit"
version = "0.1.0"
description = "Deterministic dead/unused-code audit leaf (vulture + ruff F-codes)."
requires-python = ">=3.10"
dependencies = [
    "vulture>=2.11",
    "ruff>=0.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

- [ ] **Step 3: Create `references/rubric.md`**

Create `skills/dead-code-audit/references/rubric.md`:
```markdown
# dead-code-audit Rubric

| Source | Detects | Severity | Signal |
|---|---|---|---|
| vulture | unused function/class/method/property | by confidence | DELETE |
| ruff F401 | unused import | medium | DELETE |
| ruff F811 | redefinition of unused name | medium | DELETE |
| ruff F841 | unused local variable | medium | DELETE |

Vulture confidence → severity: ≥90 high, ≥70 medium, else low; confidence → schema
`confidence` field: ≥90 high, ≥70 medium, else low.

Non-overlap rule: vulture is parsed only for `function/class/method/property`. Unused
imports, redefinitions, and unused locals come from ruff (F401/F811/F841), the codes
this leaf owns. `--allowlist FILE` passes a vulture whitelist to suppress framework
false positives. Never mutates source.
```

- [ ] **Step 4: Create `SKILL.md`**

Create `skills/dead-code-audit/SKILL.md`:
```markdown
---
name: dead-code-audit
version: 0.1.0
description: >
  Deterministic, advisory dead-code audit for Python. Uses vulture (unused
  functions/classes/methods/properties) and ruff F401/F811/F841 (unused imports,
  redefinitions, unused locals) to emit DELETE findings to the shared code-health
  finding schema. Never mutates source.
---

# dead-code-audit

## Overview

A code-health leaf skill reporting unused/dead code as advisory DELETE findings. It
does not delete anything.

## Quick Start

```bash
python3 scripts/dead_code_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/dead-code \
  --allowlist .vulture_whitelist.py
```

## Output

- `dead-code_findings.json` — sorted findings (shared schema).
- `dead-code_report.md` — summary.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error.

## Tools

vulture + ruff (F401/F811/F841 only). See `references/rubric.md`. `--allowlist FILE`
suppresses vulture false positives. Findings are deterministic.
```

- [ ] **Step 5: Commit**

```bash
git add skills/dead-code-audit
git commit -m "feat: scaffold dead-code-audit skill"
```

---

## Task 2: Fixtures + helpers

- [ ] **Step 1: Create the clean fixture (no dead code)**

Create `skills/dead-code-audit/tests/fixtures/clean/pkg/clean.py`:
```python
VALUE = 1


def get_value():
    return VALUE


RESULT = get_value()
```

Everything is referenced (no unused functions for vulture, no unused imports/locals for
ruff).

- [ ] **Step 2: Create the dirty fixture**

Create `skills/dead-code-audit/tests/fixtures/dirty/pkg/dirty.py`:
```python
import os


def public_entry():
    return _helper()


def _helper():
    return 1


def never_called():
    return 99


def leaky():
    unused_local = 123
    return 5
```

Expected: vulture flags `never_called` (and `public_entry`, `leaky` as unreferenced
functions) → DELETE; ruff F401 flags `import os`; ruff F841 flags `unused_local`.

- [ ] **Step 3: Create `helpers.py`**

Create `skills/dead-code-audit/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "dead_code_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("dead_code_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "dead-code_findings.json").read_text())
```

- [ ] **Step 4: Commit**

```bash
git add skills/dead-code-audit/tests
git commit -m "test: add dead-code-audit fixtures and helpers"
```

---

## Task 3: Analysis logic — TDD

**Files:** Create `skills/dead-code-audit/scripts/dead_code_audit.py`; test `tests/test_dead_code_findings.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/dead-code-audit/tests/test_dead_code_findings.py`:
```python
from helpers import FIXTURES, load_module

dc = load_module()
DEFAULTS = dc.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = dc.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    assert findings == []


def test_dirty_fixture_flags_unused_function_via_vulture():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    names = {f.symbol for f in findings if f.evidence_tool == "vulture"}
    assert "never_called" in names
    assert all(f.signal == "DELETE" for f in findings)


def test_dirty_fixture_flags_unused_import_and_local_via_ruff():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    codes = {f.metric_name for f in findings if f.evidence_tool == "ruff"}
    assert "F401" in codes  # unused import os
    assert "F841" in codes  # unused_local


def test_vulture_does_not_report_imports_or_variables():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    vulture_kinds = {f.metric_name for f in findings if f.evidence_tool == "vulture"}
    assert vulture_kinds <= {"dead_code_confidence"}
    # the unused import is owned by ruff (F401), never duplicated by vulture
    vulture_symbols = {f.symbol for f in findings if f.evidence_tool == "vulture"}
    assert "os" not in vulture_symbols
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/dead-code-audit && python3 -m pytest tests/test_dead_code_findings.py -v
```
Expected: FAIL — `dead_code_audit.py` does not exist.

- [ ] **Step 3: Write the analysis module**

Create `skills/dead-code-audit/scripts/dead_code_audit.py`:
```python
#!/usr/bin/env python3
"""dead-code-audit leaf: vulture (defs) + ruff F401/F811/F841 → DELETE findings."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "dead-code"

DEFAULT_THRESHOLDS = {
    "min_confidence": 60,
}

OWNED_RUFF_CODES = ("F401", "F811", "F841")
VULTURE_KEEP = {"function", "class", "method", "property"}
_VULTURE_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+): unused (?P<kind>[\w ]+?) '(?P<name>[^']+)' \((?P<conf>\d+)% confidence\)$"
)


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _severity_for_conf(conf: int) -> str:
    if conf >= 90:
        return "high"
    if conf >= 70:
        return "medium"
    return "low"


def _confidence_for_conf(conf: int) -> str:
    if conf >= 90:
        return "high"
    if conf >= 70:
        return "medium"
    return "low"


def _vulture_findings(root: Path, files: list[Path], thresholds: dict, allowlist: str | None) -> list[hc.Finding]:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = ["vulture", "--min-confidence", str(thresholds["min_confidence"]), *rel_files]
    if allowlist:
        cmd.append(allowlist)
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("vulture is not installed") from exc
    findings: list[hc.Finding] = []
    for line in proc.stdout.splitlines():
        m = _VULTURE_RE.match(line.strip())
        if not m:
            continue
        kind = m.group("kind").strip()
        if kind not in VULTURE_KEEP:
            continue  # imports/variables are owned by ruff
        conf = int(m.group("conf"))
        ln = int(m.group("line"))
        findings.append(hc.Finding(
            leaf=LEAF, signal="DELETE", severity=_severity_for_conf(conf),
            path=Path(m.group("path")).as_posix(), line_start=ln, line_end=ln,
            symbol=m.group("name"),
            metric_name="dead_code_confidence", metric_value=float(conf),
            metric_threshold=float(thresholds["min_confidence"]),
            evidence_tool="vulture", evidence_raw=line.strip(),
            confidence=_confidence_for_conf(conf),
            suggested_action=f"Remove unused {kind} '{m.group('name')}' if truly dead",
        ))
    return findings


def _ruff_findings(root: Path, files: list[Path]) -> list[hc.Finding]:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = ["ruff", "check", "--select", ",".join(OWNED_RUFF_CODES),
           "--output-format", "json", "--no-cache", *rel_files]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(f"ruff produced unparseable output: {proc.stderr.strip()}") from exc
    findings: list[hc.Finding] = []
    for item in items:
        code = item.get("code") or ""
        if code not in OWNED_RUFF_CODES:
            continue
        loc = item.get("location") or {}
        row = int(loc.get("row", 1))
        col = int(loc.get("column", 1))
        end_row = int((item.get("end_location") or {}).get("row", row))
        path = Path(item.get("filename", "")).as_posix()
        findings.append(hc.Finding(
            leaf=LEAF, signal="DELETE", severity="medium", path=path,
            line_start=row, line_end=end_row, symbol=f"{code}@{row}:{col}",
            metric_name=code, metric_value=0.0, metric_threshold=0.0,
            evidence_tool="ruff", evidence_raw=item.get("message", ""),
            confidence="high",
            suggested_action=item.get("message", f"Remove {code} occurrence"),
        ))
    return findings


def analyze_tree(root, source_prefixes, thresholds, allowlist=None) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    findings = _vulture_findings(root, files, thresholds, allowlist)
    findings += _ruff_findings(root, files)
    return hc.sort_findings(findings)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/dead-code-audit && python3 -m pytest tests/test_dead_code_findings.py -v
```
Expected: PASS (4 passed). If `vulture`/`ruff` missing: `pip install vulture ruff`.

- [ ] **Step 5: Commit**

```bash
git add skills/dead-code-audit/scripts/dead_code_audit.py skills/dead-code-audit/tests/test_dead_code_findings.py
git commit -m "feat: add dead-code-audit analysis (vulture + ruff F-codes)"
```

---

## Task 4: CLI, report, exit codes — TDD

**Files:** Modify `dead_code_audit.py` (append); test `tests/test_dead_code_cli.py`.

- [ ] **Step 1: Write the failing test**

Create `skills/dead-code-audit/tests/test_dead_code_cli.py`:
```python
from helpers import FIXTURES, read_findings, run_cli


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--allowlist" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli("--root", str(FIXTURES / "clean"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_dirty_exits_one_with_findings(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert all(d["signal"] == "DELETE" for d in data)
    assert (tmp_path / "dead-code_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "dead-code_findings.json").read_bytes() == (b / "dead-code_findings.json").read_bytes()


def test_missing_tool_exits_two(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--simulate-missing-tool")
    assert result.returncode == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/dead-code-audit && python3 -m pytest tests/test_dead_code_cli.py -v
```
Expected: FAIL — no CLI/`main` yet.

- [ ] **Step 3: Append CLI, report, and `main`**

Append to `skills/dead-code-audit/scripts/dead_code_audit.py`:
```python
def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# dead-code-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## DELETE ({len(findings)})")
    for f in findings:
        lines.append(f"- `{f.path}:{f.line_start}` {f.symbol} — {f.evidence_tool} [{f.severity}]")
    lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic dead-code audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds (min_confidence).")
    parser.add_argument("--allowlist", help="Vulture whitelist file to suppress false positives.")
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
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds, allowlist=args.allowlist)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "dead-code_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/dead-code-audit && python3 -m pytest tests/ -v
```
Expected: PASS (all dead-code-audit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/dead-code-audit/scripts/dead_code_audit.py skills/dead-code-audit/tests/test_dead_code_cli.py
git commit -m "feat: add dead-code-audit CLI, report, and exit codes"
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
];
```

- [ ] **Step 2: `check_release.py`**

```python
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
    "dead-code-audit": "dead-code-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
}
```

- [ ] **Step 3: `check_skill_fixtures.py`**

```python
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
    ["python3", "skills/dead-code-audit/scripts/dead_code_audit.py", "--help"],
]
```

- [ ] **Step 4: Run the full gate**

Run: `npm run check`
Expected: all checks pass; `check_release` lists three skills.

- [ ] **Step 5: Commit**

```bash
git add bin/install-code-health-skills.js scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "chore: register dead-code-audit in package machinery"
```

---

## Self-Review

- **Spec coverage:** §4 dead-code-audit (vulture + ruff F401/F811/F841, allowlist, confidence→severity) — Tasks 1–4. §5 rule-ownership non-overlap (vulture restricted to defs; imports/locals from ruff) — Task 3 + `test_vulture_does_not_report_imports_or_variables`. §3 schema/exit/byte-stable — Tasks 3–4. §7 registration — Tasks 1, 5. ✔
- **Placeholder scan:** none. `--simulate-missing-tool` is a documented test seam.
- **Type consistency:** `analyze_tree(root, source_prefixes, thresholds, allowlist=None)`, `DEFAULT_THRESHOLDS` key `min_confidence`, `OWNED_RUFF_CODES`, `LEAF="dead-code"` (note the findings file is `dead-code_findings.json`), and `hc.*` names match across analysis, CLI, and tests.
```
