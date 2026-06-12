import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_full_pytest.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_full_pytest", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_suite_dirs_discovers_root_and_skill_tests(tmp_path, monkeypatch):
    mod = _load()
    (tmp_path / "tests").mkdir()
    (tmp_path / "skills" / "alpha" / "tests").mkdir(parents=True)
    (tmp_path / "skills" / "beta" / "tests").mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in mod.suite_dirs()] == [
        "tests",
        "skills/alpha/tests",
        "skills/beta/tests",
    ]


def test_run_suite_executes_and_returns_structured_result(tmp_path, monkeypatch):
    """run_suite runs pytest in the suite parent cwd and returns expected dict."""
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    suite = tmp_path / "tests"
    suite.mkdir()
    (suite / "test_ok.py").write_text(
        "def test_passes():\n    assert True\n",
        encoding="utf-8",
    )

    result = mod.run_suite(suite)
    assert result["suite"] == "tests"
    assert result["returncode"] == 0
    assert "1 passed" in " ".join(result["tail"])


def test_main_writes_snapshot_and_reports_failures(tmp_path, monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    snapshot_path = tmp_path / "full_pytest_snapshot.json"
    monkeypatch.setattr(mod, "SNAPSHOT", snapshot_path)

    recorded = [
        {"suite": "skills/broken/tests", "returncode": 1, "tail": ["2 failed"]},
        {"suite": "tests", "returncode": 0, "tail": ["1 passed"]},
    ]

    def fake_suite_dirs():
        return [tmp_path / "tests", tmp_path / "skills" / "broken" / "tests"]

    def fake_run_suite(suite):
        rel = str(suite.relative_to(tmp_path))
        for r in recorded:
            if r["suite"] == rel:
                return r
        return {"suite": rel, "returncode": 1, "tail": ["unknown"]}

    monkeypatch.setattr(mod, "suite_dirs", fake_suite_dirs)
    monkeypatch.setattr(mod, "run_suite", fake_run_suite)

    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "full-pytest: 1/2 suites green" in out
    assert "FAIL skills/broken/tests" in out
    assert "2 failed" in snapshot_path.read_text(encoding="utf-8")

    # Verify snapshot order is sorted (broken < tests alphabetically)
    written = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert [r["suite"] for r in written] == ["skills/broken/tests", "tests"]


def test_snapshot_order_is_sorted_not_completion_order(tmp_path, monkeypatch):
    """Results must be ordered by suite path so reruns are byte-identical."""
    import scripts.check_full_pytest as gate

    recorded = [
        {"suite": "skills/b/tests", "returncode": 0, "tail": ["1 passed"]},
        {"suite": "skills/a/tests", "returncode": 0, "tail": ["1 passed"]},
    ]
    ordered = gate.sort_results(recorded)
    assert [r["suite"] for r in ordered] == ["skills/a/tests", "skills/b/tests"]


def test_normalize_tail_strips_volatile_duration():
    """normalize_tail removes pytest timing so snapshots are byte-stable."""
    import scripts.check_full_pytest as gate

    # Simple duration
    assert gate.normalize_tail(["34 passed in 9.60s"]) == ["34 passed"]
    # Failed + passed with duration
    assert gate.normalize_tail(["6 failed, 2 passed in 1.57s"]) == [
        "6 failed, 2 passed"
    ]
    # Duration with parenthesised H:MM:SS
    assert gate.normalize_tail(["208 passed in 185.99s (0:03:05)"]) == [
        "208 passed"
    ]
    # No tests ran (edge case)
    assert gate.normalize_tail(["no tests ran in 0.01s"]) == ["no tests ran"]
    # Already normalized (no-op)
    assert gate.normalize_tail(["1 passed"]) == ["1 passed"]
    # Integer seconds (no decimal)
    assert gate.normalize_tail(["5 passed in 2s"]) == ["5 passed"]
    # Empty tail
    assert gate.normalize_tail([]) == []


def test_run_suite_normalizes_tail(tmp_path, monkeypatch):
    """run_suite returns tail without volatile duration strings."""
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    suite = tmp_path / "tests"
    suite.mkdir()
    (suite / "test_ok.py").write_text(
        "def test_passes():\n    assert True\n",
        encoding="utf-8",
    )

    result = mod.run_suite(suite)
    tail_joined = " ".join(result["tail"])
    assert "1 passed" in tail_joined
    assert " in " not in tail_joined, f"tail still contains timing: {result['tail']}"
