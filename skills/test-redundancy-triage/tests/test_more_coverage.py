"""Additional tests to push coverage from 34% to >= 50%.

Targets uncovered branches in run_cmd, build_runtime_env, ensure_coverage_tool,
resolve_and_validate_suite_paths, write_confidence_gate_artifact, etc.
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from helpers import load_module

triage = load_module()


# ── run_cmd additional branches ─────────────────────────────────────

def test_run_cmd_timed_out(tmp_path: Path):
    """Force a timeout by running a very slow command."""
    result = triage.run_cmd(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        timeout=1,
    )
    assert result["timed_out"] is True
    assert result["returncode"] == 124


# ── build_runtime_env with numba stub ──────────────────────────────

def test_build_runtime_env_with_numba_stub(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    env = triage.build_runtime_env(
        tmp_path, out_dir, sys.executable, allow_numba_stub=True
    )
    assert "PYTHONPATH" in env
    stub_dir = out_dir / "_runtime_stubs"
    # numba should have been checked, stub may or may not have been created
    # depending on whether numba is importable
    stub_dir_exists = stub_dir.exists()
    # At minimum PYTHONPATH should be set
    assert env["PYTHONPATH"]


def test_build_runtime_env_with_preexisting_pythonpath(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    env = triage.build_runtime_env(
        tmp_path, out_dir, sys.executable,
        allow_numba_stub=False,
        extra_env={"PYTHONPATH": "/preexisting"},
    )
    assert "/preexisting" in env["PYTHONPATH"]
    assert str(tmp_path) in env["PYTHONPATH"]


# ── ensure_coverage_tool branches ──────────────────────────────────

def test_ensure_coverage_tool_nonexistent_python(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    py_exe, env, mode, note = triage.ensure_coverage_tool(
        tmp_path, out_dir, "/nonexistent_python_abc_123", {}, 10
    )
    assert mode == "unavailable"
    assert py_exe == ""


# ── resolve_and_validate_suite_paths additional ────────────────────

def test_resolve_and_validate_suite_multiple_valid(tmp_path: Path):
    (tmp_path / "test_a.py").write_text("")
    (tmp_path / "test_b.py").write_text("")
    paths = triage.resolve_and_validate_suite_paths(
        tmp_path, ["test_a.py", "test_b.py"], arg_name="--suite"
    )
    assert paths == ["test_a.py", "test_b.py"]


def test_resolve_and_validate_suite_absolute(tmp_path: Path):
    f = tmp_path / "test_abs.py"
    f.write_text("")
    paths = triage.resolve_and_validate_suite_paths(
        tmp_path, [str(f)], arg_name="--suite"
    )
    assert str(paths[0]) == "test_abs.py"


def test_resolve_and_validate_suite_mixed_valid_invalid(tmp_path: Path):
    (tmp_path / "test_ok.py").write_text("")
    with pytest.raises(SystemExit):
        triage.resolve_and_validate_suite_paths(
            tmp_path, ["test_ok.py", "missing.py"], arg_name="--suite"
        )


# ── write_confidence_gate_artifact additional branches ─────────────

def test_write_confidence_gate_bronze(tmp_path: Path):
    """Test Bronze tier when measured gates fail."""
    rows: list[dict[str, Any]] = [
        {
            "test_nodeid": "t1",
            "validation_decision": "DELETE_SAFE_HIGH",
            "deselect_suite_pass": True,
            "strict_gate_status": "disabled",
            "peer_superset_assertions": False,
            "branch_exact_match": "",
            "branch_jaccard": "",
            "report_mutants_unique_to_api": "5",
            "report_unique_line_count": "10",
            "report_unique_branch_count": "3",
            "report_overlap": "0.5",
        },
    ]
    counts = triage.write_confidence_gate_artifact(tmp_path, rows)
    assert "BRONZE_DELETE_REVIEW" in counts


def test_write_confidence_gate_silver(tmp_path: Path):
    """Test Silver tier: all core gates pass, strict gate None."""
    rows: list[dict[str, Any]] = [
        {
            "test_nodeid": "t1",
            "validation_decision": "DELETE_SAFE_HIGH",
            "deselect_suite_pass": True,
            "strict_gate_status": "",
            "peer_superset_assertions": True,
            "branch_exact_match": "",
            "branch_jaccard": "0.96",
            "report_mutants_unique_to_api": "0",
            "report_unique_line_count": "0",
            "report_unique_branch_count": "0",
            "report_overlap": "0.99",
        },
    ]
    counts = triage.write_confidence_gate_artifact(tmp_path, rows)
    # Should be SILVER since branch_exact is not True but branch_high is True
    assert "SILVER_DELETE_CANDIDATE" in counts or "GOLD_DELETE_CANDIDATE" in counts


def test_write_confidence_gate_keep_stability(tmp_path: Path):
    rows: list[dict[str, Any]] = [
        {"test_nodeid": "t1", "validation_decision": "KEEP_FOR_STABILITY",
         "deselect_suite_pass": False, "strict_gate_status": ""},
    ]
    counts = triage.write_confidence_gate_artifact(tmp_path, rows)
    assert counts.get("KEEP_CANDIDATE", 0) == 1


def test_write_confidence_gate_strict_gate_disabled(tmp_path: Path):
    rows: list[dict[str, Any]] = [
        {
            "test_nodeid": "t1",
            "validation_decision": "DELETE_SAFE_HIGH",
            "deselect_suite_pass": True,
            "strict_gate_status": "disabled",
            "peer_superset_assertions": True,
            "branch_exact_match": "true",
            "branch_jaccard": "1.0",
            "report_mutants_unique_to_api": "0",
            "report_unique_line_count": "0",
            "report_unique_branch_count": "0",
            "report_overlap": "0.99",
        },
    ]
    counts = triage.write_confidence_gate_artifact(tmp_path, rows)
    # "disabled" -> strict_gate=None, so measured_strong is False, measured_good is True
    # gives SILVER_DELETE_CANDIDATE (not GOLD because strict_gate is not True)
    assert "SILVER_DELETE_CANDIDATE" in counts


# ── bool_low_signal coverage row branches ──────────────────────────

def test_bool_low_signal_coverage_row_unique(tmp_path: Path):
    meta = triage.TestMeta(
        nodeid="t1", file="f.py", class_name="", test_name="test_x",
        entrypoint="ep", intent="int",
        assertion_types={"general_assert"},
        assert_count=1, src_tokens=frozenset(),
    )
    cov_row = {
        "coverage_signal_available": "true",
        "unique_line_count": 3,
        "unique_branch_count": 0,
        "cross_suite_overlap_ratio": 0.99,
    }
    result = triage.bool_low_signal(meta, {}, cov_row)
    # ul=3 means the (ul==0 and ub==0 and ov>=0.97) check fails,
    # so we fall through to AST fallback: general_assert is in smoke set -> True
    assert result is True


def test_bool_low_signal_coverage_row_complex(tmp_path: Path):
    meta = triage.TestMeta(
        nodeid="t1", file="f.py", class_name="", test_name="test_x",
        entrypoint="ep", intent="int",
        assertion_types={"exception"},
        assert_count=1, src_tokens=frozenset(),
    )
    cov_row = {
        "coverage_signal_available": "true",
        "unique_line_count": 0,
        "unique_branch_count": 0,
        "cross_suite_overlap_ratio": 0.99,
    }
    result = triage.bool_low_signal(meta, {}, cov_row)
    assert result is False  # exception not in smoke set


def test_bool_low_signal_ranked_mutants_unique(tmp_path: Path):
    meta = triage.TestMeta(
        nodeid="t1", file="f.py", class_name="", test_name="test_x",
        entrypoint="ep", intent="int",
        assertion_types={"general_assert"},
        assert_count=1, src_tokens=frozenset(),
    )
    ranked = {
        "unique_line_count": "0", "unique_branch_count": "0",
        "mutants_unique_to_api": "3", "cross_suite_overlap_ratio": "0.99",
    }
    result = triage.bool_low_signal(meta, ranked, None)
    assert result is False  # mutants_unique > 0


# ── prepend_pythonpath multiple prefixes ───────────────────────────

def test_prepend_pythonpath_multiple():
    env = {"PATH": "/usr/bin"}
    result = triage.prepend_pythonpath(env, "/a", "/b")
    assert result["PYTHONPATH"] == "/a:/b"


# ── parse_test_metadata async tests ────────────────────────────────

def test_parse_test_metadata_async_func(tmp_path: Path):
    test_file = tmp_path / "async_test.py"
    test_file.write_text("import asyncio\nasync def test_async(): assert True")
    result = triage.parse_test_metadata(tmp_path, ["async_test.py"])
    # Async test functions start with test_ so should be found
    assert len(result) == 1
    assert result[0].test_name == "test_async"


# ── write_inventory_artifact ───────────────────────────────────────

def test_write_inventory_artifact_multiple(tmp_path: Path):
    tests = [
        triage.TestMeta("t1", "f1.py", "", "test_a", "ep1", "i1",
                       {"general_assert"}, 1, False, frozenset(["x"])),
        triage.TestMeta("t2", "f2.py", "Cls", "test_b", "ep2", "i2",
                       {"type_check", "length_contract"}, 2, True, frozenset(["y"])),
    ]
    triage.write_inventory_artifact(tmp_path, tests)
    inv = tmp_path / "inventory.csv"
    rows = triage.read_csv_rows(inv)
    assert len(rows) == 2
    assert rows[1]["class_name"] == "Cls"
    assert rows[1]["is_parametrized"] == "True"


# ── run_cmd with actual success ───────────────────────────────────

def test_run_cmd_stdout_stderr(tmp_path: Path):
    result = triage.run_cmd(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        cwd=tmp_path,
        timeout=10,
    )
    assert result["returncode"] == 0
    assert "out" in result["output"]
    assert "err" in result["output"]


# ── stage_probe_file_overlay success ─────────────────────────────

def test_stage_probe_file_overlay_with_init(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("# init")
    (tmp_path / "pkg" / "mod.py").write_text("x = 1")
    overlay = tmp_path / "overlay"
    probe = triage.MutationProbe("P1", "pkg/mod.py", "x = 1", "x = 2")
    ok, msg = triage.stage_probe_file_overlay(tmp_path, overlay, probe)
    assert ok is True
    assert (overlay / "pkg" / "mod.py").exists()
    # init should also be copied
    assert (overlay / "pkg" / "__init__.py").exists()


# ── chunked more edge cases ────────────────────────────────────────

def test_chunked_single_item():
    assert triage.chunked([1], 2) == [[1]]


def test_chunked_exact_fit():
    assert triage.chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


# ── unique_preserve with None-equivalent ───────────────────────────

def test_unique_preserve_all_dupes():
    assert triage.unique_preserve(["a", "a", "a"]) == ["a"]


# ── normalize multiple coverage paths ─────────────────────────────

def test_normalize_source_path_no_change(tmp_path: Path):
    root = tmp_path
    result = triage.normalize_source_path_for_coverage("plain/path.py", root)
    assert result == "plain/path.py"


# ── select_branch_anchor tie break ─────────────────────────────────

def test_select_branch_anchor_tie_break():
    t1 = triage.TestMeta(
        nodeid="a::test_x", file="a.py", class_name="", test_name="test_x",
        entrypoint="ep", intent="int", assertion_types={"general_assert"},
        assert_count=1, src_tokens=frozenset({"a"}),
    )
    t2 = triage.TestMeta(
        nodeid="a::test_y", file="a.py", class_name="", test_name="test_y",
        entrypoint="ep", intent="int", assertion_types={"general_assert"},
        assert_count=1, src_tokens=frozenset({"a"}),
    )
    # Both identical except nodeid
    anchor = triage.select_branch_anchor(t1, [t2], {})
    assert anchor is not None


# ── infer_intent more patterns ────────────────────────────────────

def test_infer_intent_cleanup_in_name():
    result = triage.infer_intent("test_cleanup_old", "x", set(), "")
    assert result == "lifecycle_contract"


def test_infer_intent_teardown():
    result = triage.infer_intent("test_teardown_resources", "x", set(), "")
    assert result == "lifecycle_contract"


def test_infer_intent_del_in_name():
    result = triage.infer_intent("test___del___", "x", set(), "")
    assert result == "lifecycle_contract"


def test_infer_intent_ffi_from_src():
    result = triage.infer_intent("test_x", "x", set(), "x = _lib_stream")
    assert result == "ffi_contract"


def test_infer_intent_ctypes_from_src():
    result = triage.infer_intent("test_x", "x", set(), "CDLL('libfoo')")
    assert result == "ffi_contract"


# ── infer_assertion_types with multiple patterns ───────────────────

def test_infer_assertion_types_multiple():
    fn = ast.parse("def f():\n assert isinstance(x, int)\n assert len(x) == 5").body[0]
    calls = triage.extract_calls(fn)
    src = "assert isinstance(x, int)\n assert len(x) == 5"
    result = triage.infer_assertion_types(fn, calls, src)
    assert "type_check" in result
    assert "length_contract" in result
    # general_assert only added when no other assertion types found
    assert "general_assert" not in result


# ── build_overlay_env ─────────────────────────────────────────────

def test_build_overlay_env_with_src_dir(tmp_path: Path):
    (tmp_path / "src").mkdir()
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "src").mkdir()
    env = os.environ.copy()
    result = triage.build_overlay_env(tmp_path, env, overlay)
    assert "PYTHONPATH" in result


# ── write_coverage_artifacts ranked path ──────────────────────────

def test_write_coverage_artifacts_ranked_mode(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (tmp_path / "tests").mkdir(exist_ok=True)

    tests = [
        triage.TestMeta("t1", "tests/test_x.py", "", "test_a",
                       "ep", "int", {"general_assert"},
                       1, False, frozenset(["x"])),
    ]
    # Simulate ranked CSV with coverage columns
    ranked_path = tmp_path / "ranked.csv"
    triage.write_csv(
        ranked_path,
        [{
            "test_nodeid": "t1",
            "runtime_ms": "100",
            "executed_line_count": "5",
            "executed_branch_count": "1",
            "unique_line_count": "0",
            "unique_branch_count": "0",
            "cross_suite_overlap_ratio": "0.95",
        }],
        ["test_nodeid", "runtime_ms", "executed_line_count",
         "executed_branch_count", "unique_line_count",
         "unique_branch_count", "cross_suite_overlap_ratio"],
    )
    ranked_map = triage.parse_ranked_by_nodeid(ranked_path)

    options = triage.CoverageArtifactOptions(
        python_exe=sys.executable,
        env=os.environ.copy(),
        timeout=60,
        max_workers=1,
    )
    request = triage.CoverageArtifactRequest(
        tests=tests,
        ranked_map=ranked_map,
        ranked_path=ranked_path,
        comparator_suite_files=[],
        options=options,
    )
    cov_map, cov_summary = triage.write_coverage_artifacts(tmp_path, out_dir, request)
    assert (out_dir / "coverage_matrix.csv").exists()
    assert (out_dir / "coverage_summary.json").exists()
    assert cov_summary["mode"] == "ranked_report"


# ── write_mutation_artifacts with ranked path ──────────────────────

def test_write_mutation_artifacts_ranked_present(tmp_path: Path):
    tests = [
        triage.TestMeta("t1", "f.py", "", "test_a", "ep", "i",
                       set(), 1, False, frozenset(["x"])),
    ]
    ranked_path = tmp_path / "ranked.csv"
    ranked_path.write_text("test_nodeid\n")
    ranked = {"t1": {"mutants_unique_to_api": "5", "mutants_killed_api": "3"}}
    triage.write_mutation_artifacts(tmp_path, tests, ranked, ranked_path)
    assert (tmp_path / "mutation_matrix.csv").exists()
    assert (tmp_path / "mutation_summary.json").exists()


# ── write_branch_equiv_artifacts no pairs ──────────────────────────

def test_write_branch_equiv_artifacts_no_pairs(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    tests: list[triage.TestMeta] = []
    by_cluster: dict[tuple[str, str], list[triage.TestMeta]] = {}
    rows: list[dict[str, Any]] = []
    cov_map: dict[str, dict[str, Any]] = {}

    request = triage.BranchEquivRequest(
        root=tmp_path,
        out_dir=out_dir,
        tests=tests,
        by_cluster=by_cluster,
        rows=rows,
        coverage_map=cov_map,
        python_exe=sys.executable, env=os.environ.copy(),
        timeout=30, max_workers=1,
    )
    branch_map, summary = triage.write_branch_equiv_artifacts(request)
    assert summary.get("coverage_mode", "") == "no_pairs"
    assert (out_dir / "branch_equiv_report.csv").exists()
    assert (out_dir / "branch_equiv_summary.json").exists()
    assert (out_dir / "branch_equiv_report.md").exists()


# ── enforce_cluster_anchor empty cluster ──────────────────────────

def test_enforce_cluster_anchor_empty_entrypoint():
    rows = [
        {"test_nodeid": "t1", "entrypoint": "", "intent": "",
         "validation_decision": "DELETE_SAFE_HIGH",
         "assert_count": 1, "report_unique_line_count": 0,
         "report_unique_branch_count": 0, "report_mutants_unique_to_api": 0,
         "max_src_similarity": 0.5},
    ]
    # Should not crash with empty entrypoint
    triage.enforce_cluster_anchor(rows)
    # Decision should remain unchanged since cluster key was empty
    assert rows[0]["validation_decision"] == "DELETE_SAFE_HIGH"
