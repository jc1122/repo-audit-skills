"""Thin subprocess smoke tests for the CLI entry-point of audit_pipeline.py.

Kept intentionally light — the in-process tests exercise the core logic.
These verify the self-contained behaviours: --help, --version-like output,
and error exits.
"""

from helpers import run_cli


def test_cli_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_cli_missing_out_dir_exits_nonzero():
    result = run_cli("--root", "/tmp")
    assert result.returncode != 0
    # argparse should mention that --out-dir is required
    assert "out-dir" in (result.stdout + result.stderr).lower()


def test_cli_missing_root_exits_nonzero():
    result = run_cli("--out-dir", "/tmp")
    assert result.returncode != 0
    assert "root" in (result.stdout + result.stderr).lower()


def test_cli_bad_tqa_script_exits_one(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = run_cli(
        "--root", str(tmp_path),
        "--out-dir", str(out_dir),
        "--skip-coverage",
        "--tqa-script", "/nonexistent/tqa.py",
    )
    assert result.returncode == 1


def test_cli_bad_triage_script_exits_one(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = run_cli(
        "--root", str(tmp_path),
        "--out-dir", str(out_dir),
        "--skip-coverage",
        "--triage-script", "/nonexistent/triage.py",
        "--suite", "dummy_test.py",
    )
    assert result.returncode == 1
