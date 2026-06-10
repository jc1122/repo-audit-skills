"""Findings tests for test-effectiveness-audit (no real mutmut).

Uses captured fixtures under tests/fixtures/captured/ to exercise
findings_from_mutmut() or equivalent stable helpers in-process.

Ground truth for fixtures/weakpkg under mutmut 3.6.0:
  - 5 mutants total (1 for add, 4 for weak)
  - add mutant killed, all 4 weak mutants status "no tests"
  - cicd-stats: {"killed": 1, "survived": 0, "total": 5, "no_tests": 4, ...}
  - src/calc.py kill_rate = (5 - 4) / 5 = 0.2
  - One TEST finding for src/calc.py, severity high, metric mutation_kill_rate=0.2

Also verifies that timeout/suspicious/skipped are NOT counted as problems
(they count as killed for kill-rate purposes per the A6 accounting rule).
"""
import json
from pathlib import Path

import pytest

try:
    from helpers import load_module, FIXTURES
except ImportError:
    pytest.skip("helpers module not yet available", allow_module_level=True)

_mod = None


def _get_mod():
    global _mod
    if _mod is None:
        _mod = load_module()
    return _mod


# ---------------------------------------------------------------------------
# Ground truth: findings_from_mutmut with captured fixtures
# ---------------------------------------------------------------------------


def _setup_captured_work(work: Path) -> None:
    """Set up work/mutants/src/ with calc.py.meta and results.txt from
    captured fixtures, mirroring the real mutmut output layout."""
    mutants_dir = work / "mutants" / "src"
    mutants_dir.mkdir(parents=True)

    # Copy calc.py.meta into work/mutants/src/calc.py.meta
    meta_src = FIXTURES / "captured" / "calc.py.meta"
    (mutants_dir / "calc.py.meta").write_text(meta_src.read_text())

    # Copy captured results.txt into the work directory
    results_src = FIXTURES / "captured" / "results.txt"
    (work / "results.txt").write_text(results_src.read_text())

    # Also write cicd-stats for completeness
    cicd_src = FIXTURES / "captured" / "mutmut-cicd-stats.json"
    (work / "mutmut-cicd-stats.json").write_text(cicd_src.read_text())


def test_findings_from_captured_ground_truth(tmp_path: Path):
    """Exercise findings_from_mutmut() with captured fixtures.

    Verifies the plan ground truth:
      total 5, killed 1, no_tests 4, kill_rate 0.2,
      one TEST finding for src/calc.py, severity high,
      metric mutation_kill_rate=0.2.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)

    # Exactly one finding
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}"

    f = findings[0]
    # Check signal
    assert f.signal == "TEST", f"Unexpected signal: {f.signal}"
    # Check path
    assert f.path == "src/calc.py", f"Unexpected path: {f.path}"
    # Check severity: kill_rate 0.2 < 0.5 → high
    assert f.severity == "high", f"Unexpected severity: {f.severity}"
    # Check metric
    assert f.metric_name == "mutation_kill_rate", (
        f"Unexpected metric name: {f.metric_name}"
    )
    assert f.metric_value == 0.2, f"Unexpected kill rate: {f.metric_value}"
    assert f.metric_threshold == 0.8, (
        f"Unexpected threshold: {f.metric_threshold}"
    )
    # Check confidence
    assert f.confidence == "high", f"Unexpected confidence: {f.confidence}"
    # Check evidence tool
    assert f.evidence_tool == "mutmut", (
        f"Unexpected evidence tool: {f.evidence_tool}"
    )
    # Check location metadata
    assert f.line_start == 1
    assert f.line_end == 1
    assert f.symbol == "<module>" or "calc" in f.symbol.lower(), (
        f"Unexpected symbol: {f.symbol}"
    )
    # Check suggested action exists and is non-empty
    assert f.suggested_action, "suggested_action should not be empty"
    # Evidence should mention the weak mutants
    assert "no tests" in f.evidence_raw.lower() or "x_weak" in f.evidence_raw, (
        f"evidence_raw should reference the problem mutants: {f.evidence_raw}"
    )


def test_findings_from_captured_as_dicts(tmp_path: Path):
    """Verify the finding serializes correctly under the shared schema."""
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)

    # Convert to dict representation
    data = [f.to_dict() for f in findings]
    assert len(data) == 1
    d = data[0]

    # Required keys per shared schema
    required_keys = {
        "id", "leaf", "signal", "severity", "path", "location",
        "metric", "evidence", "confidence", "suggested_action",
    }
    assert required_keys <= d.keys(), f"Missing keys: {required_keys - d.keys()}"

    assert d["leaf"] == "test-effectiveness"
    assert d["signal"] == "TEST"
    assert d["severity"] == "high"
    assert d["path"] == "src/calc.py"
    assert d["location"] == {
        "line_start": 1,
        "line_end": 1,
        "symbol": d["location"]["symbol"],  # symbol is impl-dependent
    }
    assert d["metric"]["name"] == "mutation_kill_rate"
    assert d["metric"]["value"] == 0.2
    assert d["metric"]["threshold"] == 0.8
    assert d["evidence"]["tool"] == "mutmut"
    assert d["confidence"] == "high"
    assert d["id"]  # stable_id should be non-empty


def test_kill_rate_above_threshold_no_finding(tmp_path: Path):
    """When kill_rate >= min_kill_rate, no finding is emitted."""
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    # With min_kill_rate=0.1, kill_rate 0.2 >= 0.1 → no finding
    thresholds = {"min_kill_rate": 0.1}
    findings = mod.findings_from_mutmut(work, thresholds)
    assert len(findings) == 0, (
        f"Expected 0 findings when kill_rate >= threshold, got {len(findings)}"
    )


def test_findings_empty_when_no_modules(tmp_path: Path):
    """Empty work directory → zero findings."""
    mod = _get_mod()
    work = tmp_path / "work"
    work.mkdir()
    (work / "mutants").mkdir()

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)
    assert findings == []


def test_findings_sorted_and_deterministic(tmp_path: Path):
    """Two calls with identical input produce identical findings."""
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    thresholds = {"min_kill_rate": 0.8}
    f1 = mod.findings_from_mutmut(work, thresholds)
    f2 = mod.findings_from_mutmut(work, thresholds)

    assert len(f1) == len(f2)
    for a, b in zip(f1, f2):
        assert a.to_dict() == b.to_dict()


# ---------------------------------------------------------------------------
# Timeout / suspicious / skipped are NOT problems
# ---------------------------------------------------------------------------


def test_timeout_suspicious_skipped_not_counted_as_problems(tmp_path: Path):
    """Timeout, suspicious, and skipped mutants count as killed.

    They must NOT drag down the kill rate — only survived and no_tests
    are treated as test-suite weaknesses per the A6 accounting rule.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "pkg"
    mutants_dir.mkdir(parents=True)

    # 7 mutants total: 1 killed, 2 survived, 2 no_tests, 1 timeout, 1 suspicious
    # problems = survived(2) + no_tests(2) = 4
    # kill_rate = (7 - 4) / 7 = 3/7 ≈ 0.429 → < 0.8 → finding emitted
    (mutants_dir / "mod.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "pkg.mod.x_killed__mutmut_1": 1,
                    "pkg.mod.x_surv__mutmut_1": 0,
                    "pkg.mod.x_surv__mutmut_2": 0,
                    "pkg.mod.x_notest__mutmut_1": 33,
                    "pkg.mod.x_notest__mutmut_2": 33,
                    "pkg.mod.x_timeout__mutmut_1": None,
                    "pkg.mod.x_susp__mutmut_1": None,
                }
            }
        )
    )

    # Results text: all problems are listed (killed mutants are absent)
    results_text = """\
    pkg.mod.x_surv__mutmut_1: survived
    pkg.mod.x_surv__mutmut_2: survived
    pkg.mod.x_notest__mutmut_1: no tests
    pkg.mod.x_notest__mutmut_2: no tests
    pkg.mod.x_timeout__mutmut_1: timeout
    pkg.mod.x_susp__mutmut_1: suspicious
"""
    (work / "results.txt").write_text(results_text)

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)

    # kill_rate = (7 - 4) / 7 = 3/7 ≈ 0.429 → < 0.8 → one finding
    assert len(findings) == 1
    f = findings[0]
    assert f.path == "pkg/mod.py"
    # kill_rate = 0.428571... → 0.429 when rounded to 3 decimals
    assert abs(f.metric_value - 0.429) < 0.001, (
        f"Expected kill_rate ~0.429, got {f.metric_value}"
    )
    # severity: 0.429 < 0.5 → high
    assert f.severity == "high"


def test_perfect_kill_rate_no_finding(tmp_path: Path):
    """All mutants killed → kill_rate 1.0 → no finding."""
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "pkg"
    mutants_dir.mkdir(parents=True)

    # 3 mutants, all killed (none appear in results text)
    (mutants_dir / "mod.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "pkg.mod.x_a__mutmut_1": 1,
                    "pkg.mod.x_b__mutmut_1": 1,
                    "pkg.mod.x_c__mutmut_1": 1,
                }
            }
        )
    )

    # Empty results text (all killed → none listed)
    (work / "results.txt").write_text("")

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# Threshold propagation regression test (SP7 A6 repair)
# ---------------------------------------------------------------------------


def test_metric_threshold_preserves_configured_value(tmp_path: Path):
    """The emitted finding's metric_threshold MUST equal the configured
    min_kill_rate, not a hardcoded constant.

    Regression: prior to the SP7 A6 repair, _make_finding hardcoded
    metric_threshold=0.8 regardless of the --threshold / --config value.
    This test locks in the fix so a future refactor cannot regress.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    # Use a non-default threshold (0.55 instead of 0.8).
    # With kill_rate=0.2, this should still produce a finding.
    configured_threshold = 0.55
    thresholds = {"min_kill_rate": configured_threshold}
    findings = mod.findings_from_mutmut(work, thresholds)

    assert len(findings) == 1, (
        f"Expected 1 finding with threshold={configured_threshold}, "
        f"got {len(findings)}"
    )
    f = findings[0]

    # The key assertion: metric_threshold reflects the configured value,
    # NOT the old hardcoded 0.8.
    assert f.metric_threshold == configured_threshold, (
        f"metric_threshold should be {configured_threshold} "
        f"(the configured min_kill_rate), but got {f.metric_threshold}. "
        f"This is a regression — _make_finding must use the caller's "
        f"threshold, not a hardcoded constant."
    )

    # Also verify the dict representation matches
    d = f.to_dict()
    assert d["metric"]["threshold"] == configured_threshold, (
        f"dict metric.threshold should be {configured_threshold}, "
        f"got {d['metric']['threshold']}"
    )


def test_metric_threshold_preserves_different_custom_value(tmp_path: Path):
    """Same as above but with a different threshold to double-check
    the value is truly dynamic (not accidentally matching 0.55)."""
    mod = _get_mod()
    work = tmp_path / "work"
    _setup_captured_work(work)

    # kill_rate=0.2, use threshold=0.35 — should still produce a finding
    configured_threshold = 0.35
    thresholds = {"min_kill_rate": configured_threshold}
    findings = mod.findings_from_mutmut(work, thresholds)

    assert len(findings) == 1
    f = findings[0]

    assert f.metric_threshold == configured_threshold, (
        f"metric_threshold should be {configured_threshold}, "
        f"got {f.metric_threshold}"
    )
    assert f.to_dict()["metric"]["threshold"] == configured_threshold


# ---------------------------------------------------------------------------
# load_thresholds and render_report coverage tests
# ---------------------------------------------------------------------------


def test_load_thresholds_none_returns_defaults():
    """load_thresholds(None) returns a copy of DEFAULT_THRESHOLDS."""
    mod = _get_mod()
    result = mod.load_thresholds(None)
    assert result == mod.DEFAULT_THRESHOLDS
    assert result is not mod.DEFAULT_THRESHOLDS  # must be a copy


def test_load_thresholds_merges_json_config(tmp_path: Path):
    """load_thresholds with a valid JSON config merges values."""
    mod = _get_mod()
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"min_kill_rate": 0.5, "custom": 42}))
    result = mod.load_thresholds(str(config_file))
    assert result["min_kill_rate"] == 0.5  # overridden
    assert result["mutmut_timeout_seconds"] == 600  # preserved from defaults
    assert result["custom"] == 42  # new key added


def test_load_thresholds_missing_file_raises_toolerror():
    """load_thresholds raises ToolError for a non-existent config file."""
    mod = _get_mod()
    with pytest.raises(Exception) as exc_info:
        mod.load_thresholds("/nonexistent/path/config.json")
    # ToolError is a RuntimeError subclass
    assert "invalid --config" in str(exc_info.value).lower() or isinstance(
        exc_info.value, RuntimeError
    )


def test_load_thresholds_invalid_json_raises_toolerror(tmp_path: Path):
    """load_thresholds raises ToolError for invalid JSON."""
    mod = _get_mod()
    config_file = tmp_path / "bad.json"
    config_file.write_text("not valid json {{{")
    with pytest.raises(Exception) as exc_info:
        mod.load_thresholds(str(config_file))
    assert "invalid --config" in str(exc_info.value).lower() or isinstance(
        exc_info.value, RuntimeError
    )


def test_render_report_empty_findings():
    """render_report with empty list returns simple 'No findings' report."""
    mod = _get_mod()
    report = mod.render_report([])
    assert "No findings" in report
    assert report.startswith("# test-effectiveness-audit report")


def test_render_report_with_high_severity_findings():
    """render_report with high-severity findings includes the HIGH section."""
    mod = _get_mod()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "work"
        _mutants_dir = work / "mutants" / "pkg"
        _mutants_dir.mkdir(parents=True)
        (_mutants_dir / "mod.py.meta").write_text(
            json.dumps(
                {
                    "exit_code_by_key": {
                        "pkg.mod.x_k1__mutmut_1": 1,
                        "pkg.mod.x_s1__mutmut_1": 0,
                        "pkg.mod.x_s2__mutmut_1": 0,
                        "pkg.mod.x_s3__mutmut_1": 0,
                        "pkg.mod.x_s4__mutmut_1": 0,
                    }
                }
            )
        )
        (work / "results.txt").write_text(
            "pkg.mod.x_s1__mutmut_1: survived\n"
            "pkg.mod.x_s2__mutmut_1: survived\n"
            "pkg.mod.x_s3__mutmut_1: survived\n"
            "pkg.mod.x_s4__mutmut_1: survived\n"
        )
        thresholds = {"min_kill_rate": 0.8}
        findings = mod.findings_from_mutmut(work, thresholds)
        assert len(findings) == 1
        report = mod.render_report(findings)
        assert "HIGH severity" in report
        assert "Mutation testing" in report


def test_render_report_with_medium_severity():
    """render_report with medium-severity findings includes MEDIUM section."""
    mod = _get_mod()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "work"
        _md = work / "mutants" / "pkg"
        _md.mkdir(parents=True)
        # 2 mutants: 1 killed, 1 survived → kill_rate = 0.5
        (_md / "mod.py.meta").write_text(
            json.dumps(
                {
                    "exit_code_by_key": {
                        "pkg.mod.x_k__mutmut_1": 1,
                        "pkg.mod.x_s__mutmut_1": 0,
                    }
                }
            )
        )
        (work / "results.txt").write_text("pkg.mod.x_s__mutmut_1: survived\n")
        thresholds = {"min_kill_rate": 0.8}
        findings = mod.findings_from_mutmut(work, thresholds)
        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "medium"  # 0.5 is not < 0.5
        report = mod.render_report(findings)
        assert "MEDIUM severity" in report
        assert "HIGH severity" not in report


def test_metric_threshold_at_kill_rate_boundary_no_finding(tmp_path: Path):
    """When kill_rate equals the configured threshold, no finding is emitted.

    This confirms the threshold comparison logic works correctly with
    non-default values — the finding suppression is faithful to the
    configured threshold, not a hardcoded constant.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "pkg"
    mutants_dir.mkdir(parents=True)

    # 5 mutants: 4 killed, 1 survived → kill_rate = 4/5 = 0.8
    (mutants_dir / "mod.py.meta").write_text(
        json.dumps({
            "exit_code_by_key": {
                "pkg.mod.x_k1__mutmut_1": 1,
                "pkg.mod.x_k2__mutmut_1": 1,
                "pkg.mod.x_k3__mutmut_1": 1,
                "pkg.mod.x_k4__mutmut_1": 1,
                "pkg.mod.x_s1__mutmut_1": 0,
            }
        })
    )
    (work / "results.txt").write_text("pkg.mod.x_s1__mutmut_1: survived\n")

    # threshold=0.8, kill_rate=0.8 → kill_rate >= threshold → NO finding
    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)
    assert len(findings) == 0, (
        f"kill_rate=0.8 with threshold=0.8 should produce 0 findings, "
        f"got {len(findings)}"
    )

    # threshold=0.79, kill_rate=0.8 → kill_rate >= threshold → NO finding
    thresholds2 = {"min_kill_rate": 0.79}
    findings2 = mod.findings_from_mutmut(work, thresholds2)
    assert len(findings2) == 0, (
        f"kill_rate=0.8 with threshold=0.79 should produce 0 findings, "
        f"got {len(findings2)}"
    )

    # threshold=0.81, kill_rate=0.8 → kill_rate < threshold → finding emitted
    thresholds3 = {"min_kill_rate": 0.81}
    findings3 = mod.findings_from_mutmut(work, thresholds3)
    assert len(findings3) == 1
    assert findings3[0].metric_threshold == 0.81, (
        f"threshold should be 0.81, got {findings3[0].metric_threshold}"
    )
