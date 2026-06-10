import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage_gap.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True, capture_output=True, timeout=120, check=False,
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
