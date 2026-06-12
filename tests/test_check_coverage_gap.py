import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage_gap.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_help_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_empty_coverage_report_fails_the_ratchet(tmp_path):
    report = tmp_path / "cov.json"
    report.write_text(json.dumps({"files": {}}))
    result = _run("--coverage-json", str(report))
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["new_findings"], "zero coverage must surface new findings"


def test_injection_mode_in_process(tmp_path, capsys):
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_coverage_gap", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = tmp_path / "cov.json"
    report.write_text(json.dumps({"files": {}}))
    rc = mod.main(["--coverage-json", str(report)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "fail"
    assert payload["new_findings"]


def test_per_suite_coverage_files_are_combined(tmp_path, monkeypatch):
    """Each suite gets its own COVERAGE_FILE; combine produces one report."""
    import scripts.check_coverage_gap as gate

    env = gate.suite_env(out_dir=tmp_path, suite="skills/quality-audit/tests")
    assert env["COVERAGE_FILE"].endswith(".coverage.skills_quality-audit_tests")
