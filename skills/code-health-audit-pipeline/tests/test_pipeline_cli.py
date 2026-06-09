import json
from pathlib import Path

from helpers import FIXTURES, run_cli


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--registry" in result.stdout


def test_advise_run_writes_summary_and_report(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "stub", "skill": "stub", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "stub_findings.json"},
    ])
    out = tmp_path / "out"
    # stub emits one high DELETE finding (no gate) -> ADVISE / exit 1
    result = run_cli("--root", str(tmp_path), "--source-prefix", "pkg/",
                     "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 1
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "ADVISE"
    assert summary["exit_code"] == 1
    assert summary["leaves"]["stub"]["exit"] == 1
    assert (out / "code_health_report.md").exists()


def test_gate_on_errored_leaf_exits_two(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "err", "skill": "err", "script": str(FIXTURES / "error_leaf.py"),
         "languages": ["python"], "findings_file": "err_findings.json"},
    ])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 2
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "GATE"


def test_pass_when_empty(tmp_path):
    reg = _registry(tmp_path, [
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
    ])
    out = tmp_path / "out"
    result = run_cli("--root", str(tmp_path), "--out-dir", str(out), "--registry", str(reg))
    assert result.returncode == 0
    summary = json.loads((out / "code_health_summary.json").read_text())
    assert summary["supervisor"] == "PASS"
