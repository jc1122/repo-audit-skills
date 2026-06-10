"""Golden file tests: assert byte-equality against a frozen, path-portable JSON.

audit_test_quality.py resolves ``--root`` to an absolute path and echoes absolute
paths into its report (``root`` and each file ``path``). To keep the golden
portable across checkouts/worktrees/CI, we normalize the absolute fixture root to
the ``<FIXTURE_ROOT>`` placeholder before comparing and before freezing the
golden. The script's output contract is unchanged — only the test normalizes.
"""
import json
import tempfile
from pathlib import Path

import pytest

from helpers import FIXTURES, run_cli

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
GOLDEN_JSON = GOLDEN_DIR / "dirty_report.json"
DIRTY_ROOT = FIXTURES / "dirty"
PLACEHOLDER = "<FIXTURE_ROOT>"


def _normalize(raw: bytes) -> bytes:
    """Replace the machine-specific absolute fixture root with a placeholder."""
    return raw.decode("utf-8").replace(str(DIRTY_ROOT), PLACEHOLDER).encode("utf-8")


def _run_dirty(out_path: Path) -> bytes:
    result = run_cli("--root", str(DIRTY_ROOT), "--json-out", str(out_path))
    assert result.returncode == 0, result.stderr
    return _normalize(out_path.read_bytes())


@pytest.fixture(scope="module")
def golden_bytes():
    """Load the frozen (normalized) golden; generate it once if absent."""
    if not GOLDEN_JSON.exists():
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            GOLDEN_JSON.write_bytes(_run_dirty(Path(td) / "gen.json"))
    return GOLDEN_JSON.read_bytes()


def test_golden_json_byte_identical(tmp_path, golden_bytes):
    """Normalized script output must be byte-identical to the frozen golden."""
    current = _run_dirty(tmp_path / "current.json")
    assert current == golden_bytes, (
        "Normalized output diverged from the golden file. If the script behavior "
        "intentionally changed, regenerate fixtures/golden/dirty_report.json."
    )


def test_golden_is_path_portable(golden_bytes):
    """The frozen golden must contain no machine-specific absolute paths."""
    assert b"<FIXTURE_ROOT>" in golden_bytes
    assert b"/home/" not in golden_bytes


def test_golden_json_has_expected_structure(golden_bytes):
    """Golden JSON parses correctly and has all expected top-level keys."""
    report = json.loads(golden_bytes)
    assert "root" in report
    assert "config" in report
    assert "summary" in report
    assert "files" in report
    assert report["summary"]["totals"]["files"] >= 2
    assert report["summary"]["totals"]["internal_imports"] > 0
