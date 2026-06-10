"""Prong 2: In-process main() run against the frozen fixture suite.

Drives triage_redundancy.main() in-process against tests/fixtures/.
The subprocess calls inside main() are NOT traced, but main()'s own
orchestration and artifact-writing lines ARE traced in-process.

Keep it fast: --max-workers 1, no strict gate, minimal timeout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from helpers import load_module

triage = load_module()

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_FILES = sorted(str(f) for f in FIXTURE_DIR.glob("fixture_math*.py"))

assert FIXTURE_FILES, f"No fixture files found in {FIXTURE_DIR}"


@pytest.fixture(autouse=True)
def _save_argv():
    """Save and restore sys.argv around each test."""
    saved = sys.argv[:]
    yield
    sys.argv = saved


class TestMainInProcess:
    """Drive main() in-process against the fixture suite."""

    def test_main_basic_no_coverage(self, tmp_path, monkeypatch):
        """Run main() with minimum coverage collection.
        
        With --max-workers 1, --timeout-seconds 30, and no comparator suite,
        coverage collection should be fast and fall back to 'unavailable' mode
        (since the fixture isn't a real package with coverage tooling).
        """
        out_dir = tmp_path / "artifacts"
        fixture_root = FIXTURE_DIR.parent  # tests/
        
        sys.argv = [
            "triage_redundancy.py",
            "--root", str(fixture_root),
            "--out-dir", str(out_dir),
            "--max-workers", "1",
            "--timeout-seconds", "60",
        ]
        for f in FIXTURE_FILES:
            sys.argv.extend(["--suite", f])

        # Monkeypatch any env that might interfere
        monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

        result = triage.main()
        assert result == 0

        # Check that core artifacts were created
        assert (out_dir / "inventory.csv").exists()
        assert (out_dir / "coverage_matrix.csv").exists()
        assert (out_dir / "coverage_summary.json").exists()
        assert (out_dir / "mutation_matrix.csv").exists()
        assert (out_dir / "mutation_summary.json").exists()
        # candidate_validation.csv is always written
        assert (out_dir / "candidate_validation.csv").exists()
        assert (out_dir / "candidate_validation_summary.json").exists()
        # branch equiv report - may be empty if coverage unavailable
        assert (out_dir / "branch_equiv_report.csv").exists()
        assert (out_dir / "branch_equiv_summary.json").exists()

    def test_main_with_help_arg(self):
        """--help should raise SystemExit(0)."""
        sys.argv = ["triage_redundancy.py", "--help"]
        with pytest.raises(SystemExit) as exc:
            triage.main()
        assert exc.value.code == 0

    def test_main_no_suite_raises(self, tmp_path):
        """Missing --suite should raise SystemExit."""
        sys.argv = [
            "triage_redundancy.py",
            "--root", str(tmp_path),
            "--out-dir", str(tmp_path / "out"),
        ]
        with pytest.raises(SystemExit):
            triage.main()

    def test_main_baseline_output(self, tmp_path):
        """Verify key artifact CSV content after a run."""
        out_dir = tmp_path / "artifacts"
        fixture_root = FIXTURE_DIR.parent

        sys.argv = [
            "triage_redundancy.py",
            "--root", str(fixture_root),
            "--out-dir", str(out_dir),
            "--max-workers", "1",
            "--timeout-seconds", "60",
        ]
        for f in FIXTURE_FILES:
            sys.argv.extend(["--suite", f])

        result = triage.main()
        assert result == 0

        # Verify inventory.csv content
        rows = triage.read_csv_rows(out_dir / "inventory.csv")
        assert len(rows) > 0
        # Each row should have the expected columns
        for row in rows:
            assert "test_nodeid" in row
            assert "file" in row
            assert "entrypoint" in row
            assert "intent" in row
            assert "assertion_types" in row

        # Verify candidate_validation.csv content
        val_rows = triage.read_csv_rows(out_dir / "candidate_validation.csv")
        assert len(val_rows) >= 1
        decisions = {r.get("validation_decision", "") for r in val_rows}
        # Should have at least one decision
        assert len(decisions) > 0

    def test_main_discoveries_count(self, tmp_path):
        """The fixture has 3 test files with known test counts."""
        out_dir = tmp_path / "artifacts"
        fixture_root = FIXTURE_DIR.parent

        sys.argv = [
            "triage_redundancy.py",
            "--root", str(fixture_root),
            "--out-dir", str(out_dir),
            "--max-workers", "1",
            "--timeout-seconds", "60",
        ]
        for f in FIXTURE_FILES:
            sys.argv.extend(["--suite", f])

        result = triage.main()
        assert result == 0

        # Count tests discovered
        inv_rows = triage.read_csv_rows(out_dir / "inventory.csv")
        assert len(inv_rows) >= 6  # at least 6 test functions across 3 files
