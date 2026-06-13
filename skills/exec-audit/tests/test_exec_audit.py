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

import pytest

# Paths to the skill
SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "exec_audit.py"
VENDORED_HC = SKILL_ROOT / "scripts" / "health_common.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module():
    """Load exec_audit as a module for in-process testing."""
    spec = importlib.util.spec_from_file_location("exec_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_vendored_hc():
    """Load the vendored health_common.py for coverage."""
    spec = importlib.util.spec_from_file_location("hc_vendored_exec", VENDORED_HC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # needed so dataclass resolves annotations
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
        ET.SubElement(
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
# Subprocess contract tests (preserved from original)
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
    _run_cli("--root", str(repo), "--out-dir", str(out_dir))
    # May exit 1 (for benchmark_entrypoints_missing) but must not have duplicate_execution
    data = _read_findings(out_dir)
    dup_exec = [f for f in data if f["metric"]["name"] == "duplicate_execution"]
    assert len(dup_exec) == 0, f"unexpected duplicate_execution findings: {dup_exec}"


def test_degenerate_repo_only_benchmark_gap(tmp_path):
    """Degenerate (empty) repo emits only benchmark_entrypoints_missing rows, if any."""
    repo = tmp_path / "empty"
    repo.mkdir()
    out_dir = tmp_path / "out"
    _run_cli("--root", str(repo), "--out-dir", str(out_dir))
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
    _run_cli(
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


# ---------------------------------------------------------------------------
# In-process coverage tests: module loading
# ---------------------------------------------------------------------------


def test_load_module_in_process():
    """Module loads and exposes LEAF constant and key functions."""
    mod = _load_module()
    assert mod.LEAF == "exec-audit"
    assert callable(mod._load_package_json)
    assert callable(mod._expand_npm_script)
    assert callable(mod._split_atomic)
    assert callable(mod._runner_of)
    assert callable(mod._duplicate_findings)


# ---------------------------------------------------------------------------
# In-process: _load_package_json
# ---------------------------------------------------------------------------


def test_load_package_json_valid(tmp_path):
    """Load a valid package.json."""
    mod = _load_module()
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "test", "scripts": {"test": "jest"}}')
    result = mod._load_package_json(tmp_path)
    assert result == {"name": "test", "scripts": {"test": "jest"}}


def test_load_package_json_missing(tmp_path):
    """Return None for missing package.json."""
    mod = _load_module()
    result = mod._load_package_json(tmp_path)
    assert result is None


def test_load_package_json_invalid_json(tmp_path):
    """Return None for invalid JSON."""
    mod = _load_module()
    pkg = tmp_path / "package.json"
    pkg.write_text("not json")
    result = mod._load_package_json(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# In-process: _expand_npm_script
# ---------------------------------------------------------------------------


def test_expand_npm_script_simple():
    """Expand a simple npm script (no nesting)."""
    mod = _load_module()
    scripts = {"test": "jest", "lint": "eslint ."}
    result = mod._expand_npm_script(scripts, "test")
    assert result == "jest"


def test_expand_npm_script_recursive():
    """Recursively expand npm run references."""
    mod = _load_module()
    scripts = {
        "test": "jest",
        "test:unit": "npm run test",
        "test:all": "npm run test && npm run test:unit",
    }
    result = mod._expand_npm_script(scripts, "test:all")
    assert result == "jest && jest"


def test_expand_npm_script_cycle_detection():
    """Cycle of npm run references returns empty string."""
    mod = _load_module()
    scripts = {"a": "npm run b", "b": "npm run a"}
    result = mod._expand_npm_script(scripts, "a")
    assert result == ""


def test_expand_npm_script_depth_limit():
    """Depth > 20 returns empty string."""
    mod = _load_module()
    # Chain of 22 scripts; depth from script0 → script21 > 20
    scripts = {f"script{i}": f"npm run script{i+1}" for i in range(21)}
    scripts["script21"] = "echo done"
    result = mod._expand_npm_script(scripts, "script0")
    assert result == ""


def test_expand_npm_script_missing_script():
    """Non-existent script returns empty string."""
    mod = _load_module()
    result = mod._expand_npm_script({}, "nonexistent")
    assert result == ""


def test_expand_npm_script_unknown_inner():
    """Inner npm run to missing script leaves reference untouched."""
    mod = _load_module()
    scripts = {"a": "npm run missing"}
    result = mod._expand_npm_script(scripts, "a")
    assert "npm run missing" in result


# ---------------------------------------------------------------------------
# In-process: _split_atomic
# ---------------------------------------------------------------------------


def test_split_atomic_basic():
    """Split on && and ;."""
    mod = _load_module()
    result = mod._split_atomic("jest && eslint . ; tsc")
    assert result == ["jest", "eslint .", "tsc"]


def test_split_atomic_empty():
    """Empty string produces empty list."""
    mod = _load_module()
    result = mod._split_atomic("")
    assert result == []


def test_split_atomic_whitespace_only():
    """Whitespace-only chunks are stripped out."""
    mod = _load_module()
    result = mod._split_atomic("  jest  &&  && eslint")
    assert result == ["jest", "eslint"]


# ---------------------------------------------------------------------------
# In-process: _runner_of
# ---------------------------------------------------------------------------


def test_runner_of_basic():
    """Extract runner from command."""
    mod = _load_module()
    assert mod._runner_of("jest --coverage") == "jest"
    assert mod._runner_of("   eslint .  ") == "eslint"
    assert mod._runner_of("") == ""


def test_runner_of_path():
    """Runner with path."""
    mod = _load_module()
    assert mod._runner_of("./node_modules/.bin/jest") == "./node_modules/.bin/jest"


# ---------------------------------------------------------------------------
# In-process: _duplicate_findings
# ---------------------------------------------------------------------------


def test_duplicate_findings_detected(tmp_path):
    """Duplicate runners produce findings."""
    mod = _load_module()
    scripts = {
        "test": "jest",
        "test:unit": "npm run test",
        "test:all": "npm run test && npm run test:unit",
    }
    findings = mod._duplicate_findings(tmp_path, scripts)
    assert len(findings) >= 1
    f = findings[0]
    assert f.signal == "PERF"
    assert f.metric_name == "duplicate_execution"
    assert f.leaf == "exec-audit"
    assert f.confidence == "high"


def test_duplicate_findings_no_dupes(tmp_path):
    """Distinct runners produce no findings."""
    mod = _load_module()
    scripts = {"test": "jest", "lint": "eslint ."}
    findings = mod._duplicate_findings(tmp_path, scripts)
    assert findings == []


# ---------------------------------------------------------------------------
# In-process: _parse_junit
# ---------------------------------------------------------------------------


def test_parse_junit_valid(tmp_path):
    """Parse valid JUnit XML."""
    mod = _load_module()
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<testsuite name="pytest" tests="2">'
        '<testcase name="test_a" classname="tests.test_mod" time="0.5"/>'
        '<testcase name="test_b" classname="tests.test_mod" time="2.0"/>'
        "</testsuite>"
    )
    cases = mod._parse_junit(xml_path)
    assert len(cases) == 2
    assert cases[0]["name"] == "test_a"
    assert cases[0]["duration"] == 0.5
    assert cases[1]["classname"] == "tests.test_mod"
    assert cases[1]["duration"] == 2.0


def test_parse_junit_invalid_xml(tmp_path):
    """Invalid XML raises ToolError."""
    mod = _load_module()
    xml_path = tmp_path / "junk.xml"
    xml_path.write_text("not xml")
    with pytest.raises(mod.ToolError):
        mod._parse_junit(xml_path)


def test_parse_junit_missing_time_attribute(tmp_path):
    """Missing time attribute defaults to 0.0."""
    mod = _load_module()
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<testsuite name="pytest" tests="1">'
        '<testcase name="test_a" classname="tests.test_mod"/>'
        "</testsuite>"
    )
    cases = mod._parse_junit(xml_path)
    assert len(cases) == 1
    assert cases[0]["duration"] == 0.0


# ---------------------------------------------------------------------------
# In-process: _slow_test_findings
# ---------------------------------------------------------------------------


def test_slow_test_findings(tmp_path):
    """Detect slow tests above threshold."""
    mod = _load_module()
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<testsuite name="pytest" tests="2">'
        '<testcase name="test_fast" classname="tests.test_mod" time="0.1"/>'
        '<testcase name="test_slow" classname="tests.test_mod" time="5.0"/>'
        "</testsuite>"
    )
    thresholds = {"slow_test_threshold_s": 1.0, "slow_test_cap_s": 300.0}
    findings = mod._slow_test_findings([str(xml_path)], thresholds)
    assert len(findings) == 1
    f = findings[0]
    assert f.metric_name == "slow_test"
    assert f.metric_value == 5.0
    assert f.signal == "PERF"
    assert f.severity == "medium"


def test_slow_test_findings_none_above_threshold(tmp_path):
    """No findings when all tests under threshold."""
    mod = _load_module()
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<testsuite name="pytest" tests="1">'
        '<testcase name="test_fast" classname="tests.test_mod" time="0.5"/>'
        "</testsuite>"
    )
    thresholds = {"slow_test_threshold_s": 1.0, "slow_test_cap_s": 300.0}
    findings = mod._slow_test_findings([str(xml_path)], thresholds)
    assert findings == []


# ---------------------------------------------------------------------------
# In-process: _has_benchmark_marker
# ---------------------------------------------------------------------------


def test_has_benchmark_marker_none(tmp_path):
    """Empty directory has no benchmark marker."""
    mod = _load_module()
    assert mod._has_benchmark_marker(tmp_path) is False


def test_has_benchmark_marker_requirements_pytest_benchmark(tmp_path):
    """Detect pytest-benchmark in requirements-dev.txt."""
    mod = _load_module()
    (tmp_path / "requirements-dev.txt").write_text("pytest-benchmark\n")
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_pyproject(tmp_path):
    """Detect pytest-benchmark in pyproject.toml."""
    mod = _load_module()
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]\nrequires = ['pytest-benchmark']\n")
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_package_json_bench_script(tmp_path):
    """Detect bench script in package.json."""
    mod = _load_module()
    (tmp_path / "package.json").write_text('{"scripts": {"bench": "jest --bench"}}')
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_package_json_benchmark_script(tmp_path):
    """Detect benchmark script in package.json."""
    mod = _load_module()
    (tmp_path / "package.json").write_text('{"scripts": {"benchmark": "echo"}}')
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_scope_script(tmp_path):
    """Detect bench:xxx scope script in package.json."""
    mod = _load_module()
    (tmp_path / "package.json").write_text('{"scripts": {"bench:perf": "node perf.js"}}')
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_benchmarks_dir(tmp_path):
    """Detect benchmarks/ directory."""
    mod = _load_module()
    (tmp_path / "benchmarks").mkdir()
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_bench_dir(tmp_path):
    """Detect bench/ directory."""
    mod = _load_module()
    (tmp_path / "bench").mkdir()
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_conftest_pytest_benchmark(tmp_path):
    """Detect pytest benchmark in conftest.py."""
    mod = _load_module()
    conftest = tmp_path / "conftest.py"
    conftest.write_text("import pytest\npytest_plugins = ['pytest-benchmark']\n")
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_test_file_benchmark_mark(tmp_path):
    """Detect pytest.mark.benchmark in test files."""
    mod = _load_module()
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_perf.py").write_text("import pytest\n@pytest.mark.benchmark\ndef test_x(): pass\n")
    assert mod._has_benchmark_marker(tmp_path) is True


def test_has_benchmark_marker_makefile(tmp_path):
    """Detect benchmark target in Makefile."""
    mod = _load_module()
    (tmp_path / "Makefile").write_text("benchmark:\n\tpytest --benchmark\n")
    assert mod._has_benchmark_marker(tmp_path) is True


# ---------------------------------------------------------------------------
# In-process: _benchmark_gap_finding
# ---------------------------------------------------------------------------


def test_benchmark_gap_finding_when_missing(tmp_path):
    """Emit finding when no benchmark marker exists."""
    mod = _load_module()
    finding = mod._benchmark_gap_finding(tmp_path)
    assert finding is not None
    assert finding.metric_name == "benchmark_entrypoints_missing"
    assert finding.signal == "PERF"
    assert finding.severity == "info"
    assert finding.confidence == "low"
    assert finding.leaf == "exec-audit"


def test_benchmark_gap_finding_when_present(tmp_path):
    """Return None when benchmark marker exists."""
    mod = _load_module()
    (tmp_path / "bench").mkdir()
    finding = mod._benchmark_gap_finding(tmp_path)
    assert finding is None


# ---------------------------------------------------------------------------
# In-process: _render_report
# ---------------------------------------------------------------------------


def test_render_report_empty():
    """Render report with no findings."""
    mod = _load_module()
    report = mod._render_report([])
    assert "# exec-audit report" in report
    assert "No findings" in report


def test_render_report_with_findings():
    """Render report with findings includes signal sections."""
    mod = _load_module()
    finding = mod.hc.Finding(
        leaf="exec-audit",
        signal="PERF",
        severity="medium",
        path="test.py",
        line_start=1,
        line_end=1,
        symbol="test_sym",
        metric_name="test_metric",
        metric_value=1.0,
        metric_threshold=0.5,
        evidence_tool="test",
        evidence_raw="test evidence",
        confidence="high",
        suggested_action="fix it",
    )
    report = mod._render_report([finding])
    assert "# exec-audit report" in report
    assert "## PERF" in report
    assert "test_metric" in report


# ---------------------------------------------------------------------------
# In-process: _load_thresholds
# ---------------------------------------------------------------------------


def test_load_thresholds_default():
    """Default thresholds when no config file."""
    mod = _load_module()
    t = mod._load_thresholds(None)
    assert t["slow_test_threshold_s"] == 1.0
    assert t["slow_test_cap_s"] == 300.0
    assert t["max_runner_occurrences"] == 1


def test_load_thresholds_from_file(tmp_path):
    """Merge config values with defaults."""
    mod = _load_module()
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"slow_test_threshold_s": 2.0}')
    t = mod._load_thresholds(str(cfg))
    assert t["slow_test_threshold_s"] == 2.0
    assert t["max_runner_occurrences"] == 1  # default preserved


def test_load_thresholds_invalid_config(tmp_path):
    """Invalid config file raises ToolError."""
    mod = _load_module()
    cfg = tmp_path / "cfg.json"
    cfg.write_text("not json")
    with pytest.raises(mod.ToolError):
        mod._load_thresholds(str(cfg))


# ---------------------------------------------------------------------------
# In-process: _analyze
# ---------------------------------------------------------------------------


def test_analyze_empty_repo(tmp_path):
    """_analyze on empty repo returns benchmark gap finding."""
    mod = _load_module()
    findings = mod._analyze(tmp_path, [], dict(mod.DEFAULT_THRESHOLDS))
    assert isinstance(findings, list)
    # With empty repo, at most benchmark gap
    for f in findings:
        assert f.leaf == "exec-audit"


def test_analyze_with_junit(tmp_path):
    """_analyze with JUnit XML file processes slow tests."""
    mod = _load_module()
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<?xml version="1.0"?>'
        '<testsuite name="pytest" tests="1">'
        '<testcase name="test_fast" classname="tests.test_mod" time="0.1"/>'
        "</testsuite>"
    )
    findings = mod._analyze(tmp_path, [str(xml_path)], dict(mod.DEFAULT_THRESHOLDS))
    assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# In-process: _build_parser
# ---------------------------------------------------------------------------


def test_build_parser():
    """Parser is created with expected arguments."""
    mod = _load_module()
    parser = mod._build_parser()
    assert parser is not None
    # Parse known flags
    ns = parser.parse_args(["--root", "/tmp", "--out-dir", "/tmp/out"])
    assert ns.root == "/tmp"
    assert ns.out_dir == "/tmp/out"
    assert ns.format == "json"


# ---------------------------------------------------------------------------
# In-process: main function paths
# ---------------------------------------------------------------------------


def test_main_in_process_missing_args():
    """main([]) returns exit 2."""
    mod = _load_module()
    rc = mod.main([])
    assert rc == 2


def test_main_in_process_with_args(tmp_path):
    """main with root and out-dir succeeds."""
    mod = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n")
    out_dir = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc in (0, 1)
    # findings JSON should be written
    assert (out_dir / "exec-audit_findings.json").exists()
    # markdown report always written
    assert (out_dir / "exec-audit_report.md").exists()


def test_main_in_process_invalid_junit(tmp_path):
    """main with missing JUnit file exits 2."""
    mod = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    rc = mod.main([
        "--root", str(repo),
        "--out-dir", str(out_dir),
        "--junit-xml", str(tmp_path / "nope.xml"),
    ])
    assert rc == 2


def test_main_in_process_config_error(tmp_path):
    """main with invalid config file exits 2."""
    mod = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    cfg = tmp_path / "bad.json"
    cfg.write_text("not json")
    rc = mod.main([
        "--root", str(repo),
        "--out-dir", str(out_dir),
        "--config", str(cfg),
    ])
    assert rc == 2


# ======================================================================
# In-process tests (coverage for exec_audit.py and its vendored health_common.py)
# ======================================================================


class TestLoadPackageJson:
    """Coverage: _load_package_json."""

    def test_valid(self, tmp_path):
        mod = _load_module()
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "p", "scripts": {"test": "jest"}})
        )
        result = mod._load_package_json(tmp_path)
        assert result == {"name": "p", "scripts": {"test": "jest"}}

    def test_missing(self, tmp_path):
        mod = _load_module()
        assert mod._load_package_json(tmp_path) is None

    def test_invalid_json(self, tmp_path):
        mod = _load_module()
        (tmp_path / "package.json").write_text("not json")
        assert mod._load_package_json(tmp_path) is None


class TestExpandNpmScript:
    """Coverage: _expand_npm_script."""

    def test_simple(self):
        mod = _load_module()
        scripts = {"test": "jest"}
        assert mod._expand_npm_script(scripts, "test") == "jest"

    def test_recursive_expansion(self):
        mod = _load_module()
        scripts = {
            "test": "jest",
            "test:unit": "npm run test",
            "test:all": "npm run test && npm run test:unit",
        }
        result = mod._expand_npm_script(scripts, "test:all")
        assert result == "jest && jest"

    def test_cycle_detection(self):
        mod = _load_module()
        scripts = {"a": "npm run b", "b": "npm run a"}
        assert mod._expand_npm_script(scripts, "a") == ""

    def test_depth_limit(self):
        mod = _load_module()
        scripts = {}
        for i in range(25):
            scripts[f"s{i}"] = f"npm run s{i+1}"
        scripts["s24"] = "echo done"
        assert mod._expand_npm_script(scripts, "s0") == ""

    def test_missing_script(self):
        mod = _load_module()
        assert mod._expand_npm_script({}, "nope") == ""

    def test_nonexistent_inner(self):
        mod = _load_module()
        scripts = {"a": "npm run b"}
        # 'b' is not in scripts, so the inner ref stays as-is
        result = mod._expand_npm_script(scripts, "a")
        assert "npm run b" in result


class TestSplitAtomic:
    """Coverage: _split_atomic."""

    def test_ampersand_and_semicolon(self):
        mod = _load_module()
        parts = mod._split_atomic("jest && eslint . ; tsc")
        assert parts == ["jest", "eslint .", "tsc"]

    def test_empty(self):
        mod = _load_module()
        assert mod._split_atomic("") == []

    def test_only_whitespace(self):
        mod = _load_module()
        assert mod._split_atomic("   ") == []


class TestRunnerOf:
    """Coverage: _runner_of."""

    def test_extracts_runner(self):
        mod = _load_module()
        assert mod._runner_of("jest --coverage") == "jest"
        assert mod._runner_of("  eslint . ") == "eslint"

    def test_empty_string(self):
        mod = _load_module()
        assert mod._runner_of("") == ""


class TestDuplicateFindings:
    """Coverage: _duplicate_findings (PERF signal for duplicate runners)."""

    def test_detects_duplicate_jest(self, tmp_path):
        mod = _load_module()
        scripts = {
            "test": "jest",
            "test:unit": "npm run test",
            "test:all": "npm run test && npm run test:unit",
        }
        findings = mod._duplicate_findings(tmp_path, scripts)
        assert len(findings) >= 1
        f = findings[0]
        assert f.signal == "PERF"
        assert f.metric_name == "duplicate_execution"
        assert f.leaf == "exec-audit"

    def test_no_duplicates(self, tmp_path):
        mod = _load_module()
        scripts = {"test": "jest", "lint": "eslint ."}
        findings = mod._duplicate_findings(tmp_path, scripts)
        assert findings == []


class TestParseJunit:
    """Coverage: _parse_junit."""

    def test_valid_xml(self, tmp_path):
        mod = _load_module()
        xml_path = _make_junit_xml(
            tmp_path,
            [
                {"name": "t1", "classname": "TestMod", "time": 0.5},
                {"name": "t2", "classname": "TestMod", "time": 2.0},
            ],
        )
        cases = mod._parse_junit(xml_path)
        assert len(cases) == 2
        assert cases[0]["duration"] == 0.5
        assert cases[0]["name"] == "t1"

    def test_invalid_xml(self, tmp_path):
        mod = _load_module()
        p = tmp_path / "bad.xml"
        p.write_text("not xml")
        with pytest.raises(mod.ToolError, match="cannot parse"):
            mod._parse_junit(p)


class TestSlowTestFindings:
    """Coverage: _slow_test_findings."""

    def test_flags_slow_only(self, tmp_path):
        mod = _load_module()
        xml_path = _make_junit_xml(
            tmp_path,
            [
                {"name": "fast", "classname": "T", "time": 0.1},
                {"name": "slow", "classname": "T", "time": 5.5},
            ],
        )
        findings = mod._slow_test_findings(
            [str(xml_path)],
            {"slow_test_threshold_s": 1.0, "slow_test_cap_s": 300.0},
        )
        slow = [f for f in findings if f.metric_name == "slow_test"]
        assert len(slow) == 1
        assert slow[0].metric_value == 5.5

    def test_all_fast(self, tmp_path):
        mod = _load_module()
        xml_path = _make_junit_xml(
            tmp_path,
            [{"name": "fast", "classname": "T", "time": 0.1}],
        )
        findings = mod._slow_test_findings(
            [str(xml_path)],
            {"slow_test_threshold_s": 1.0, "slow_test_cap_s": 300.0},
        )
        slow = [f for f in findings if f.metric_name == "slow_test"]
        assert len(slow) == 0

    def test_file_not_found(self, tmp_path):
        mod = _load_module()
        with pytest.raises(mod.ToolError, match="not found"):
            mod._slow_test_findings(
                [str(tmp_path / "nope.xml")],
                {"slow_test_threshold_s": 1.0, "slow_test_cap_s": 300.0},
            )


class TestHasBenchmarkMarker:
    """Coverage: _has_benchmark_marker — various marker detection paths."""

    def test_empty_dir_false(self, tmp_path):
        mod = _load_module()
        assert mod._has_benchmark_marker(tmp_path) is False

    def test_requirements_dev(self, tmp_path):
        mod = _load_module()
        (tmp_path / "requirements-dev.txt").write_text("pytest-benchmark\n")
        assert mod._has_benchmark_marker(tmp_path) is True

    def test_pyproject_toml(self, tmp_path):
        mod = _load_module()
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\npytest-benchmark\n"
        )
        assert mod._has_benchmark_marker(tmp_path) is True

    def test_bench_dir(self, tmp_path):
        mod = _load_module()
        (tmp_path / "benchmarks").mkdir()
        assert mod._has_benchmark_marker(tmp_path) is True

    def test_package_json_bench_script(self, tmp_path):
        mod = _load_module()
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"bench": "node bench.js"}})
        )
        assert mod._has_benchmark_marker(tmp_path) is True

    def test_conftest_benchmark(self, tmp_path):
        mod = _load_module()
        (tmp_path / "conftest.py").write_text(
            "import pytest\npytest_plugins = ['pytest_benchmark']\n"
        )
        assert mod._has_benchmark_marker(tmp_path) is True

    def test_test_file_marker(self, tmp_path):
        mod = _load_module()
        (tmp_path / "test_bench.py").write_text(
            "import pytest\n@pytest.mark.benchmark\ndef test_x(): pass\n"
        )
        assert mod._has_benchmark_marker(tmp_path) is True


class TestBenchmarkGapFinding:
    """Coverage: _benchmark_gap_finding."""

    def test_emits_when_no_marker(self, tmp_path):
        mod = _load_module()
        f = mod._benchmark_gap_finding(tmp_path)
        assert f is not None
        assert f.metric_name == "benchmark_entrypoints_missing"
        assert f.signal == "PERF"
        assert f.severity == "info"
        assert f.confidence == "low"

    def test_none_when_marker_present(self, tmp_path):
        mod = _load_module()
        (tmp_path / "bench").mkdir()
        assert mod._benchmark_gap_finding(tmp_path) is None


class TestRenderReport:
    """Coverage: _render_report."""

    def test_empty(self):
        mod = _load_module()
        r = mod._render_report([])
        assert "# exec-audit report" in r
        assert "No findings" in r

    def test_with_findings(self, tmp_path):
        mod = _load_module()
        f = _make_one_finding(mod)
        r = mod._render_report([f])
        assert "PERF" in r
        assert "test_metric" in r


class TestLoadThresholdsInProcess:
    """Coverage: _load_thresholds."""

    def test_defaults(self):
        mod = _load_module()
        t = mod._load_thresholds(None)
        assert t["slow_test_threshold_s"] == 1.0

    def test_from_file(self, tmp_path):
        mod = _load_module()
        (tmp_path / "cfg.json").write_text('{"slow_test_threshold_s": 3.0}')
        t = mod._load_thresholds(str(tmp_path / "cfg.json"))
        assert t["slow_test_threshold_s"] == 3.0
        # other defaults preserved
        assert t["max_runner_occurrences"] == 1

    def test_invalid_config(self, tmp_path):
        mod = _load_module()
        (tmp_path / "cfg.json").write_text("bad")
        with pytest.raises(mod.ToolError, match="invalid"):
            mod._load_thresholds(str(tmp_path / "cfg.json"))


class TestAnalyzeInProcess:
    """Coverage: _analyze."""

    def test_empty_dir(self, tmp_path):
        mod = _load_module()
        findings = mod._analyze(tmp_path, [], mod.DEFAULT_THRESHOLDS)
        assert isinstance(findings, list)
        # should have at most benchmark_entrypoints_missing
        for f in findings:
            assert f.leaf == "exec-audit"

    def test_with_package_json_no_dupes(self, tmp_path):
        mod = _load_module()
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest", "lint": "eslint"}})
        )
        findings = mod._analyze(tmp_path, [], mod.DEFAULT_THRESHOLDS)
        dup = [f for f in findings if f.metric_name == "duplicate_execution"]
        assert len(dup) == 0


class TestBuildParserInProcess:
    """Coverage: _build_parser."""

    def test_creates_parser(self):
        mod = _load_module()
        parser = mod._build_parser()
        assert parser is not None

    def test_help(self):
        mod = _load_module()
        parser = mod._build_parser()
        import io

        try:
            parser.print_help(io.StringIO())
        except SystemExit:
            pass  # argparse may exit on --help; that's ok


class TestMainInProcess:
    """Coverage: main entry point."""

    def test_no_args(self):
        mod = _load_module()
        assert mod.main([]) == 2

    def test_missing_out_dir(self, tmp_path):
        mod = _load_module()
        rc = mod.main(["--root", str(tmp_path)])
        assert rc == 2  # --out-dir required

    def test_ok_run(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest"}})
        )
        out = tmp_path / "out"
        rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
        # rc can be 0 (clean) or 1 (findings) — both are OK
        assert rc in (0, 1)

    def test_invalid_config(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        out = tmp_path / "out"
        cfg = tmp_path / "cfg.json"
        cfg.write_text("bad")
        rc = mod.main(
            ["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)]
        )
        assert rc == 2


# ---------------------------------------------------------------------------
# Vendored health_common.py coverage: import the vendored copy in-process
# ---------------------------------------------------------------------------


def test_vendored_health_common_is_importable(tmp_path):
    """Loading the vendored health_common.py exercises all its lines."""
    hc_path = SKILL_ROOT / "scripts" / "health_common.py"
    spec = importlib.util.spec_from_file_location("hc_exec_vendored2", hc_path)
    hc_mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = hc_mod  # needed for dataclass annotation resolution
    spec.loader.exec_module(hc_mod)

    # Exercise Finding dataclass
    f = hc_mod.Finding(
        leaf="test",
        signal="SIMPLIFY",
        severity="low",
        path="f.py",
        line_start=1,
        line_end=2,
        symbol="s",
        metric_name="m",
        metric_value=0.5,
        metric_threshold=1.0,
        evidence_tool="t",
        evidence_raw="r",
        confidence="medium",
        suggested_action="a",
    )
    d = f.to_dict()
    assert d["leaf"] == "test"
    assert d["signal"] == "SIMPLIFY"
    assert d["metric"]["name"] == "m"
    assert len(d["id"]) == 16  # stable_id is hex SHA1[:16]

    # sort_findings
    sorted_f = hc_mod.sort_findings([f])
    assert len(sorted_f) == 1

    # write_findings
    data = hc_mod.write_findings([f], tmp_path, "test-leaf")
    assert len(data) == 1
    assert (tmp_path / "test-leaf_findings.json").exists()

    # Constants
    assert hc_mod.EXIT_CLEAN == 0
    assert hc_mod.EXIT_FINDINGS == 1
    assert hc_mod.EXIT_ERROR == 2


# ---------------------------------------------------------------------------
# Helpers for in-process tests
# ---------------------------------------------------------------------------


def _make_one_finding(mod):
    return mod.hc.Finding(
        leaf="exec-audit",
        signal="PERF",
        severity="medium",
        path="t.py",
        line_start=0,
        line_end=0,
        symbol="sym",
        metric_name="test_metric",
        metric_value=1.0,
        metric_threshold=0.5,
        evidence_tool="e",
        evidence_raw="raw",
        confidence="high",
        suggested_action="fix",
    )
