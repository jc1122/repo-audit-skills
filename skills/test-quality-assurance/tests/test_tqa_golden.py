"""Golden file tests: assert byte-equality against frozen JSON output.

The golden file is generated once by running the script on the dirty fixture
and then frozen. This test asserts current output matches.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import FIXTURES, run_cli

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
GOLDEN_JSON = GOLDEN_DIR / "dirty_report.json"


def _generate_golden():
    """Generate the golden file (run once manually if it doesn't exist)."""
    GOLDEN_DIR.mkdir(exist_ok=True)
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(GOLDEN_JSON),
    )
    assert result.returncode == 0
    print(f"Golden file written to {GOLDEN_JSON}")
    # Return content for first-time use
    return GOLDEN_JSON.read_bytes()


@pytest.fixture(scope="module")
def golden_bytes():
    """Load (or generate) the golden file bytes."""
    if not GOLDEN_JSON.exists():
        return _generate_golden()
    return GOLDEN_JSON.read_bytes()


def test_golden_json_byte_identical(tmp_path, golden_bytes):
    """Current script output must be byte-identical to the golden file."""
    current = tmp_path / "current.json"
    run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(current),
    )
    assert current.read_bytes() == golden_bytes, (
        "Output diverged from golden file! "
        "If the script behavior intentionally changed, regenerate the golden file."
    )


def test_golden_json_has_expected_structure(golden_bytes):
    """Golden JSON parses correctly and has all expected top-level keys."""
    report = json.loads(golden_bytes)
    assert "root" in report
    assert "config" in report
    assert "summary" in report
    assert "files" in report
    assert report["summary"]["totals"]["files"] >= 2
    assert report["summary"]["totals"]["internal_imports"] > 0
