"""In-process tests for artifact-gated leaf logic (T5 umbrella v2).
These call pipeline functions directly so pytest-cov can trace them."""

import io
import json
from contextlib import redirect_stdout

from helpers import FIXTURES, load_module

ch = load_module()


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


# ---------------------------------------------------------------------------
# _partition_leaves unit tests
# ---------------------------------------------------------------------------
def test_partition_no_requires_is_runnable():
    leaves = [{"name": "x", "languages": ["python"]}]
    runnable, skipped = ch._partition_leaves(leaves, None)
    assert [r["name"] for r in runnable] == ["x"]
    assert skipped == []


def test_partition_coverage_json_missing_skips():
    leaves = [{"name": "g", "requires": {"coverage_json": True}, "languages": ["python"]}]
    runnable, skipped = ch._partition_leaves(leaves, None)
    assert runnable == []
    assert len(skipped) == 1
    assert skipped[0]["leaf"] == "g"
    assert skipped[0]["reason"] == "requires coverage_json artifact"


def test_partition_coverage_json_present_runs():
    leaves = [{"name": "g", "requires": {"coverage_json": True}, "languages": ["python"]}]
    runnable, skipped = ch._partition_leaves(leaves, "/tmp/cov.json")
    assert [r["name"] for r in runnable] == ["g"]
    assert skipped == []


def test_partition_unknown_requirement_skipped():
    leaves = [{"name": "b", "requires": {"bogus": True}, "languages": ["python"]}]
    runnable, skipped = ch._partition_leaves(leaves, None)
    assert runnable == []
    assert len(skipped) == 1
    assert skipped[0]["leaf"] == "b"
    assert skipped[0]["reason"] == "requires bogus artifact"


def test_partition_skipped_sorted_by_name():
    leaves = [
        {"name": "z", "requires": {"coverage_json": True}, "languages": ["python"]},
        {"name": "a", "requires": {"coverage_json": True}, "languages": ["python"]},
        {"name": "m", "requires": {"coverage_json": True}, "languages": ["python"]},
    ]
    _runnable, skipped = ch._partition_leaves(leaves, None)
    assert [s["leaf"] for s in skipped] == ["a", "m", "z"]


def test_partition_mixed_runnable_and_skipped():
    leaves = [
        {"name": "no-req", "languages": ["python"]},
        {"name": "gated-cov", "requires": {"coverage_json": True}, "languages": ["python"]},
        {"name": "unknown-req", "requires": {"bogus": True}, "languages": ["python"]},
    ]
    runnable, skipped = ch._partition_leaves(leaves, None)
    assert [r["name"] for r in runnable] == ["no-req"]
    assert {s["leaf"] for s in skipped} == {"gated-cov", "unknown-req"}

    # With coverage_json → gated-cov becomes runnable
    runnable, skipped = ch._partition_leaves(leaves, "/tmp/cov.json")
    assert [r["name"] for r in runnable] == ["no-req", "gated-cov"]
    assert {s["leaf"] for s in skipped} == {"unknown-req"}


# ---------------------------------------------------------------------------
# run_leaves / _run_one in-process tests
# ---------------------------------------------------------------------------
def test_run_leaves_passes_coverage_json_to_gated_leaf(tmp_path):
    """Combo test: run_leaves + _run_one pass --coverage-json when leaf requires it."""
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text("{}")

    leaves = [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
        {"name": "argv-log", "skill": "argv-log", "script": str(FIXTURES / "argv_log_leaf.py"),
         "languages": ["python"], "findings_file": "argv_log_findings.json",
         "requires": {"coverage_json": True}},
    ]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(
        leaves, root=str(tmp_path), source_prefixes=["pkg/"],
        out_dir=out, overrides={}, coverage_json=str(cov_path),
    )
    # argv-log leaf ran and emitted findings
    assert "argv-log" in leaf_exit
    argv_log = json.loads((out / "argv-log" / "argv_log.json").read_text())
    assert argv_log["has_coverage_json"] is True
    assert "--coverage-json" in argv_log["argv"]
    assert str(cov_path) in argv_log["argv"]


# ---------------------------------------------------------------------------
# main() in-process tests (covers partition/skip/write branches)
# ---------------------------------------------------------------------------
def test_main_no_artifact_skips_gated_leaf(tmp_path):
    """In-process main() without --coverage-json: gated leaf skipped."""
    leaves = [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
        {"name": "gated", "skill": "gated", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "gated_findings.json",
         "requires": {"coverage_json": True}},
    ]
    reg = _registry(tmp_path, leaves)
    out = tmp_path / "out"
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ch.main([
            "--root", str(tmp_path), "--out-dir", str(out),
            "--registry", str(reg),
        ])
    assert code == 0  # empty leaf passes
    stdout = json.loads(buf.getvalue().strip())
    assert stdout["status"] == "ok"
    skipped = stdout.get("skipped", [])
    assert len(skipped) == 1
    assert skipped[0]["leaf"] == "gated"
    assert "coverage_json" in skipped[0]["reason"]

    summary = json.loads((out / "code_health_summary.json").read_text())
    assert "gated" not in summary["leaves"]
    assert "empty" in summary["leaves"]


def test_main_with_artifact_runs_gated_leaf(tmp_path):
    """In-process main() with --coverage-json: gated leaf runs."""
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text("{}")

    leaves = [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
        {"name": "argv-log", "skill": "argv-log", "script": str(FIXTURES / "argv_log_leaf.py"),
         "languages": ["python"], "findings_file": "argv_log_findings.json",
         "requires": {"coverage_json": True}},
    ]
    reg = _registry(tmp_path, leaves)
    out = tmp_path / "out"
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ch.main([
            "--root", str(tmp_path), "--out-dir", str(out),
            "--registry", str(reg),
            "--coverage-json", str(cov_path),
        ])
    assert code == 1  # ADVISE (argv-log emits a finding)
    stdout = json.loads(buf.getvalue().strip())
    skipped = stdout.get("skipped", [])
    assert skipped == []

    summary = json.loads((out / "code_health_summary.json").read_text())
    assert "argv-log" in summary["leaves"]
    assert summary["leaves"]["argv-log"]["exit"] == 0


def test_real_registry_test_effectiveness_skipped_without_mutation_scope():
    """The registered test-effectiveness leaf (requires mutation_scope) fail-safe
    skips when its artifact is absent, so it never enters the runnable set and
    therefore never gates the pipeline."""
    leaves = ch.load_registry(ch.DEFAULT_REGISTRY)
    runnable, skipped = ch._partition_leaves(leaves, None)
    assert {"leaf": "test-effectiveness", "reason": "requires mutation_scope artifact"} in skipped
    assert "test-effectiveness" not in {r["name"] for r in runnable}
