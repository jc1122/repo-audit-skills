"""Tests for exec-audit leaf.

All fixtures are built under tmp_path; no static fixture files.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess as sp
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Paths to the skill
SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "exec_audit.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module():
    """Load exec_audit as a module for in-process testing."""
    spec = importlib.util.spec_from_file_location("exec_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_cli(*args: str) -> sp.CompletedProcess[str]:
    return sp.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _read_findings(out_dir: Path) -> list[dict]:
    fp = out_dir / "exec-audit_findings.json"
    if not fp.exists():
        return []
    return json.loads(fp.read_text())


def _make_node_skeleton(tmp_path: Path) -> Path:
    """Create a minimal non-Python Node.js project with distinct test and lint scripts."""
    repo = tmp_path / "node_skel"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "node-skel",
                "scripts": {
                    "test": "jest",
                    "lint": "eslint .",
                    "build": "tsc",
                    "ci": "npm run test && npm run lint",
                },
            }
        )
    )
    return repo


def _make_dup_npm_repo(tmp_path: Path) -> Path:
    """Create a repo whose npm scripts cause duplicate execution after expansion."""
    repo = tmp_path / "dup_npm"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "dup-npm",
                "scripts": {
                    "test": "jest",
                    "test:unit": "npm run test",
                    "test:all": "npm run test && npm run test:unit",
                },
            }
        )
    )
    return repo


def _make_junit_xml(out_dir: Path, cases: list[dict]) -> Path:
    """Write a minimal JUnit XML file with the given testcases.

    Each case dict: name, classname, time (seconds as float or str).
    """
    xml_path = out_dir / "junit.xml"
    root = ET.Element("testsuite", name="pytest", tests=str(len(cases)))
    for c in cases:
        tc = ET.SubElement(
            root,
            "testcase",
            name=c["name"],
            classname=c.get("classname", ""),
            time=str(c.get("time", 0)),
        )
    tree = ET.ElementTree(root)
    tree.write(str(xml_path), encoding="unicode", xml_declaration=True)
    return xml_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dup_npm_invocation_is_detected(tmp_path):
    """Duplicate npm test invocation → PERF finding with signal PERF."""
    repo = _make_dup_npm_repo(tmp_path)
    out_dir = tmp_path / "out"
    result = _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    data = _read_findings(out_dir)
    perf = [f for f in data if f["signal"] == "PERF" and f["metric"]["name"] == "duplicate_execution"]
    assert len(perf) >= 1, f"expected >=1 duplicate_execution PERF finding, got {data}"


def test_node_skeleton_no_duplicate_execution(tmp_path):
    """Non-Python node skeleton with distinct test/lint has no duplicate_execution rows."""
    repo = _make_node_skeleton(tmp_path)
    out_dir = tmp_path / "out"
    result = _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    # May exit 1 (for benchmark_entrypoints_missing) but must not have duplicate_execution
    data = _read_findings(out_dir)
    dup_exec = [f for f in data if f["metric"]["name"] == "duplicate_execution"]
    assert len(dup_exec) == 0, f"unexpected duplicate_execution findings: {dup_exec}"


def test_degenerate_repo_only_benchmark_gap(tmp_path):
    """Degenerate (empty) repo emits only benchmark_entrypoints_missing rows, if any."""
    repo = tmp_path / "empty"
    repo.mkdir()
    out_dir = tmp_path / "out"
    result = _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    data = _read_findings(out_dir)
    # All findings must be benchmark_entrypoints_missing
    non_bem = [f for f in data if f["metric"]["name"] != "benchmark_entrypoints_missing"]
    assert len(non_bem) == 0, f"unexpected non-benchmark-gap findings: {non_bem}"
    # At most one benchmark_entrypoints_missing
    bem = [f for f in data if f["metric"]["name"] == "benchmark_entrypoints_missing"]
    assert len(bem) <= 1, f"expected ≤1 benchmark_entrypoints_missing, got {len(bem)}"


def test_junit_slow_test_detection(tmp_path):
    """JUnit XML with one slow and one fast testcase → exactly one slow_test row."""
    junit = _make_junit_xml(
        tmp_path,
        [
            {"name": "test_fast", "classname": "tests.test_foo", "time": 0.1},
            {"name": "test_slow", "classname": "tests.test_bar", "time": 5.5},
        ],
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    result = _run_cli(
        "--root", str(repo),
        "--out-dir", str(out_dir),
        "--junit-xml", str(junit),
    )
    data = _read_findings(out_dir)
    slow = [f for f in data if f["metric"]["name"] == "slow_test"]
    assert len(slow) == 1, f"expected exactly 1 slow_test finding, got {len(slow)}: {data}"
    s = slow[0]
    assert s["metric"]["value"] == 5.5, f"expected duration 5.5, got {s['metric']['value']}"
    assert "test_slow" in s["location"]["symbol"], f"expected test_slow in symbol, got {s['location']['symbol']}"


def test_help_exits_zero():
    """--help exits 0 and mentions --root."""
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout


def test_missing_required_args_exits_two(tmp_path):
    """Missing --root or --out-dir → exit 2 with error status."""
    mod = _load_module()
    # No args at all
    rc = mod.main([])
    assert rc == 2, f"expected exit 2, got {rc}"


def test_clean_python_project_stdout_ok(tmp_path):
    """A clean Python project dir (no package.json) exits with status ok."""
    repo = tmp_path / "clean"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')\n")
    out_dir = tmp_path / "out"
    result = _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    status = json.loads(result.stdout.strip())
    assert status["status"] == "ok"
    assert status["leaf"] == "exec-audit"


def test_junit_file_not_found_exits_two(tmp_path):
    """Referencing a non-existent JUnit file → exit 2 ToolError."""
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    result = _run_cli(
        "--root", str(repo),
        "--out-dir", str(out_dir),
        "--junit-xml", str(tmp_path / "nope.xml"),
    )
    assert result.returncode == 2
    status = json.loads(result.stdout.strip())
    assert status["status"] == "error"


def test_output_contract_leaf_and_filename(tmp_path):
    """Regression: output file is exec-audit_findings.json, every finding has leaf='exec-audit'."""
    repo = _make_dup_npm_repo(tmp_path)
    out_dir = tmp_path / "out"
    result = _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    assert result.returncode == 1

    # Old filename must not exist
    old_path = out_dir / "exec_findings.json"
    assert not old_path.exists(), (
        f"old filename {old_path} must not exist after rename to exec-audit"
    )

    # New filename must exist
    new_path = out_dir / "exec-audit_findings.json"
    assert new_path.exists(), f"{new_path} must exist"

    data = json.loads(new_path.read_text(encoding="utf-8"))
    assert len(data) >= 1, "expected at least one finding"

    for f in data:
        assert f["leaf"] == "exec-audit", (
            f"every finding must have leaf='exec-audit', got {f['leaf']!r}"
        )
