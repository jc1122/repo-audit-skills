"""Golden/contract tests for triage_redundancy artifact idempotence.

Uses session-scoped fixtures to run main() only once per artifact set,
avoiding repeated ~50s subprocess invocations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from helpers import load_module

triage = load_module()

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_FILES = sorted(str(f) for f in FIXTURE_DIR.glob("fixture_math*.py"))


@pytest.fixture(autouse=True)
def _save_argv():
    saved = sys.argv[:]
    yield
    sys.argv = saved


def _run_main(out_dir: Path) -> None:
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


# ── Session-scoped: run main() once for structural golden checks ──────

@pytest.fixture(scope="class")
def golden_run(tmp_path_factory):
    """Run main() once and return the output directory."""
    out = tmp_path_factory.mktemp("golden")
    _run_main(out)
    return out


@pytest.fixture(scope="class")
def golden_runs(tmp_path_factory):
    """Run main() twice for idempotence checks."""
    run1 = tmp_path_factory.mktemp("run1")
    run2 = tmp_path_factory.mktemp("run2")
    _run_main(run1)
    _run_main(run2)
    return run1, run2


# ── Summary key structure tests (share one run) ──────────────────────

class TestGoldenSummaryKeys:
    def test_coverage_summary_keys(self, golden_run):
        data = json.loads((golden_run / "coverage_summary.json").read_text())
        assert {"generated_at", "mode", "tests_total"}.issubset(data.keys())

    def test_mutation_summary_keys(self, golden_run):
        data = json.loads((golden_run / "mutation_summary.json").read_text())
        assert {"generated_at", "tests_total"}.issubset(data.keys())

    def test_candidate_validation_summary_keys(self, golden_run):
        data = json.loads(
            (golden_run / "candidate_validation_summary.json").read_text()
        )
        assert {"generated_at", "counts", "baseline_pass"}.issubset(data.keys())

    def test_branch_equiv_summary_keys(self, golden_run):
        data = json.loads((golden_run / "branch_equiv_summary.json").read_text())
        assert {"generated_at", "pairs_total"}.issubset(data.keys())

    def test_coverage_matrix_not_empty(self, golden_run):
        rows = triage.read_csv_rows(golden_run / "coverage_matrix.csv")
        assert len(rows) > 0

    def test_mutation_matrix_not_empty(self, golden_run):
        rows = triage.read_csv_rows(golden_run / "mutation_matrix.csv")
        assert len(rows) > 0


# ── Idempotence tests (share two runs) ───────────────────────────────

class TestGoldenIdempotence:
    def test_inventory_idempotent(self, golden_runs):
        run1, run2 = golden_runs
        csv1 = (run1 / "inventory.csv").read_bytes()
        csv2 = (run2 / "inventory.csv").read_bytes()
        assert csv1 == csv2, "inventory.csv should be byte-identical"

    def test_mutation_matrix_idempotent(self, golden_runs):
        run1, run2 = golden_runs
        csv1 = (run1 / "mutation_matrix.csv").read_bytes()
        csv2 = (run2 / "mutation_matrix.csv").read_bytes()
        assert csv1 == csv2

    def test_confidence_gate_idempotent(self, golden_runs):
        run1, run2 = golden_runs
        csv1 = (run1 / "confidence_gate_matrix.csv").read_bytes()
        csv2 = (run2 / "confidence_gate_matrix.csv").read_bytes()
        assert csv1 == csv2

    def test_candidate_validation_decisions_idempotent(self, golden_runs):
        run1, run2 = golden_runs
        rows1 = triage.read_csv_rows(run1 / "candidate_validation.csv")
        rows2 = triage.read_csv_rows(run2 / "candidate_validation.csv")
        assert len(rows1) == len(rows2)
        d1 = {r["test_nodeid"]: r["validation_decision"] for r in rows1}
        d2 = {r["test_nodeid"]: r["validation_decision"] for r in rows2}
        assert d1 == d2

    def test_branch_equiv_structure(self, golden_runs):
        run1, run2 = golden_runs
        rows1 = triage.read_csv_rows(run1 / "branch_equiv_report.csv")
        rows2 = triage.read_csv_rows(run2 / "branch_equiv_report.csv")
        assert len(rows1) == len(rows2)
