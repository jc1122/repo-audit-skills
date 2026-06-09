# Plan 2 — duplication-audit leaf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `duplication-audit` leaf — deterministic copy-paste clone detection emitting EXTRACT / MERGE findings to the shared schema.

**Architecture:** Wraps `jscpd` (token-based clone detector, JSON reporter). One finding per jscpd clone **pair**: clone spanning two different files → `EXTRACT`, clone within one file → `MERGE`. Self-contained leaf following the pattern established in Plan 1 (vendored `health_common.py`, advisory-only, byte-stable output).

**Tech Stack:** Python 3.10+, Node ≥18 (`jscpd` via `npx`), `pytest`.

**Prerequisite:** Plan 1 is complete and `npm run check` is green. Work in `/home/jakub/projects/code-health-skills`.

**Design note (deviation from spec §4):** jscpd reports duplicates pairwise. This plan emits one finding per pair rather than unioning pairs into N-way clone groups. This is deterministic and simpler (YAGNI); N-way grouping can be added later without changing the schema.

---

## File Structure (this plan)

```
skills/duplication-audit/
├─ SKILL.md
├─ LICENSE
├─ pyproject.toml
├─ scripts/
│  ├─ health_common.py            # vendored copy of shared/health_common.py
│  └─ duplication_audit.py
├─ references/rubric.md
└─ tests/
   ├─ helpers.py
   ├─ fixtures/clean/pkg/a.py
   ├─ fixtures/dirty/pkg/a.py
   ├─ fixtures/dirty/pkg/b.py
   ├─ test_duplication_findings.py
   └─ test_duplication_cli.py
```

Modified (registry appends): `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`.

---

## Task 1: Scaffold the skill + vendor the helper

**Files:**
- Create: `skills/duplication-audit/{SKILL.md,LICENSE,pyproject.toml,references/rubric.md}`
- Create (vendored): `skills/duplication-audit/scripts/health_common.py`

- [ ] **Step 1: Create dirs and vendor the helper**

Run:
```bash
mkdir -p skills/duplication-audit/scripts skills/duplication-audit/references skills/duplication-audit/tests/fixtures
cp shared/health_common.py skills/duplication-audit/scripts/health_common.py
cp LICENSE skills/duplication-audit/LICENSE
```
Expected: `skills/duplication-audit/scripts/health_common.py` is byte-identical to `shared/health_common.py`.

- [ ] **Step 2: Create `pyproject.toml`**

Create `skills/duplication-audit/pyproject.toml`:
```toml
[project]
name = "duplication-audit"
version = "0.1.0"
description = "Deterministic copy-paste clone audit leaf (jscpd)."
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```

- [ ] **Step 3: Create `references/rubric.md`**

Create `skills/duplication-audit/references/rubric.md`:
```markdown
# duplication-audit Rubric

Clone detection via `jscpd` (token-based). One finding per clone pair.

| Condition | Threshold | Severity | Signal |
|---|---|---|---|
| Clone across two files | tokens > min | medium | EXTRACT |
| Clone within one file | tokens > min | medium | MERGE |
| Large clone | tokens > 3× min | high | EXTRACT/MERGE |

Defaults: `min_tokens=50`, `min_lines=5` (override via `--config`). Confidence is
`high` (deterministic). The leaf never mutates source.
```

- [ ] **Step 4: Create `SKILL.md`**

Create `skills/duplication-audit/SKILL.md`:
```markdown
---
name: duplication-audit
version: 0.1.0
description: >
  Deterministic, advisory copy-paste clone audit for Python. Uses jscpd to detect
  duplicated token sequences and emits EXTRACT (cross-file) / MERGE (same-file)
  findings to the shared code-health finding schema. Never mutates source.
---

# duplication-audit

## Overview

A code-health leaf skill. It reports duplicated code blocks as advisory findings; it
does not refactor anything.

## Quick Start

```bash
python3 scripts/duplication_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/duplication
```

## Output

- `duplication_findings.json` — sorted findings (shared schema).
- `duplication_report.md` — summary grouped by signal.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error (e.g. jscpd/node missing).

## Tools and Thresholds

`jscpd` via `npx`. See `references/rubric.md`. Override with `--config thresholds.json`
(keys `min_tokens`, `min_lines`).

## Notes

- `--source-prefix` filters to product code (repeatable).
- Findings are deterministic: identical input yields byte-identical
  `duplication_findings.json`.
- One finding per clone pair (cross-file → EXTRACT, same-file → MERGE).
```

- [ ] **Step 5: Commit**

```bash
git add skills/duplication-audit
git commit -m "feat: scaffold duplication-audit skill"
```

---

## Task 2: Fixtures + helpers

**Files:**
- Create: clean + dirty fixtures, `tests/helpers.py`

- [ ] **Step 1: Create the clean fixture**

Create `skills/duplication-audit/tests/fixtures/clean/pkg/a.py`:
```python
def alpha(x):
    return x + 1


def beta(y):
    return y * 2
```

- [ ] **Step 2: Create the dirty fixtures (a cross-file clone)**

Create `skills/duplication-audit/tests/fixtures/dirty/pkg/a.py`:
```python
def process_records(records):
    cleaned = []
    for record in records:
        if record is None:
            continue
        name = record.get("name", "").strip().lower()
        value = record.get("value", 0)
        if value < 0:
            value = 0
        cleaned.append({"name": name, "value": value, "ok": True})
    return cleaned
```

Create `skills/duplication-audit/tests/fixtures/dirty/pkg/b.py`:
```python
def normalize_rows(records):
    cleaned = []
    for record in records:
        if record is None:
            continue
        name = record.get("name", "").strip().lower()
        value = record.get("value", 0)
        if value < 0:
            value = 0
        cleaned.append({"name": name, "value": value, "ok": True})
    return cleaned
```

The shared loop body (≈9 lines / well over 50 tokens) appears in both files → one
cross-file EXTRACT finding.

- [ ] **Step 3: Create `helpers.py`**

Create `skills/duplication-audit/tests/helpers.py`:
```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "duplication_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("duplication_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "duplication_findings.json").read_text())
```

- [ ] **Step 4: Commit**

```bash
git add skills/duplication-audit/tests
git commit -m "test: add duplication-audit fixtures and helpers"
```

---

## Task 3: Analysis logic — TDD

**Files:**
- Create: `skills/duplication-audit/scripts/duplication_audit.py`
- Test: `skills/duplication-audit/tests/test_duplication_findings.py`

Requires Node + jscpd reachable via `npx` (the script calls `npx --yes jscpd`). The
missing-tool path is covered in Task 4.

- [ ] **Step 1: Write the failing test**

Create `skills/duplication-audit/tests/test_duplication_findings.py`:
```python
from helpers import FIXTURES, load_module

da = load_module()
DEFAULTS = da.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = da.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_flags_cross_file_extract():
    findings = da.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings, "expected at least one duplication finding"
    assert any(f.signal == "EXTRACT" for f in findings)
    f = next(f for f in findings if f.signal == "EXTRACT")
    assert f.metric_name == "duplicate_tokens"
    assert f.metric_value >= DEFAULTS["min_tokens"]
    assert f.confidence == "high"
    assert {f.path, f.symbol.split(":")[0]} == {"pkg/a.py", "pkg/b.py"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/duplication-audit && python3 -m pytest tests/test_duplication_findings.py -v
```
Expected: FAIL — `duplication_audit.py` does not exist.

- [ ] **Step 3: Write the analysis module**

Create `skills/duplication-audit/scripts/duplication_audit.py`:
```python
#!/usr/bin/env python3
"""duplication-audit leaf: jscpd clone detection → EXTRACT/MERGE findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "duplication"

DEFAULT_THRESHOLDS = {
    "min_tokens": 50,
    "min_lines": 5,
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _run_jscpd(root: Path, files: list[Path], thresholds: dict, out_dir: Path) -> dict:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = [
        "npx", "--yes", "jscpd", "--silent",
        "--reporters", "json", "--output", str(out_dir),
        "--min-tokens", str(thresholds["min_tokens"]),
        "--min-lines", str(thresholds["min_lines"]),
        *rel_files,
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("npx/node is not installed (needed to run jscpd)") from exc
    report_path = out_dir / "jscpd-report.json"
    if not report_path.exists():
        raise ToolError(f"jscpd produced no report: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _findings_from_report(report: dict, root: Path, thresholds: dict) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    min_tokens = thresholds["min_tokens"]
    for dup in report.get("duplicates", []):
        ff, sf = dup["firstFile"], dup["secondFile"]
        p1, p2 = _rel(ff["name"], root), _rel(sf["name"], root)
        tokens = int(dup.get("tokens", 0))
        signal = "MERGE" if p1 == p2 else "EXTRACT"
        severity = "high" if tokens > 3 * min_tokens else "medium"
        symbol = f"{p2}:{sf['start']}-{sf['end']}"
        findings.append(hc.Finding(
            leaf=LEAF, signal=signal, severity=severity, path=p1,
            line_start=int(ff["start"]), line_end=int(ff["end"]), symbol=symbol,
            metric_name="duplicate_tokens", metric_value=float(tokens),
            metric_threshold=float(min_tokens),
            evidence_tool="jscpd",
            evidence_raw=f"{p1}:{ff['start']}-{ff['end']} == {p2}:{sf['start']}-{sf['end']} ({tokens} tokens)",
            confidence="high",
            suggested_action=(
                f"Extract shared code between {p1} and {p2}" if signal == "EXTRACT"
                else f"Merge duplicated block within {p1}"
            ),
        ))
    return findings


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        report = _run_jscpd(root, files, thresholds, Path(tmp))
    return hc.sort_findings(_findings_from_report(report, root, thresholds))
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/duplication-audit && python3 -m pytest tests/test_duplication_findings.py -v
```
Expected: PASS. If it errors on `npx`, ensure Node ≥18 is installed and network is available for `npx --yes jscpd` (or pre-install: `npm i -g jscpd`).

- [ ] **Step 5: Commit**

```bash
git add skills/duplication-audit/scripts/duplication_audit.py skills/duplication-audit/tests/test_duplication_findings.py
git commit -m "feat: add duplication-audit analysis (jscpd)"
```

---

## Task 4: CLI, report, exit codes — TDD

**Files:**
- Modify: `skills/duplication-audit/scripts/duplication_audit.py` (append)
- Test: `skills/duplication-audit/tests/test_duplication_cli.py`

- [ ] **Step 1: Write the failing test**

Create `skills/duplication-audit/tests/test_duplication_cli.py`:
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
    assert any(d["signal"] == "EXTRACT" for d in data)
    assert (tmp_path / "duplication_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "duplication_findings.json").read_bytes() == (b / "duplication_findings.json").read_bytes()


def test_missing_tool_exits_two(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--simulate-missing-tool")
    assert result.returncode == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd skills/duplication-audit && python3 -m pytest tests/test_duplication_cli.py -v
```
Expected: FAIL — no CLI/`main` yet.

- [ ] **Step 3: Append CLI, report, and `main`**

Append to `skills/duplication-audit/scripts/duplication_audit.py`:
```python
def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# duplication-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(f"- `{f.path}:{f.line_start}` ↔ `{f.symbol}` — {f.metric_value:g} tokens [{f.severity}]")
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic duplication audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds (min_tokens, min_lines).")
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
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "duplication_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd skills/duplication-audit && python3 -m pytest tests/ -v
```
Expected: PASS (all duplication-audit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/duplication-audit/scripts/duplication_audit.py skills/duplication-audit/tests/test_duplication_cli.py
git commit -m "feat: add duplication-audit CLI, report, and exit codes"
```

---

## Task 5: Register in package machinery + green the gate

**Files:**
- Modify: `bin/install-code-health-skills.js`, `scripts/check_release.py`, `scripts/check_skill_fixtures.py`

- [ ] **Step 1: Add to the installer `skills[]`**

In `bin/install-code-health-skills.js`, change the `skills` array to:
```javascript
const skills = [
  "complexity-audit",
  "duplication-audit",
];
```

- [ ] **Step 2: Add to `check_release.py`**

In `scripts/check_release.py`, update the two dicts:
```python
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
}
```

- [ ] **Step 3: Add to `check_skill_fixtures.py`**

In `scripts/check_skill_fixtures.py`, update `HELP_COMMANDS`:
```python
HELP_COMMANDS = [
    ["python3", "skills/complexity-audit/scripts/complexity_audit.py", "--help"],
    ["python3", "skills/duplication-audit/scripts/duplication_audit.py", "--help"],
]
```

- [ ] **Step 4: Run the full gate**

Run: `npm run check`
Expected: all three checks pass; `check_release` lists both `complexity-audit` and `duplication-audit`; `check_vendored_common` confirms the new vendored copy matches.

- [ ] **Step 5: Commit**

```bash
git add bin/install-code-health-skills.js scripts/check_release.py scripts/check_skill_fixtures.py
git commit -m "chore: register duplication-audit in package machinery"
```

---

## Self-Review

- **Spec coverage:** §4 duplication-audit (jscpd, EXTRACT/MERGE, min-tokens/lines) — Tasks 1–4. §3 shared schema + exit codes + byte-stable output — Tasks 3–4. §7 registration + vendored-copy rule — Tasks 1, 5. ✔
- **Deviation logged:** pairwise findings instead of N-way groups (header note). Schema unchanged, so N-way grouping is a later, non-breaking enhancement.
- **Placeholder scan:** none. `--simulate-missing-tool` is a documented test seam.
- **Type consistency:** `analyze_tree(root, source_prefixes, thresholds)`, `DEFAULT_THRESHOLDS` keys (`min_tokens`, `min_lines`), `LEAF="duplication"`, and `hc.*` names match across analysis, CLI, and tests.
```
