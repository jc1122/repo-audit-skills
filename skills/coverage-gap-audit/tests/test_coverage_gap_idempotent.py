import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "coverage_gap_audit.py"
DIRTY = SKILL / "tests" / "fixtures" / "uncovered"


def _run(out):
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(DIRTY),
         "--source-prefix", "pkg/",
         "--coverage-json", str(DIRTY / "coverage_partial.json"),
         "--out-dir", str(out)],
        text=True, capture_output=True, timeout=180, check=False,
    )
    return (out / "coverage-gap_findings.json").read_bytes()


def test_byte_identical_across_runs(tmp_path):
    assert _run(tmp_path / "a") == _run(tmp_path / "b")
