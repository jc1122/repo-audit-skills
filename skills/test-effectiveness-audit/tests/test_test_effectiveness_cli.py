"""CLI contract and integration tests for test-effectiveness-audit.

Covers:
- Subprocess help smoke (exactly one, per C-4 rule)
- Scope refusal: missing --paths, --tests-dir, --max-mutants → exit 2
- Budget refusal: scope too large → exit 2
- EXACTLY ONE real-mutmut integration test (subprocess, timeout=180)

Other CLI/contract tests use mod.main([...]) in-process with capsys for coverage.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

try:
    from helpers import load_module, run_cli, FIXTURES, SKILL_ROOT, SCRIPT
except ImportError:
    pytest.skip("helpers module not yet available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Help smoke (the single subprocess test, per C-4)
# ---------------------------------------------------------------------------


def test_help_exits_zero():
    """run_cli('--help') exits 0 — the single subprocess smoke test."""
    result = run_cli("--help")
    assert result.returncode == 0, f"stderr: {result.stderr}"


# ---------------------------------------------------------------------------
# Scope refusal tests (in-process via mod.main for coverage)
# ---------------------------------------------------------------------------


def test_missing_paths_exits_two(tmp_path, capsys):
    """Missing --paths exits 2 with status-error JSON and rationale about
    unscoped mutation testing / top-N scoped paths."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--tests-dir",
            "tests",
            "--max-mutants",
            "100",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"
    assert (
        "paths" in data["message"].lower()
        or "scope" in data["message"].lower()
        or "mutation" in data["message"].lower()
    ), f"unexpected message: {data['message']}"


def test_missing_tests_dir_exits_two(tmp_path, capsys):
    """Missing --tests-dir exits 2 with status-error JSON."""
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src/calc.py\n")
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--paths",
            str(paths_file),
            "--max-mutants",
            "100",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"
    assert (
        "tests-dir" in data["message"].lower()
        or "tests" in data["message"].lower()
        or "scope" in data["message"].lower()
    ), f"unexpected message: {data['message']}"


def test_missing_max_mutants_exits_two(tmp_path, capsys):
    """Missing --max-mutants exits 2 with status-error JSON."""
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src/calc.py\n")
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--paths",
            str(paths_file),
            "--tests-dir",
            "tests",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"
    assert (
        "max-mutants" in data["message"].lower()
        or "mutants" in data["message"].lower()
        or "scope" in data["message"].lower()
    ), f"unexpected message: {data['message']}"


def test_missing_all_scope_args_exits_two(tmp_path, capsys):
    """Missing all three scope args (paths, tests-dir, max-mutants) exits 2."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(tmp_path), "--out-dir", str(out)])
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"


def test_budget_refusal_exits_two(tmp_path, capsys):
    """--max-mutants budget refusal exits 2 with 'scope too large' wording.

    Creates a source file with many functions so the AST-based estimate
    exceeds a low --max-mutants value, triggering the budget refusal."""
    src = tmp_path / "src"
    src.mkdir()
    # 50 functions × 8 estimated_mutants_per_def = ~400 mutants > max_mutants=10
    funcs = "\n".join(f"def f{i}(): pass" for i in range(50))
    (src / "big.py").write_text(funcs + "\n")

    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src/big.py\n")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--paths",
            str(paths_file),
            "--tests-dir",
            "tests",
            "--max-mutants",
            "10",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"
    assert "scope too large" in data["message"].lower(), (
        f"expected 'scope too large' in message, got: {data['message']}"
    )


def test_missing_root_and_out_dir_exits_two(tmp_path, capsys):
    """Missing --root and --out-dir exits 2 per the leaf CLI contract."""
    mod = load_module()
    rc = mod.main([])
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"


def test_mutmut_not_installed_exits_two(tmp_path, capsys, monkeypatch):
    """When mutmut is not installed, the script exits 2 with ToolError.

    Uses monkeypatch on find_spec to simulate missing mutmut."""
    mod = load_module()

    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src/calc.py\n")
    src = tmp_path / "src"
    src.mkdir()
    (src / "calc.py").write_text("def add(a,b): return a+b\n")

    def _fake_find_spec(name):
        if name == "mutmut":
            return None
        return importlib.util.find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", _fake_find_spec)

    out = tmp_path / "out"
    rc = mod.main(
        [
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--paths",
            str(paths_file),
            "--tests-dir",
            "tests",
            "--max-mutants",
            "100",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "error"
    assert "mutmut" in data["message"].lower() or "install" in data["message"].lower()


# ---------------------------------------------------------------------------
# EXACTLY ONE real-mutmut integration test (subprocess, per plan A6)
# ---------------------------------------------------------------------------


def test_real_mutmut_integration(tmp_path):
    """Real mutmut run against fixtures/weakpkg.

    Skips with message 'mutmut not installed' only when
    importlib.util.find_spec('mutmut') is None.  Locally mutmut is installed
    so this test should RUN and PASS.

    Asserts:
    - Exit code 1 (findings present)
    - One TEST finding for src/calc.py
    - kill_rate 0.2
    - severity high
    - No side effects in tmp_path (no mutants/, no setup.cfg)
    """
    if importlib.util.find_spec("mutmut") is None:
        pytest.skip("mutmut not installed")

    # Copy weakpkg fixtures into tmp_path
    weakpkg = FIXTURES / "weakpkg"
    shutil.copytree(weakpkg, tmp_path, dirs_exist_ok=True)

    # Create paths file pointing to src
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src\n")

    out = tmp_path / "out"
    result = run_cli(
        "--root",
        str(tmp_path),
        "--out-dir",
        str(out),
        "--paths",
        str(paths_file),
        "--tests-dir",
        "tests",
        "--max-mutants",
        "100",
    )

    # Exit 1 means findings were emitted
    assert result.returncode == 1, (
        f"Expected exit 1, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Assert no side effects in tmp_path
    assert not (tmp_path / "mutants").exists(), (
        "mutants/ should not exist in target root"
    )
    assert not (tmp_path / "setup.cfg").exists(), (
        "setup.cfg should not exist in target root"
    )

    # All mutmut artifacts should be under out-dir/.mutmut-work
    mutmut_work = out / ".mutmut-work"
    assert mutmut_work.is_dir(), (
        f"Expected .mutmut-work under out-dir, but {mutmut_work} is not a directory"
    )

    # Read findings
    findings = json.loads((out / "test-effectiveness_findings.json").read_text())

    # Assert exactly one TEST finding for src/calc.py
    test_findings = [f for f in findings if f["signal"] == "TEST"]
    assert len(test_findings) == 1, (
        f"Expected 1 TEST finding, got {len(test_findings)}: {test_findings}"
    )
    f = test_findings[0]
    assert f["path"] == "src/calc.py", f"Unexpected path: {f['path']}"
    assert f["severity"] == "high", f"Unexpected severity: {f['severity']}"
    assert f["metric"]["name"] == "mutation_kill_rate", (
        f"Unexpected metric name: {f['metric']['name']}"
    )
    assert f["metric"]["value"] == 0.2, (
        f"Unexpected kill rate: {f['metric']['value']}"
    )
    assert f["confidence"] == "high", f"Unexpected confidence: {f['confidence']}"

    # Verify status line
    status = json.loads(result.stdout.strip().splitlines()[-1])
    assert status["status"] == "ok"
    assert status["findings"] == 1
    assert status["leaf"] == "test-effectiveness"
