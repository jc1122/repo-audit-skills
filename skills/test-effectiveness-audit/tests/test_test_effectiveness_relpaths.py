"""Relpath and side-effect tests for test-effectiveness-audit.

Covers:
- Findings paths must be root-relative POSIX and contain no absolute paths.
- Running the integration must not create mutants/ or setup.cfg in the
  fixture root or target root; all mutmut artifacts belong under
  out-dir/.mutmut-work.
"""
import json
import os
from pathlib import Path

import pytest

try:
    from helpers import load_module
except ImportError:
    pytest.skip("helpers module not yet available", allow_module_level=True)

_mod = None


def _get_mod():
    global _mod
    if _mod is None:
        _mod = load_module()
    return _mod


# ---------------------------------------------------------------------------
# Findings paths are root-relative POSIX
# ---------------------------------------------------------------------------


def test_findings_paths_are_root_relative_posix(tmp_path: Path):
    """Every path in findings must be root-relative and use POSIX separators.

    Absolute paths (starting with /) and backslash-separated paths are
    forbidden per the leaf CLI contract.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "src"
    mutants_dir.mkdir(parents=True)

    (mutants_dir / "calc.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "src.calc.x_weak__mutmut_1": 33,
                    "src.calc.x_weak__mutmut_2": 33,
                }
            }
        )
    )
    results = "    src.calc.x_weak__mutmut_1: no tests\n    src.calc.x_weak__mutmut_2: no tests\n"
    (work / "results.txt").write_text(results)

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)

    for f in findings:
        path = f.path
        # Must not be absolute
        assert not os.path.isabs(path), f"Path is absolute: {path}"
        # Must use POSIX separators
        assert "\\" not in path, f"Path contains backslashes: {path}"
        # Must be non-empty
        assert path, "Path is empty"


def test_findings_paths_use_forward_slash():
    """POSIX separator '/' is used in all findings paths (hard requirement)."""
    # This property is enforced by the implementation, not just by test data.
    # Verify that when we produce findings, paths use '/' not os.sep.
    # The path is constructed as as_posix() or equivalent in the impl.
    mod = _get_mod()
    work = Path("/tmp/_test_relpaths_work")
    work.mkdir(parents=True, exist_ok=True)
    mutants_dir = work / "mutants" / "pkg" / "sub"
    mutants_dir.mkdir(parents=True, exist_ok=True)

    try:
        (mutants_dir / "mod.py.meta").write_text(
            json.dumps(
                {
                    "exit_code_by_key": {
                        "pkg.sub.mod.x_f__mutmut_1": 33,
                    }
                }
            )
        )
        results = "    pkg.sub.mod.x_f__mutmut_1: no tests\n"
        (work / "results.txt").write_text(results)

        thresholds = {"min_kill_rate": 0.8}
        findings = mod.findings_from_mutmut(work, thresholds)

        for f in findings:
            assert "/" in f.path or f.path == f.path.replace("\\", "/"), (
                f"Path does not use forward slash: {f.path}"
            )
    finally:
        # Clean up
        import shutil
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)


def test_findings_paths_are_relative_to_root(tmp_path: Path):
    """Finding paths should not contain the absolute root path as a prefix.

    For example, if root is /tmp/..., a finding path of
    /tmp/.../src/calc.py would be an absolute leak.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "src"
    mutants_dir.mkdir(parents=True)

    (mutants_dir / "calc.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "src.calc.x_weak__mutmut_1": 33,
                }
            }
        )
    )
    (work / "results.txt").write_text(
        "    src.calc.x_weak__mutmut_1: no tests\n"
    )

    thresholds = {"min_kill_rate": 0.8}
    findings = mod.findings_from_mutmut(work, thresholds)

    for f in findings:
        # If the path starts with / or matches tmp_path, it's an absolute leak
        assert not f.path.startswith(str(tmp_path)), (
            f"Path contains absolute root prefix: {f.path}"
        )
        assert not f.path.startswith("/"), f"Path is absolute: {f.path}"


# ---------------------------------------------------------------------------
# Side-effect isolation
# ---------------------------------------------------------------------------


def test_findings_from_mutmut_does_not_create_side_effects(tmp_path: Path):
    """findings_from_mutmut() is a pure function — it reads from work/
    but must not create mutants/ or setup.cfg anywhere outside work/."""
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "src"
    mutants_dir.mkdir(parents=True)

    (mutants_dir / "calc.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "src.calc.x_weak__mutmut_1": 33,
                }
            }
        )
    )
    (work / "results.txt").write_text(
        "    src.calc.x_weak__mutmut_1: no tests\n"
    )

    thresholds = {"min_kill_rate": 0.8}
    _ = mod.findings_from_mutmut(work, thresholds)

    # No mutants/ or setup.cfg should appear in tmp_path (outside work/)
    assert not (tmp_path / "mutants").exists(), (
        "mutants/ should not be created in tmp_path"
    )
    assert not (tmp_path / "setup.cfg").exists(), (
        "setup.cfg should not be created in tmp_path"
    )


def test_sandbox_artifacts_stay_under_out_dir(tmp_path: Path):
    """If prepare_sandbox or equivalent creates files, they must be under
    out-dir/.mutmut-work, not in the target root.

    This test verifies the isolation contract by exercising the helper
    functions that set up the sandbox, without running real mutmut.
    """
    mod = _get_mod()

    # Create a minimal source tree
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "calc.py").write_text("def add(a,b): return a+b\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_calc.py").write_text("def test_add(): assert True\n")

    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("src\n")

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Exercise read_scope_paths
    rel_paths = mod.read_scope_paths(tmp_path, paths_file)
    assert len(rel_paths) >= 1
    assert "src" in rel_paths or "src/calc.py" in rel_paths

    # Exercise estimate_mutants
    est = mod.estimate_mutants(tmp_path, rel_paths, 8)
    assert est >= 1  # at least 1 function × 8 = 8

    # Exercise prepare_sandbox
    work = mod.prepare_sandbox(tmp_path, rel_paths, "tests", out_dir)
    assert work.exists()
    assert work.is_relative_to(out_dir) or str(work).startswith(str(out_dir)), (
        f"Sandbox work dir {work} must be under out-dir {out_dir}"
    )

    # setup.cfg should be in work, not in tmp_path
    assert (work / "setup.cfg").exists(), "setup.cfg should exist in sandbox"
    assert not (tmp_path / "setup.cfg").exists(), (
        "setup.cfg must not be in target root"
    )

    # mutants/ should not exist in tmp_path
    assert not (tmp_path / "mutants").exists(), (
        "mutants/ must not be in target root"
    )

    # Copied sources should be in work
    assert (work / "src" / "calc.py").exists(), (
        "src/calc.py should be copied to sandbox"
    )
    assert (work / "tests" / "test_calc.py").exists(), (
        "tests/test_calc.py should be copied to sandbox"
    )
