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
