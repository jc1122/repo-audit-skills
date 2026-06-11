"""Regression coverage for clean ToolError handling on mutmut run failure."""

import importlib.util
import json
import subprocess

import pytest

try:
    from helpers import load_module
except ImportError:
    pytest.skip("helpers module not yet available", allow_module_level=True)


def test_mutmut_run_failure_exits_two_with_clean_json(tmp_path, capsys, monkeypatch):
    mod = load_module()

    src = tmp_path / "src"
    src.mkdir()
    (src / "calc.py").write_text("def add(a, b):\n    return a + b\n")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_calc.py").write_text(
        "from src.calc import add\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n"
    )

    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src/calc.py\n")

    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name):
        if name == "mutmut":
            return object()
        return original_find_spec(name)

    def fail_mutmut_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=7,
            cmd=args[0],
            output="prelude\nmutmut stdout failure\n",
            stderr="mutmut stderr failure\n",
        )

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(subprocess, "run", fail_mutmut_run)

    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(tmp_path / "out"),
            "--paths",
            str(paths_file),
            "--tests-dir",
            "tests",
            "--max-mutants",
            "100",
        ]
    )

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert rc == 2
    assert data["status"] == "error"
    assert "mutmut run failed (exit 7):" in data["message"]
    assert "mutmut run failed" in data["message"]
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    assert captured.err == ""
