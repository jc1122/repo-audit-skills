# coverage-gap-audit Implementation Plan (Sub-project 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build the `coverage-gap-audit` leaf skill (testedness: coverage.py JSON → `TEST` findings), gate the repo's own suites + testedness behind a fifth ratcheted check (`check:coverage`), then run a bounded self-refinement loop that adds tests for the package's own uncovered production scripts.

**Architecture:** A stdlib-only leaf in the established leaf shape (vendored `health_common.py`, fixtures, golden/CLI/relpath/idempotence tests) that *consumes* coverage reports rather than running tests. A repo gate script runs all 8 suites as separate pytest subprocesses under pytest-cov, combines coverage, runs the leaf production-scoped, and ratchets a frozen baseline — mechanizing the Actionability Rule. Phase 2 is a small convergence loop over that gate's actionable findings.

**Tech Stack:** Python (stdlib leaf), coverage==7.14.1 + pytest-cov==7.1.0 (gate only), pytest, npm gates.

**Spec:** `docs/superpowers/specs/2026-06-10-coverage-gap-audit-design.md`

**Environment:** repo root `/home/jakub/projects/repo-audit-skills`; `. .venv/bin/activate`. The venv's `pip`/`pytest` shims have stale shebangs — always use `.venv/bin/python -m pip` / `.venv/bin/python -m pytest`. One-time env prep (before Task 7): `.venv/bin/python -m pip install coverage==7.14.1 pytest-cov==7.1.0`.

**Standing ratchet rule (applies to EVERY task):** any task that adds or edits a production `.py` file under `scripts/`, `shared/`, or `skills/*/scripts/` will surface new self-audit findings (`check:selfaudit` fails with `new_findings`). Before committing: write the code ruff-clean (`ruff check --select E,W,F,B,SIM,UP` + `ruff format` it), then for residual structural findings (module-MI is expected on every new single-file tool) append a justified freeze line to `scripts/self_audit_frozen.md` and ratchet (`python3 scripts/self_audit.py && cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json`) **in the same commit**. `npm run check` must be green at every commit. Never touch `tests/fixtures/**` of existing skills; never edit `skills/test-*/scripts/**`.

---

## Task ordering (for the orchestrator)

Sequential chain (shared files / strict dependencies): **T1 → T2 → T3 → T4 → T5 → T7**.
Parallel lane (disjoint files, any time): **T6** (self_audit argparse), **T8** (docs).
Then **Phase 2 loop** (after T7), then **T9 release (LAST)**.
T1, T5, T7 (and possibly T6) touch the self-audit baseline/frozen log — never run two baseline-touching tasks concurrently.

---

# PHASE 1 — Build the skill + gates

## Task 1: `TEST` signal in the shared schema (+ re-vendor + ratchet)

**Files:**
- Modify: `shared/health_common.py` (SIGNALS frozenset, ~line 18)
- Modify: `skills/{complexity,duplication,dead-code,structure,quality}-audit/scripts/health_common.py` (re-vendor)
- Modify: `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` (EFFORT map, ~line 21)
- Test: `tests/test_health_common.py`, `skills/code-health-audit-pipeline/tests/test_pipeline_logic.py`
- Modify: `scripts/self_audit_baseline.json`, `scripts/self_audit_frozen.md` (ratchet churn)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_health_common.py`:

```python
def test_test_signal_is_in_schema():
    assert "TEST" in hc.SIGNALS
```

Append to `skills/code-health-audit-pipeline/tests/test_pipeline_logic.py` (the file already binds the pipeline module as `ch = load_module()` at the top — reuse it):

```python
def test_test_signal_has_effort_weight():
    assert ch.EFFORT["TEST"] == 3
```

- [ ] **Step 2: Run both to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health_common.py -q` → FAIL (`'TEST' in SIGNALS` assert).
Run: `cd skills/code-health-audit-pipeline && /home/jakub/projects/repo-audit-skills/.venv/bin/python -m pytest tests/test_pipeline_logic.py -q` → FAIL (KeyError `TEST`).

- [ ] **Step 3: Implement**

In `shared/health_common.py`, add `"TEST",` to the `SIGNALS` frozenset (after `"TYPE",`). In `code_health_pipeline.py`, add `"TEST": 3,` to `EFFORT` (after `"TYPE": 2,`).

- [ ] **Step 4: Re-vendor the shared file**

```bash
for d in complexity-audit duplication-audit dead-code-audit structure-audit quality-audit; do
  cp shared/health_common.py "skills/$d/scripts/health_common.py"
done
```

- [ ] **Step 5: Verify suites, then ratchet the expected churn**

Run every suite (root `tests/` + the 6 skill suites, each from its own directory) → all pass.
Run `npm run check` → `check:selfaudit` is EXPECTED to fail with symbol-churned `duplicate_tokens` findings (the shared file gained a line, shifting clone line-ranges). Verify the new findings are ONLY churned duplication symbols on `health_common.py`/pipeline files (no new metrics, no net growth beyond churn pairs), then:

```bash
python3 scripts/self_audit.py && cp scripts/self_audit_snapshot.json scripts/self_audit_baseline.json
```

Append to the Round log in `scripts/self_audit_frozen.md`:
`- **SP3-T1**: added TEST to SIGNALS + EFFORT; re-vendored; ratchet absorbed duplication line-range churn (no net new findings).`
Re-run `npm run check` → four "pass".

- [ ] **Step 6: Commit**

```bash
git add shared scripts/self_audit_baseline.json scripts/self_audit_frozen.md skills/*/scripts/health_common.py skills/code-health-audit-pipeline tests/test_health_common.py
git commit -m "feat(schema): add TEST signal for testedness findings

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 2: Scaffold `skills/coverage-gap-audit/`

**Files (all Create):** `skills/coverage-gap-audit/{SKILL.md,pyproject.toml,LICENSE,references/rubric.md,scripts/health_common.py,tests/helpers.py}`

- [ ] **Step 1: Create the directory tree and copy invariants**

```bash
mkdir -p skills/coverage-gap-audit/{scripts,references,tests/fixtures}
cp LICENSE skills/coverage-gap-audit/LICENSE
cp shared/health_common.py skills/coverage-gap-audit/scripts/health_common.py
```

- [ ] **Step 2: `skills/coverage-gap-audit/SKILL.md`**

````markdown
---
name: coverage-gap-audit
version: 0.1.0
description: >
  Deterministic, advisory testedness audit for Python. Consumes coverage.py JSON
  report(s) and emits TEST findings (shared code-health schema) for production
  files with no or insufficient test coverage. Never runs tests, never mutates
  source. The machine-readable answer to "is this file safe to refactor?".
---

# coverage-gap-audit

## Overview

A code-health leaf skill reporting under-tested files as advisory TEST findings.
It consumes existing coverage data; generate it first, e.g.:

```bash
python -m pytest tests -q --cov --cov-report= && python -m coverage json -o coverage.json
```

## Quick Start

```bash
python3 scripts/coverage_gap_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --coverage-json coverage.json \
  --out-dir /tmp/coverage-gap
```

`--coverage-json` is repeatable; multiple reports are merged (union of executed
lines, max statement count).

## Output

- `coverage-gap_findings.json` — sorted findings (shared schema).
- `coverage-gap_report.md` — summary.

## Findings

- `file_coverage_percent` 0% → severity high (untested file).
- `0% < pct < min_file_coverage` (default 50%) → severity medium.

## Exit Codes

- `0` clean, `1` advisory findings present, `2` tool/config error (missing or
  invalid coverage report).
````

- [ ] **Step 3: `skills/coverage-gap-audit/pyproject.toml`**

```toml
[project]
name = "coverage-gap-audit"
version = "0.1.0"
description = "Deterministic testedness audit leaf (coverage.py JSON -> TEST findings)."
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest==8.0", "coverage==7.14.1", "pytest-cov==7.1.0"]
```

- [ ] **Step 4: `skills/coverage-gap-audit/references/rubric.md`**

```markdown
# coverage-gap rubric

| condition | severity | confidence | meaning |
|---|---|---|---|
| file absent from all reports, or 0 executed lines | high | high | untested file |
| 0% < percent < min_file_coverage (default 50%) | medium | medium | under-tested file |
| percent >= min_file_coverage | — | — | no finding |

Merge rule across multiple `--coverage-json` reports: executed lines = union;
`num_statements` = max; files with 0 statements count as 100% covered.
Percent = `round(100 * |executed| / num_statements, 2)`.
Signal is always `TEST`; symbol is always `<file>`; line range is `1..1`.
```

- [ ] **Step 5: `skills/coverage-gap-audit/tests/helpers.py`**

```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "coverage_gap_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("coverage_gap_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False
    )


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "coverage-gap_findings.json").read_text())
```

- [ ] **Step 6: Commit**

```bash
git add skills/coverage-gap-audit
git commit -m "feat(coverage-gap): scaffold leaf skill (SKILL.md, pyproject, vendored common)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 3: Fixtures (frozen source trees + frozen coverage reports)

**Files (all Create):** under `skills/coverage-gap-audit/tests/fixtures/`:
`covered/pkg/mod.py`, `covered/coverage_full.json`, `uncovered/pkg/covered.py`, `uncovered/pkg/partial.py`, `uncovered/pkg/uncovered.py`, `uncovered/coverage_partial.json`, `uncovered/coverage_extra.json`

- [ ] **Step 1: The fully-covered tree**

`covered/pkg/mod.py`:
```python
def double(value):
    return 2 * value


def triple(value):
    return 3 * value
```

`covered/coverage_full.json` (handcrafted minimal coverage.py-shaped report; statements on lines 1, 2, 5, 6):
```json
{
  "files": {
    "pkg/mod.py": {
      "executed_lines": [1, 2, 5, 6],
      "summary": {"num_statements": 4}
    }
  }
}
```

- [ ] **Step 2: The gappy tree**

`uncovered/pkg/covered.py`:
```python
def used_everywhere(value):
    return value + 1


def also_used(value):
    return value - 1
```

`uncovered/pkg/partial.py` (8 statement lines: 1, 2, 5, 6, 7, 8, 9, 10):
```python
def used(value):
    return value + 1


def unused_branchy(value):
    if value > 0:
        value = value - 1
    if value > 10:
        value = value - 10
    return value
```

`uncovered/pkg/uncovered.py`:
```python
def never_imported():
    return "untested"
```

`uncovered/coverage_partial.json` (covered.py 100%, partial.py 2/8 = 25%, uncovered.py absent):
```json
{
  "files": {
    "pkg/covered.py": {
      "executed_lines": [1, 2, 5, 6],
      "summary": {"num_statements": 4}
    },
    "pkg/partial.py": {
      "executed_lines": [1, 2],
      "summary": {"num_statements": 8}
    }
  }
}
```

`uncovered/coverage_extra.json` (a second report finishing partial.py — used by the merge test):
```json
{
  "files": {
    "pkg/partial.py": {
      "executed_lines": [5, 6, 7, 8, 9, 10],
      "summary": {"num_statements": 8}
    }
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add skills/coverage-gap-audit/tests/fixtures
git commit -m "test(coverage-gap): frozen fixture trees + coverage reports

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 4: The leaf, via TDD

**Files:**
- Create: `skills/coverage-gap-audit/scripts/coverage_gap_audit.py`
- Test: `skills/coverage-gap-audit/tests/test_coverage_gap_findings.py`, `tests/test_coverage_gap_cli.py`, `tests/test_coverage_gap_relpaths.py`, `tests/test_coverage_gap_idempotent.py`

- [ ] **Step 1: Write the failing findings tests**

`skills/coverage-gap-audit/tests/test_coverage_gap_findings.py`:
```python
from helpers import FIXTURES, load_module

cg = load_module()
DEFAULTS = cg.DEFAULT_THRESHOLDS


def _analyze(tree, *reports):
    return cg.analyze_tree(
        FIXTURES / tree,
        source_prefixes=["pkg/"],
        thresholds=DEFAULTS,
        coverage_jsons=[str(FIXTURES / tree / r) for r in reports],
    )


def test_fully_covered_tree_yields_no_findings():
    assert _analyze("covered", "coverage_full.json") == []


def test_untested_file_is_high_severity_zero_percent():
    findings = {f.path: f for f in _analyze("uncovered", "coverage_partial.json")}
    f = findings["pkg/uncovered.py"]
    assert f.signal == "TEST"
    assert f.severity == "high"
    assert f.confidence == "high"
    assert f.metric_name == "file_coverage_percent"
    assert f.metric_value == 0.0
    assert f.symbol == "<file>"


def test_partially_covered_file_is_medium_severity():
    findings = {f.path: f for f in _analyze("uncovered", "coverage_partial.json")}
    f = findings["pkg/partial.py"]
    assert f.severity == "medium"
    assert f.metric_value == 25.0
    assert f.metric_threshold == 50.0


def test_covered_file_is_not_flagged():
    findings = {f.path for f in _analyze("uncovered", "coverage_partial.json")}
    assert "pkg/covered.py" not in findings
    assert findings == {"pkg/partial.py", "pkg/uncovered.py"}


def test_multiple_reports_merge_by_union():
    findings = {
        f.path
        for f in _analyze("uncovered", "coverage_partial.json", "coverage_extra.json")
    }
    assert findings == {"pkg/uncovered.py"}  # partial.py reaches 8/8 after the union
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd skills/coverage-gap-audit && /home/jakub/projects/repo-audit-skills/.venv/bin/python -m pytest tests/test_coverage_gap_findings.py -q`
Expected: FAIL/ERROR (`coverage_gap_audit.py` does not exist).

- [ ] **Step 3: Implement `scripts/coverage_gap_audit.py` (complete file)**

```python
#!/usr/bin/env python3
"""coverage-gap-audit leaf: coverage.py JSON report(s) -> TEST findings for
untested / under-tested files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "coverage-gap"

DEFAULT_THRESHOLDS = {
    "min_file_coverage": 50.0,
}


class ToolError(RuntimeError):
    pass


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [
        p
        for p in files
        if any(
            p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes
        )
    ]


def load_coverage(paths: list[str], root: Path) -> dict[str, dict]:
    """Merge coverage.py JSON reports keyed by root-relative posix path."""
    merged: dict[str, dict] = {}
    for raw in paths:
        try:
            report = json.loads(Path(raw).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"unreadable coverage report {raw}: {exc}") from exc
        files = report.get("files")
        if not isinstance(files, dict):
            raise ToolError(f"{raw} is not a coverage.py JSON report (no 'files' map)")
        for name, data in files.items():
            key = _rel(name, root)
            entry = merged.setdefault(key, {"executed": set(), "statements": 0})
            entry["executed"] |= set(data.get("executed_lines", []))
            summary = data.get("summary", {})
            entry["statements"] = max(
                entry["statements"], int(summary.get("num_statements", 0))
            )
    return merged


def _coverage_percent(entry: dict | None) -> float:
    if entry is None:
        return 0.0
    if entry["statements"] == 0:
        return 100.0
    return round(100.0 * len(entry["executed"]) / entry["statements"], 2)


def analyze_tree(
    root, source_prefixes, thresholds, coverage_jsons
) -> list[hc.Finding]:
    root = Path(root)
    merged = load_coverage(list(coverage_jsons), root)
    minimum = float(thresholds["min_file_coverage"])
    findings: list[hc.Finding] = []
    for path in _iter_python_files(root, list(source_prefixes or [])):
        rel = path.relative_to(root).as_posix()
        pct = _coverage_percent(merged.get(rel))
        if pct >= minimum:
            continue
        untested = pct == 0.0
        entry = merged.get(rel)
        if entry is None:
            evidence = "absent from all coverage reports"
        else:
            evidence = (
                f"{len(entry['executed'])}/{entry['statements']} statements executed"
            )
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="TEST",
                severity="high" if untested else "medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol="<file>",
                metric_name="file_coverage_percent",
                metric_value=pct,
                metric_threshold=minimum,
                evidence_tool="coverage",
                evidence_raw=evidence,
                confidence="high" if untested else "medium",
                suggested_action=f"Add behavior tests covering {rel} "
                f"(coverage {pct}% < {minimum}%)",
            )
        )
    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# coverage-gap-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## TEST ({len(findings)})")
    for f in findings:
        lines.append(
            f"- `{f.path}` {f.metric_value}% covered — {f.evidence_raw} [{f.severity}]"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic testedness audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument(
        "--coverage-json",
        action="append",
        default=[],
        dest="coverage_jsons",
        help="coverage.py JSON report. Repeatable; reports are merged.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--config", help="JSON file overriding thresholds (min_file_coverage)."
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir or not args.coverage_jsons:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "--root, --out-dir and --coverage-json are required",
                }
            )
        )
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(
            args.root, args.source_prefixes, thresholds, args.coverage_jsons
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "coverage-gap_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run findings tests** → all 5 PASS.

- [ ] **Step 5: Write the CLI tests, run them**

`skills/coverage-gap-audit/tests/test_coverage_gap_cli.py`:
```python
from helpers import FIXTURES, read_findings, run_cli


def _dirty_args(out):
    return (
        "--root", str(FIXTURES / "uncovered"),
        "--source-prefix", "pkg/",
        "--coverage-json", str(FIXTURES / "uncovered" / "coverage_partial.json"),
        "--out-dir", str(out),
    )


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--coverage-json" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli(
        "--root", str(FIXTURES / "covered"),
        "--source-prefix", "pkg/",
        "--coverage-json", str(FIXTURES / "covered" / "coverage_full.json"),
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_gappy_exits_one_with_findings(tmp_path):
    result = run_cli(*_dirty_args(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert all(d["signal"] == "TEST" for d in data)
    assert (tmp_path / "coverage-gap_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli(*_dirty_args(a))
    run_cli(*_dirty_args(b))
    assert (a / "coverage-gap_findings.json").read_bytes() == (
        b / "coverage-gap_findings.json"
    ).read_bytes()


def test_missing_coverage_report_exits_two(tmp_path):
    result = run_cli(
        "--root", str(FIXTURES / "covered"),
        "--coverage-json", str(tmp_path / "nope.json"),
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 2
    assert "unreadable coverage report" in result.stdout


def test_missing_required_args_exits_two(tmp_path):
    result = run_cli("--root", str(FIXTURES / "covered"), "--out-dir", str(tmp_path))
    assert result.returncode == 2
```

Run: suite → PASS.

- [ ] **Step 6: relpath + idempotence tests**

`skills/coverage-gap-audit/tests/test_coverage_gap_relpaths.py` (absolute keys in the report must come out root-relative):
```python
import json

from helpers import run_cli, read_findings


def test_absolute_report_paths_are_emitted_relative(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text("def f():\n    return 1\n")
    report = {
        "files": {
            str(pkg / "m.py"): {
                "executed_lines": [1],
                "summary": {"num_statements": 2},
            }
        }
    }
    (tmp_path / "cov.json").write_text(json.dumps(report))
    out = tmp_path / "out"
    run_cli(
        "--root", str(tmp_path), "--source-prefix", "pkg/",
        "--coverage-json", str(tmp_path / "cov.json"), "--out-dir", str(out),
    )
    data = read_findings(out)
    assert data, "expected a partial-coverage finding"
    assert all(not f["path"].startswith("/") for f in data), [f["path"] for f in data]
```

`skills/coverage-gap-audit/tests/test_coverage_gap_idempotent.py`:
```python
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "coverage_gap_audit.py"
DIRTY = SKILL / "tests" / "fixtures" / "uncovered"


def _run(out):
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(DIRTY),
         "--source-prefix", "pkg/",
         "--coverage-json", str(DIRTY / "coverage_partial.json"),
         "--out-dir", str(out)],
        text=True, capture_output=True, timeout=180, check=False,
    )
    return (out / "coverage-gap_findings.json").read_bytes()


def test_byte_identical_across_runs(tmp_path):
    assert _run(tmp_path / "a") == _run(tmp_path / "b")
```

- [ ] **Step 7: Run the full new suite**

Run: `cd skills/coverage-gap-audit && /home/jakub/projects/repo-audit-skills/.venv/bin/python -m pytest tests/ -q` → all PASS (13 tests).

- [ ] **Step 8: Commit**

```bash
git add skills/coverage-gap-audit
git commit -m "feat(coverage-gap): testedness leaf via TDD (findings/CLI/relpath/idempotence)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 5: Register the skill in the package machinery (+ ratchet)

**Files:**
- Modify: `scripts/check_release.py:17-38` (both dicts), `scripts/check_skill_fixtures.py:14-32` (HELP_COMMANDS), `bin/install-repo-audit-skills.js:10-20` (skills array), `README.md` (skill list, if present)
- Modify: `scripts/self_audit_baseline.json`, `scripts/self_audit_frozen.md` (standing ratchet rule — the new leaf script is now in self-audit scope)

- [ ] **Step 1: Register**

`check_release.py`: add `"coverage-gap-audit": "coverage-gap-audit",` to `REQUIRED_SKILLS` and `"coverage-gap-audit": ["scripts/coverage_gap_audit.py"],` to `REQUIRED_SCRIPTS`.
`check_skill_fixtures.py`: append `["python3", "skills/coverage-gap-audit/scripts/coverage_gap_audit.py", "--help"],` to `HELP_COMMANDS`.
`bin/install-repo-audit-skills.js`: add `"coverage-gap-audit",` to the `skills` array.
`README.md`: add one line describing the skill next to the other leaves (match existing list format).

- [ ] **Step 2: Verify registration**

Run: `node bin/install-repo-audit-skills.js --list` → `skills` includes `coverage-gap-audit`.
Run: `npm run check` → `check:vendored` now also checks the new vendored copy (glob-discovered); `check:fixtures` and `check:release` pass (SKILL.md version 0.1.0 == package 0.1.0); `check:selfaudit` is EXPECTED to fail — the new leaf script entered the auto-discovered production scope.

- [ ] **Step 3: Apply the standing ratchet rule**

Inspect `new_findings`: expected are findings on `skills/coverage-gap-audit/scripts/coverage_gap_audit.py` only — certainly `maintainability_index :: <module>`, likely `duplicate_tokens` clones of the other leaves' argparse/`_rel`/`_iter_python_files` idioms. Fix any plain lint (E501 etc.) outright. Then append freeze lines to `scripts/self_audit_frozen.md` section D (module-MI: "whole-module metric on an intentionally single-file standalone tool") and section C (clones: "cross-leaf CLI/parse idiom; dedup needs forbidden cross-skill imports (see R2 evidence)"), ratchet, and re-run `npm run check` → four "pass".

- [ ] **Step 4: Commit**

```bash
git add scripts bin/install-repo-audit-skills.js README.md skills/coverage-gap-audit
git commit -m "feat(coverage-gap): register skill in release/fixtures/installer machinery

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 6 (parallel lane): give `scripts/self_audit.py` a real CLI

**Files:**
- Modify: `scripts/self_audit.py`
- Test: `tests/test_self_audit_cli.py` (Create)

- [ ] **Step 1: Failing test**

`tests/test_self_audit_cli.py`:
```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "self_audit.py"


def test_help_exits_zero_fast_without_running_the_audit():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_unknown_argument_is_rejected():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--bogus"],
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert result.returncode == 2
```

- [ ] **Step 2: Verify it fails**

Run: `.venv/bin/python -m pytest tests/test_self_audit_cli.py -q` → FAIL (today `--help` runs a full ~30s audit and prints `{"status": "ok", ...}`; the 10s timeout or the `usage:` assert trips).

- [ ] **Step 3: Implement**

In `scripts/self_audit.py`, add at the top with the other imports: `import argparse`. Replace `def main() -> int:` with:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the code-health pipeline over this package's production "
        "code and write scripts/self_audit_snapshot.json."
    )
    parser.parse_args(argv)
    findings = run(ROOT / ".self_audit_out")
    SNAPSHOT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "count": len(findings)}))
    return 0
```

(argparse exits 0 on `--help` and 2 on unknown args before the audit body runs.)

- [ ] **Step 4: Verify**

Run: `.venv/bin/python -m pytest tests/ -q` → PASS. Run `npm run check` → four "pass" (the snapshot content is unchanged; if `check:selfaudit` flags churn from the edited file's own metrics, apply the standing ratchet rule).

- [ ] **Step 5: Commit**

```bash
git add scripts/self_audit.py tests/test_self_audit_cli.py
git commit -m "fix(self-audit): argparse CLI so --help no longer runs a full audit

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 7: `check:coverage` gate — suites under pytest-cov + ratcheted testedness baseline

**Files:**
- Create: `.coveragerc`, `scripts/check_coverage_gap.py`, `scripts/coverage_gap_baseline.json`, `tests/test_check_coverage_gap.py`
- Modify: `package.json` (scripts), `scripts/check_release.py` (required-files list), `.gitignore`, `scripts/self_audit_frozen.md` (+ self-audit ratchet per standing rule)

- [ ] **Step 0: Env prep (once)**

```bash
.venv/bin/python -m pip install coverage==7.14.1 pytest-cov==7.1.0
```

- [ ] **Step 1: `.coveragerc`**

```ini
[run]
relative_files = True
source =
    scripts
    shared
    skills
omit =
    */tests/*
    */fixtures/*

[json]
pretty_print = False
```

- [ ] **Step 2: `scripts/check_coverage_gap.py` (complete file)**

```python
#!/usr/bin/env python3
"""Testedness gate: run every suite under coverage, then ratchet the
coverage-gap findings against scripts/coverage_gap_baseline.json."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / "skills" / "coverage-gap-audit" / "scripts" / "coverage_gap_audit.py"
OUT = ROOT / ".self_audit_out" / "coverage"
SNAPSHOT = ROOT / "scripts" / "coverage_gap_snapshot.json"
BASELINE = ROOT / "scripts" / "coverage_gap_baseline.json"
RCFILE = ROOT / ".coveragerc"
SUITES = [
    "tests",
    "skills/complexity-audit/tests",
    "skills/duplication-audit/tests",
    "skills/dead-code-audit/tests",
    "skills/structure-audit/tests",
    "skills/quality-audit/tests",
    "skills/code-health-audit-pipeline/tests",
    "skills/coverage-gap-audit/tests",
]
SUITE_TIMEOUT = 600


def _prefixes() -> list[str]:
    pres = ["shared", "scripts"]
    for d in sorted((ROOT / "skills").iterdir()):
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres


def run_suites_with_coverage() -> tuple[Path, dict[str, int]]:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob(".coverage*"):
        stale.unlink()
    env = dict(os.environ, COVERAGE_FILE=str(OUT / ".coverage"))
    results: dict[str, int] = {}
    for suite in SUITES:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", suite, "-q", "-p", "no:cacheprovider",
             "--cov", "--cov-append", "--cov-report=", f"--cov-config={RCFILE}"],
            cwd=ROOT, env=env, text=True, capture_output=True,
            timeout=SUITE_TIMEOUT, check=False,
        )
        results[suite] = proc.returncode
    coverage_json = OUT / "coverage.json"
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", str(coverage_json),
         f"--rcfile={RCFILE}"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=120, check=False,
    )
    return coverage_json, results


def run_leaf(coverage_json: Path) -> list[dict]:
    cmd = [sys.executable, str(LEAF), "--root", str(ROOT),
           "--out-dir", str(OUT / "leaf"), "--coverage-json", str(coverage_json)]
    for p in _prefixes():
        cmd += ["--source-prefix", p]
    proc = subprocess.run(
        cmd, cwd=ROOT, text=True, capture_output=True, timeout=300, check=False
    )
    if proc.returncode == 2:
        print(json.dumps({"status": "fail", "leaf_error": proc.stdout.strip()}))
        raise SystemExit(1)
    findings = json.loads(
        (OUT / "leaf" / "coverage-gap_findings.json").read_text(encoding="utf-8")
    )
    return sorted(
        ({"path": f["path"], "metric": f["metric"]["name"]} for f in findings),
        key=lambda d: (d["path"], d["metric"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all suites under coverage and ratchet testedness findings."
    )
    parser.add_argument(
        "--coverage-json",
        help="Use an existing coverage.py JSON report instead of running suites "
        "(testing/debugging only).",
    )
    args = parser.parse_args(argv)
    suite_results: dict[str, int] = {}
    if args.coverage_json:
        coverage_json = Path(args.coverage_json)
    else:
        coverage_json, suite_results = run_suites_with_coverage()
        failed = {s: rc for s, rc in suite_results.items() if rc != 0}
        if failed:
            print(json.dumps({"status": "fail", "failed_suites": failed}, indent=2))
            return 1
    current = run_leaf(coverage_json)
    SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    base = {tuple(sorted(d.items())) for d in baseline}
    new = [d for d in current if tuple(sorted(d.items())) not in base]
    if new:
        print(json.dumps({"status": "fail", "new_findings": new}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "suites": len(suite_results) or None,
                "count": len(current),
                "baseline": len(baseline),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: First real run — inspect, then freeze the baseline**

```bash
printf '[]\n' > scripts/coverage_gap_baseline.json
python3 scripts/check_coverage_gap.py
```
Expected: `"status": "fail"` with `new_findings` listing (a) all `skills/test-*/scripts/*.py` files, (b) some `scripts/*.py` gate scripts. Sanity-check the OPPOSITE direction — these files must NOT appear (they are covered; if any does, pytest-cov subprocess tracing is broken — STOP and investigate before freezing): `shared/health_common.py`, the six code-health leaf scripts, `skills/coverage-gap-audit/scripts/coverage_gap_audit.py`. Then freeze:
```bash
cp scripts/coverage_gap_snapshot.json scripts/coverage_gap_baseline.json
python3 scripts/check_coverage_gap.py   # now "status": "pass", count == baseline
```
Append to `scripts/self_audit_frozen.md` a new section:
```markdown
## Coverage-gap baseline (initial freeze, SP3-T7)

Rule: entries under `skills/test-*/scripts/` are frozen by the Actionability Rule
(spec SP3 decision 9) until Sub-project 4 writes their tests. All other entries are
the Phase 2 worklist and must be fixed (tests added) or individually justified below.
```

- [ ] **Step 4: Root test for the gate (uses injection mode — never runs suites)**

`tests/test_check_coverage_gap.py`:
```python
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage_gap.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True, capture_output=True, timeout=120, check=False,
    )


def test_help_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_empty_coverage_report_fails_the_ratchet(tmp_path):
    report = tmp_path / "cov.json"
    report.write_text(json.dumps({"files": {}}))
    result = _run("--coverage-json", str(report))
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["new_findings"], "zero coverage must surface new findings"
```

Run: `.venv/bin/python -m pytest tests/test_check_coverage_gap.py -q` → PASS.
Then re-run `python3 scripts/check_coverage_gap.py` once more (the test overwrote the snapshot) → `"status": "pass"`.

- [ ] **Step 5: Wire the gate**

`package.json`: add `"check:coverage": "python3 scripts/check_coverage_gap.py"` and append `&& npm run check:coverage` to `"check"`.
`scripts/check_release.py` `check_package` list: add `"scripts/check_coverage_gap.py"` and `"scripts/coverage_gap_baseline.json"`.
`.gitignore`: add `scripts/coverage_gap_snapshot.json` (the `.self_audit_out/` entry already covers the work dir).

- [ ] **Step 6: Verify + standing ratchet rule**

Run: `npm run check` → FIVE `"status": "pass"` blocks. `check:selfaudit` will first flag the new `check_coverage_gap.py` (module-MI at minimum): apply the standing ratchet rule (freeze + ratchet) before this commit. Note: `check:coverage` runs the full suite set (~30-60s) — this is the gate that finally puts the 75+ tests behind `npm run check`.

- [ ] **Step 7: Commit**

```bash
git add .coveragerc scripts/check_coverage_gap.py scripts/coverage_gap_baseline.json tests/test_check_coverage_gap.py package.json scripts/check_release.py .gitignore scripts/self_audit_baseline.json scripts/self_audit_frozen.md
git commit -m "feat(gates): check:coverage — suites under pytest-cov + ratcheted testedness baseline

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

## Task 8 (parallel lane): runbook docs

**Files:** Create `docs/self-audit/coverage-gap.md`

- [ ] **Step 1: Write it**

```markdown
# Testedness gate (check:coverage)

`npm run check:coverage` (part of `npm run check`) does three things:
1. Runs every pytest suite (root + 7 skills) as separate processes under
   pytest-cov (separate processes — the suites collide if collected together).
2. Combines coverage into `.self_audit_out/coverage/coverage.json`.
3. Runs the coverage-gap-audit leaf over the production scope and ratchets the
   normalized findings against `scripts/coverage_gap_baseline.json`.

A finding here = an under-tested production file = NOT safe to refactor.
This is the machine-readable Actionability Rule from the dogfooding run.

To use the leaf on a target repo:

    python -m pytest tests -q --cov --cov-report= && python -m coverage json -o coverage.json
    python3 skills/coverage-gap-audit/scripts/coverage_gap_audit.py \
      --root . --source-prefix src/ --coverage-json coverage.json --out-dir /tmp/covgap
```

- [ ] **Step 2: Commit**

```bash
git add docs/self-audit/coverage-gap.md
git commit -m "docs: testedness gate runbook

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

# PHASE 2 — Self-refinement loop (PROTOCOL, orchestrator-driven)

**Precondition:** Tasks 1-8 merged; `npm run check` green with FIVE gates; `coverage_gap_baseline.json` frozen.

**Round (repeat, max 4 rounds, cap 4 findings/round):**
1. Run `python3 scripts/check_coverage_gap.py`; read `scripts/coverage_gap_snapshot.json`.
2. **Actionable** = entries whose `path` is NOT under `skills/test-*/scripts/` (those stay rule-frozen until Sub-project 4). Expected initial worklist: `scripts/check_release.py`, `scripts/check_skill_fixtures.py`, `scripts/check_self_audit.py`, `scripts/self_audit.py`, possibly `scripts/check_coverage_gap.py` and `scripts/check_vendored_common.py` (partial).
3. One worker per finding, own worktree. The worker **either**:
   - **ADD TESTS** (preferred): a root `tests/test_<name>.py` exercising the script's observable contract (JSON stdout shape, exit codes, pass/fail paths) until the file clears `min_file_coverage` (50%). Pattern to follow: `tests/test_check_vendored_common.py`. Subprocess invocations are fine — pytest-cov traces them. **Or**
   - **FREEZE**: append `path :: coverage-gap/file_coverage_percent :: reason` under the "Coverage-gap baseline" section of `scripts/self_audit_frozen.md` (concrete reason required).
4. **Accept** only if, in the worktree: `npm run check` green (all FIVE gates) and the root suite passes. Else discard.
5. Merge accepted; re-run `python3 scripts/check_coverage_gap.py`; ratchet (`cp scripts/coverage_gap_snapshot.json scripts/coverage_gap_baseline.json`); commit baseline + any frozen-log lines; `npm run check` green.
6. Record net change (files newly covered + frozen).

**Stop:** converged (actionable coverage-gap set empty), 4-round bound, or a no-progress round.

**Caution:** new root tests put the gate scripts in coverage for the first time — the snapshot only shrinks. If it ever GROWS, a test was deleted or a new untested production file appeared: STOP and investigate.

---

## Task 9: Release prep 0.2.0 (LAST — after the loop)

**Files:** Modify `package.json` (version), all TEN `skills/*/SKILL.md` (`version:` frontmatter)

- [ ] **Step 1: Bump versions atomically**

```bash
python3 - <<'EOF'
import json, re
from pathlib import Path
pkg = Path("package.json")
data = json.loads(pkg.read_text())
data["version"] = "0.2.0"
pkg.write_text(json.dumps(data, indent=2) + "\n")
for md in Path("skills").glob("*/SKILL.md"):
    md.write_text(re.sub(r"^version: .*$", "version: 0.2.0", md.read_text(), count=1, flags=re.M))
EOF
```

- [ ] **Step 2: Verify the full gate set + pack**

Run: `npm run check` → FIVE `"status": "pass"` (check:release validates every SKILL.md version == 0.2.0).
Run: `npm run pack:dry-run` → tarball listing includes `skills/coverage-gap-audit/**` and `scripts/check_coverage_gap.py`, and NO `__pycache__`/`.pytest_cache` entries.

- [ ] **Step 3: Commit (do NOT push)**

```bash
git add package.json skills/*/SKILL.md
git commit -m "release: v0.2.0 — coverage-gap-audit (testedness leaf + check:coverage gate)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**Post-run HUMAN steps (not the orchestrator's):** review the branch, `git push`, tag/publish if desired, reinstall locally via `node bin/install-repo-audit-skills.js --force`.

---

## Definition of Done

1. `npm run check` green with **FIVE** gates (`check:vendored`, `check:fixtures`, `check:release`, `check:selfaudit`, `check:coverage`).
2. The new skill's suite (13+ tests: findings, CLI, relpath, idempotence) passes from its own directory; the leaf is stdlib-only at runtime; fixtures are frozen and committed.
3. `"TEST" in SIGNALS` in `shared/health_common.py`; all SIX vendored copies byte-identical (`check:vendored` lists 6).
4. `check:coverage` runs all 8 suites as separate pytest subprocesses under pytest-cov (CLI subprocesses traced — verified by leaf scripts NOT appearing in the snapshot), emits one combined `coverage.json`, and ratchets `coverage_gap_baseline.json`; a failing suite fails the gate.
5. `self_audit.py --help` exits 0 in <10s without running the audit (test passes).
6. The skill is registered everywhere: `check_release` dicts, `check_skill_fixtures` HELP_COMMANDS, installer `--list`, README.
7. Phase 2 loop converged (actionable coverage-gap set empty) or hit the 4-round bound; every frozen entry has a concrete justification in `scripts/self_audit_frozen.md`; baseline ratcheted and committed each round.
8. Version 0.2.0 in `package.json` and all ten SKILL.md; `npm pack --dry-run` clean; nothing pushed.
9. Run report: per-task gate evidence, per-round net change, final baseline counts (self-audit + coverage-gap), justification list for all new freezes.

## Out of scope (per spec)

Umbrella `leaf_registry.json` integration (deferred — the umbrella cannot supply `--coverage-json`); function-level coverage; mutation testing; writing tests for `skills/test-*/scripts` (Sub-project 4); touching `tests/fixtures/**` of any existing skill; changing any existing tool's output contract.
