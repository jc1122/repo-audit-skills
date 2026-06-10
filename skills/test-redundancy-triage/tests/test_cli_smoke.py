"""CLI smoke tests for triage_redundancy.py (thin subprocess).

Subprocess tests do NOT count toward in-process coverage but verify
the CLI interface works end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers import run_cli, read_csv

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_FILES = sorted(str(f) for f in FIXTURE_DIR.glob("fixture_math*.py"))


class TestCLIHelp:
    def test_help_exits_zero(self):
        result = run_cli(["--help"])
        assert result.returncode == 0

    def test_help_contains_usage(self):
        result = run_cli(["--help"])
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_no_args_shows_error(self):
        result = run_cli([], timeout=10)
        assert result.returncode != 0


# ── Shared CLI fixture run ────────────────────────────────────────

@pytest.fixture(scope="class")
def cli_run(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("cli_artifacts")
    fixture_root = str(FIXTURE_DIR.parent.resolve())
    args = [
        "--root", fixture_root,
        "--out-dir", str(out_dir),
        "--max-workers", "1",
        "--timeout-seconds", "60",
    ]
    for f in FIXTURE_FILES:
        args.extend(["--suite", f])
    result = run_cli(args, timeout=120)
    assert result.returncode == 0
    return out_dir


class TestCLIFixtureRun:
    def test_artifacts_exist(self, cli_run):
        expected = [
            "inventory.csv", "coverage_matrix.csv",
            "coverage_summary.json", "mutation_matrix.csv",
            "mutation_summary.json", "candidate_validation.csv",
            "candidate_validation_summary.json",
            "branch_equiv_report.csv", "branch_equiv_summary.json",
        ]
        for fname in expected:
            assert (cli_run / fname).exists(), f"Missing: {fname}"

    def test_candidate_csv_has_columns(self, cli_run):
        rows = read_csv(cli_run / "candidate_validation.csv")
        assert len(rows) >= 1
        for row in rows:
            assert "test_nodeid" in row
            assert "validation_decision" in row

    def test_summary_is_valid_json(self, cli_run):
        summary = json.loads(
            (cli_run / "candidate_validation_summary.json").read_text()
        )
        assert "counts" in summary
        assert "baseline_pass" in summary
