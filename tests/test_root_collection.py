import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_collect_only_is_clean():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "errors during collection" not in out
