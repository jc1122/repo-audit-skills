import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run():
    return subprocess.run(
        [sys.executable, "scripts/check_vendored_common.py"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )


def test_passes_when_no_copies_or_copies_match():
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
