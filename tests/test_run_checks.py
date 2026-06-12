"""Tests for scripts/run_checks.py — timed gate runner core."""
import json
import subprocess
import time
from unittest.mock import MagicMock

import pytest

import scripts.run_checks as rc

# ------------------------------------------------------------------ budget_violations (existing)


def test_budget_violation_fails_gate():
    budget = {"selfaudit": 0.000001}
    timings = {"selfaudit": 1.5}
    violations = rc.budget_violations(timings, budget)
    assert violations == [("selfaudit", 1.5, 0.000001)]


def test_within_budget_passes():
    assert rc.budget_violations({"selfaudit": 1.0}, {"selfaudit": 30}) == []


def test_missing_budget_entry_is_a_violation():
    assert rc.budget_violations({"newgate": 1.0}, {}) == [("newgate", 1.0, None)]


# ------------------------------------------------------------------ _load_budget


def test_load_budget_returns_dict_when_file_exists(tmp_path, monkeypatch):
    budget_data = {"vendored": 10, "pytest": 60}
    budget_file = tmp_path / "check_budget.json"
    budget_file.write_text(json.dumps(budget_data))
    monkeypatch.setattr(rc, "SCRIPTS_DIR", tmp_path)
    result = rc._load_budget()
    assert result == budget_data


def test_load_budget_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "SCRIPTS_DIR", tmp_path)
    result = rc._load_budget()
    assert result == {}


# ------------------------------------------------------------------ _run_one


def test_run_one_success(monkeypatch):
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "pass output\n"
    fake_proc.stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    _counter = iter([100.0, 100.5])
    monkeypatch.setattr(time, "perf_counter", lambda: next(_counter))

    name, code, elapsed, tail = rc._run_one("testgate", "scripts/fake.py")
    assert name == "testgate"
    assert code == 0
    assert elapsed == pytest.approx(0.5)
    assert tail == "pass output"


def test_run_one_failure(monkeypatch):
    fake_proc = MagicMock()
    fake_proc.returncode = 1
    fake_proc.stdout = ""
    fake_proc.stderr = "something broke\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    _counter = iter([200.0, 201.2])
    monkeypatch.setattr(time, "perf_counter", lambda: next(_counter))

    name, code, elapsed, tail = rc._run_one("failgate", "scripts/fake.py")
    assert name == "failgate"
    assert code == 1
    assert elapsed == pytest.approx(1.2)
    assert tail == "something broke"


def test_run_one_timeout(monkeypatch):
    def _raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="x", timeout=600)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)
    _counter = iter([50.0, 51.0])
    monkeypatch.setattr(time, "perf_counter", lambda: next(_counter))

    name, code, elapsed, tail = rc._run_one("slowgate", "scripts/fake.py")
    assert name == "slowgate"
    assert code == 1
    assert elapsed == pytest.approx(1.0)
    assert "TIMEOUT" in tail


def test_run_one_truncates_long_output(monkeypatch):
    big_output = "x" * 3000
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = big_output
    fake_proc.stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    _counter = iter([0.0, 0.1])
    monkeypatch.setattr(time, "perf_counter", lambda: next(_counter))

    _name, _code, _elapsed, tail = rc._run_one("big", "scripts/fake.py")
    assert len(tail) == 2000
    assert tail == big_output[-2000:]


# ------------------------------------------------------------------ _run_all_gates


def test_run_all_gates_populates_timings_and_results(monkeypatch):
    call_count = 0

    def _fake_run_one(name, path):
        nonlocal call_count
        call_count += 1
        return (name, 0, 0.1 * call_count, "")

    monkeypatch.setattr(rc, "_run_one", _fake_run_one)

    timings: dict[str, float] = {}
    results: dict[str, tuple[int, str]] = {}
    rc._run_all_gates(timings, results)

    assert len(timings) == len(rc.CHEAP) + len(rc.HEAVY)
    assert len(results) == len(rc.CHEAP) + len(rc.HEAVY)
    for name in timings:
        assert timings[name] > 0
        assert results[name][0] == 0


# ------------------------------------------------------------------ _write_timings


def test_write_timings_persists_json(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "SCRIPTS_DIR", tmp_path)
    rc._write_timings({"foo": 1.5, "bar": 2.0})
    written = json.loads((tmp_path / "check_timings.json").read_text())
    assert written == {"foo": 1.5, "bar": 2.0}


def test_write_timings_creates_dir_if_missing(tmp_path, monkeypatch):
    scripts_subdir = tmp_path / "nested" / "scripts"
    monkeypatch.setattr(rc, "SCRIPTS_DIR", scripts_subdir)
    rc._write_timings({"x": 0.1})
    assert (scripts_subdir / "check_timings.json").exists()


# ------------------------------------------------------------------ _print_failed_gates


def test_print_failed_gates_output(capsys):
    results = {
        "a": (0, "ok"),
        "b": (1, "bad thing"),
        "c": (0, "fine"),
    }
    timings = {"a": 0.5, "b": 1.2, "c": 0.3}
    rc._print_failed_gates(results, timings)
    out = capsys.readouterr().out
    assert "FAILED GATES" in out
    assert "FAIL  b  (exit 1, 1.20s)" in out
    assert "bad thing" in out
    assert "FAIL  a" not in out
    assert "FAIL  c" not in out


def test_print_failed_gates_no_failures(capsys):
    results = {"a": (0, "ok"), "b": (0, "fine")}
    timings = {"a": 0.5, "b": 0.3}
    rc._print_failed_gates(results, timings)
    out = capsys.readouterr().out
    # Still prints the header
    assert "FAILED GATES" in out


# ------------------------------------------------------------------ _print_over_budget


def test_print_over_budget_with_values(capsys):
    violations = [("cov", 130.5, 120.0), ("pytest", 140.0, 120.0)]
    rc._print_over_budget(violations)
    out = capsys.readouterr().out
    assert "OVER BUDGET" in out
    assert "cov  130.500s > 120.000s" in out
    assert "pytest  140.000s > 120.000s" in out


def test_print_over_budget_missing_entry(capsys):
    violations = [("newbie", 5.5, None)]
    rc._print_over_budget(violations)
    out = capsys.readouterr().out
    assert "OVER BUDGET" in out
    assert "no budget entry" in out


# ------------------------------------------------------------------ _print_summary


def test_print_summary_all_pass(capsys):
    results = {}
    for name, _path in rc.CHEAP + rc.HEAVY:
        results[name] = (0, "")
    rc._print_summary(results, [])
    out = capsys.readouterr().out
    assert f"gates: {len(rc.CHEAP)}/{len(rc.CHEAP)} cheap" in out
    assert f"{len(rc.HEAVY)}/{len(rc.HEAVY)} heavy" in out
    assert "0 over-budget" in out
    assert "0 failed" in out


def test_print_summary_with_failures(capsys):
    results = {}
    for i, (name, _path) in enumerate(rc.CHEAP + rc.HEAVY):
        results[name] = (1 if i < 3 else 0, "")
    rc._print_summary(results, [("x", 1.0, 0.5)])
    out = capsys.readouterr().out
    assert "1 over-budget" in out
    assert "3 failed" in out


# ------------------------------------------------------------------ main() integration


def test_main_all_pass_and_within_budget(monkeypatch, capsys):
    """main() returns 0 when every gate passes and no budget violations."""

    def _fake_run_all(timings, results):
        for name, _path in rc.CHEAP + rc.HEAVY:
            timings[name] = 1.0
            results[name] = (0, "")

    monkeypatch.setattr(rc, "_run_all_gates", _fake_run_all)
    # Budget covers every gate with a high ceiling so nothing exceeds.
    _all_names = [n for n, _ in rc.CHEAP + rc.HEAVY]
    monkeypatch.setattr(rc, "_load_budget", lambda: {n: 999 for n in _all_names})
    monkeypatch.setattr(rc, "_write_timings", lambda t: None)

    exit_code = rc.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "FAILED" not in out
    assert "OVER BUDGET" not in out
    assert "0 over-budget" in out
    assert "0 failed" in out


def test_main_fails_on_gate_failure(monkeypatch, capsys):
    """main() returns 1 when any gate fails, even if within budget."""

    def _fake_run_all(timings, results):
        for name, _path in rc.CHEAP + rc.HEAVY:
            timings[name] = 0.5
            results[name] = (1 if name == "release" else 0, "boom" if name == "release" else "")

    monkeypatch.setattr(rc, "_run_all_gates", _fake_run_all)
    _all_names = [n for n, _ in rc.CHEAP + rc.HEAVY]
    monkeypatch.setattr(rc, "_load_budget", lambda: {n: 999 for n in _all_names})
    monkeypatch.setattr(rc, "_write_timings", lambda t: None)

    exit_code = rc.main()
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "FAILED GATES" in out
    assert "FAIL  release" in out
    assert "boom" in out
    assert "0 over-budget" in out


def test_main_fails_on_budget_violation(monkeypatch, capsys):
    """main() returns 1 when a gate is over budget even if it passes."""

    def _fake_run_all(timings, results):
        for name, _path in rc.CHEAP + rc.HEAVY:
            timings[name] = 50.0
            results[name] = (0, "")

    monkeypatch.setattr(rc, "_run_all_gates", _fake_run_all)
    monkeypatch.setattr(rc, "_load_budget", lambda: {"vendored": 10})
    monkeypatch.setattr(rc, "_write_timings", lambda t: None)

    exit_code = rc.main()
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "FAILED" not in out  # no functional failures
    assert "OVER BUDGET" in out
    assert "50.000s > 10.000s" in out
    assert "10 over-budget" in out
    assert "0 failed" in out


def test_main_writes_timings(tmp_path, monkeypatch, capsys):
    """main() persists timings to the real SCRIPTS_DIR (mocked to tmp_path)."""

    def _fake_run_all(timings, results):
        timings["a"] = 1.5
        results["a"] = (0, "")

    monkeypatch.setattr(rc, "_run_all_gates", _fake_run_all)
    monkeypatch.setattr(rc, "_load_budget", lambda: {"a": 999})
    monkeypatch.setattr(rc, "CHEAP", [("a", "x.py")])
    monkeypatch.setattr(rc, "HEAVY", [])
    monkeypatch.setattr(rc, "SCRIPTS_DIR", tmp_path)

    exit_code = rc.main()
    assert exit_code == 0
    written = json.loads((tmp_path / "check_timings.json").read_text())
    assert written == {"a": 1.5}


# ------------------------------------------------------------------ constants


def test_cheap_has_8_entries():
    assert len(rc.CHEAP) == 8


def test_heavy_has_2_entries():
    assert len(rc.HEAVY) == 2


def test_cheap_names_match_budget_keys():
    budget_keys = {
        "vendored", "fixtures", "release", "selfaudit",
        "security", "hygiene", "docs", "dependency",
    }
    assert {name for name, _ in rc.CHEAP} == budget_keys


def test_heavy_names_match_budget_keys():
    assert {name for name, _ in rc.HEAVY} == {"coverage", "pytest"}
