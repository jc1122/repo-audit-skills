import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "self_audit.py"


def test_help_exits_zero_fast_without_running_the_audit():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_unknown_argument_is_rejected():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--bogus"],
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert result.returncode == 2
