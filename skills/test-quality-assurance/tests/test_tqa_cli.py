"""CLI smoke tests for audit_test_quality.py via subprocess."""

from helpers import FIXTURES, read_json, run_cli


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout
    assert "--json-out" in result.stdout


def test_clean_fixture_exits_zero(tmp_path):
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"
    result = run_cli(
        "--root", str(FIXTURES / "clean"),
        "--json-out", str(json_out),
        "--md-out", str(md_out),
    )
    assert result.returncode == 0
    assert json_out.exists()
    assert md_out.exists()


def test_dirty_fixture_exits_zero(tmp_path):
    """dirty fixture produces report with findings (exit 0 because it never fails)."""
    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(json_out),
    )
    assert result.returncode == 0
    report = read_json(json_out)
    assert report["summary"]["totals"]["files"] >= 1
    assert report["summary"]["totals"]["internal_imports"] > 0


def test_cli_with_custom_patterns(tmp_path):
    """Exercise custom internal-import-pattern and public-hint flags."""
    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--internal-import-pattern", r"from\s+[\w\.]+\.xyz\s+import",
        "--public-hint", "DataEngine(",
        "--json-out", str(json_out),
    )
    assert result.returncode == 0
    report = read_json(json_out)
    assert "DataEngine(" in report["config"]["public_hints"]


def test_cli_invalid_regex_exits_one(tmp_path):
    """Invalid regex should cause exit code 1."""
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--internal-import-pattern", r"[invalid",
        "--json-out", str(tmp_path / "report.json"),
    )
    assert result.returncode == 1


def test_cli_no_auto_public_hints(tmp_path):
    """--no-auto-public-hints flag should suppress inference."""
    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "clean"),
        "--no-auto-public-hints",
        "--json-out", str(json_out),
    )
    assert result.returncode == 0
    report = read_json(json_out)
    assert report["config"]["auto_inferred_public_hints"] is False


def test_cli_with_cov_json(tmp_path):
    """Pass coverage JSON for rubric scoring."""
    import json
    cov_data = {"totals": {"percent_covered": 88.0, "covered_branches": 70, "num_branches": 100}}
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps(cov_data))

    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(json_out),
        "--cov-json", str(cov_path),
    )
    assert result.returncode == 0
    report = read_json(json_out)
    assert "rubric_scores" in report
    assert report["rubric_scores"]["Coverage/Mutation"]["score"] >= 1


def test_cli_with_baseline_json(tmp_path):
    """Pass baseline JSON and get delta in report."""
    import json
    # First, create a baseline by running the script
    baseline_out = tmp_path / "baseline.json"
    run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(baseline_out),
    )

    # Now run with baseline
    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(json_out),
        "--baseline-json", str(baseline_out),
    )
    assert result.returncode == 0
    report = read_json(json_out)
    assert "delta" in report


def test_cli_default_md_output_to_stdout(tmp_path):
    """Without --md-out, markdown goes to stdout."""
    json_out = tmp_path / "report.json"
    result = run_cli(
        "--root", str(FIXTURES / "dirty"),
        "--json-out", str(json_out),
    )
    assert result.returncode == 0
    # Markdown should be printed to stdout
    assert "# Test Quality Inventory" in result.stdout
