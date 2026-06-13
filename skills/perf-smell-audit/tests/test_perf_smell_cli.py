import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "perf_smell_audit.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_cli_clean_exits_zero(tmp_path):
    out = tmp_path / "out"
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(FIXTURES / "clean"),
         "--source-prefix", "pkg/", "--out-dir", str(out)],
    ).returncode
    assert rc == 0
    assert json.loads((out / "perf-smell_findings.json").read_text()) == []


def test_cli_dirty_exits_one_with_findings(tmp_path):
    out = tmp_path / "out"
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(FIXTURES / "dirty"),
         "--source-prefix", "pkg/", "--out-dir", str(out)],
    ).returncode
    assert rc == 1
    data = json.loads((out / "perf-smell_findings.json").read_text())
    assert data and all(d["signal"] == "PERF" for d in data)
