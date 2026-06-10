"""Tests for artifact-gated leaf requires support (T5 umbrella v2)."""

import json

from helpers import FIXTURES, run_cli


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


def test_requires_skipped_when_no_artifact(tmp_path):
    """Gated leaf skipped without --coverage-json; not in summary leaves."""
    reg = _registry(tmp_path, [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
        {"name": "gated", "skill": "gated", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "gated_findings.json",
         "requires": {"coverage_json": True}},
    ])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 0  # empty leaf: PASS

    stdout = json.loads(result.stdout.strip())
    assert stdout["status"] == "ok"
    skipped = stdout.get("skipped", [])
    assert len(skipped) == 1
    assert skipped[0]["leaf"] == "gated"
    assert "coverage_json" in skipped[0]["reason"]

    summary = json.loads((out / "code_health_summary.json").read_text())
    assert "gated" not in summary["leaves"]
    assert "empty" in summary["leaves"]


def test_no_artifact_output_byte_identical(tmp_path):
    """Summary & report files are byte-identical with/without gated leaf when no --coverage-json."""
    leaf_empty = {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
                  "languages": ["python"], "findings_file": "empty_findings.json"}
    leaf_gated = {"name": "gated", "skill": "gated", "script": str(FIXTURES / "stub_leaf.py"),
                  "languages": ["python"], "findings_file": "gated_findings.json",
                  "requires": {"coverage_json": True}}

    # (a) registry WITHOUT the gated leaf
    reg_a = _registry(tmp_path, [leaf_empty])
    out_a = tmp_path / "out_a"
    run_cli("--root", str(tmp_path), "--out-dir", str(out_a), "--registry", str(reg_a))

    # (b) registry WITH the gated leaf
    reg_b = _registry(tmp_path, [leaf_empty, leaf_gated])
    out_b = tmp_path / "out_b"
    run_cli("--root", str(tmp_path), "--out-dir", str(out_b), "--registry", str(reg_b))

    summary_a = (out_a / "code_health_summary.json").read_bytes()
    summary_b = (out_b / "code_health_summary.json").read_bytes()
    report_a = (out_a / "code_health_report.md").read_bytes()
    report_b = (out_b / "code_health_report.md").read_bytes()

    assert summary_a == summary_b, "code_health_summary.json must be byte-identical"
    assert report_a == report_b, "code_health_report.md must be byte-identical"


def test_requires_runs_with_artifact(tmp_path):
    """Gated leaf RUNS with --coverage-json and its findings appear in summary."""
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text('{"files": {}}')

    leaf = {"name": "argv-log", "skill": "argv-log",
            "script": str(FIXTURES / "argv_log_leaf.py"),
            "languages": ["python"], "findings_file": "argv_log_findings.json",
            "requires": {"coverage_json": True}}

    reg = _registry(tmp_path, [leaf])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out),
                     "--registry", str(reg), "--coverage-json", str(cov_path))
    assert result.returncode == 1  # ADVISE (has finding)

    stdout = json.loads(result.stdout.strip())
    skipped = stdout.get("skipped", [])
    assert len(skipped) == 0

    # The leaf ran and its finding appears in the summary
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert "argv-log" in summary["leaves"]
    assert summary["leaves"]["argv-log"]["exit"] == 0

    # Verify --coverage-json was passed to the leaf's command
    argv_log = json.loads((out / "argv-log" / "argv_log.json").read_text())
    assert argv_log["has_coverage_json"] is True
    assert "--coverage-json" in argv_log["argv"]
    assert str(cov_path) in argv_log["argv"]


def test_unknown_requirement_is_skipped(tmp_path):
    """Leaf with unknown requires key is skipped (fail-safe)."""
    leaf = {"name": "bad", "skill": "bad", "script": str(FIXTURES / "stub_leaf.py"),
            "languages": ["python"], "findings_file": "bad_findings.json",
            "requires": {"bogus": True}}

    reg = _registry(tmp_path, [leaf])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))

    stdout = json.loads(result.stdout.strip())
    skipped = stdout.get("skipped", [])
    assert len(skipped) == 1
    assert skipped[0]["leaf"] == "bad"
    assert "bogus" in skipped[0]["reason"]

    # The gated leaf is absent from summary leaves
    assert not (out / "code_health_summary.json").exists() or "bad" not in json.loads(
        (out / "code_health_summary.json").read_text())["leaves"]


def test_real_registry_smoke(tmp_path):
    """Real post-T5 registry: coverage-gap skipped without --coverage-json."""
    from helpers import SKILL_ROOT
    real_registry = SKILL_ROOT / "scripts" / "leaf_registry.json"

    # Create a tiny fixture repo
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "__init__.py").write_text("")

    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--source-prefix", "pkg",
                     "--out-dir", str(out), "--registry", str(real_registry))

    stdout = json.loads(result.stdout.strip())
    skipped = stdout.get("skipped", [])
    skipped_names = [s["leaf"] for s in skipped]
    assert "coverage-gap" in skipped_names, f"Expected coverage-gap skipped, got {skipped_names}"

    # coverage-gap must NOT appear in summary leaves
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert "coverage-gap" not in summary["leaves"]
