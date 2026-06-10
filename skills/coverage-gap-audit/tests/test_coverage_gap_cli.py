from helpers import FIXTURES, read_findings, run_cli


def _dirty_args(out):
    return (
        "--root", str(FIXTURES / "uncovered"),
        "--source-prefix", "pkg/",
        "--coverage-json", str(FIXTURES / "uncovered" / "coverage_partial.json"),
        "--out-dir", str(out),
    )


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--coverage-json" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli(
        "--root", str(FIXTURES / "covered"),
        "--source-prefix", "pkg/",
        "--coverage-json", str(FIXTURES / "covered" / "coverage_full.json"),
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_gappy_exits_one_with_findings(tmp_path):
    result = run_cli(*_dirty_args(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert all(d["signal"] == "TEST" for d in data)
    assert (tmp_path / "coverage-gap_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli(*_dirty_args(a))
    run_cli(*_dirty_args(b))
    assert (a / "coverage-gap_findings.json").read_bytes() == (
        b / "coverage-gap_findings.json"
    ).read_bytes()


def test_missing_coverage_report_exits_two(tmp_path):
    result = run_cli(
        "--root", str(FIXTURES / "covered"),
        "--coverage-json", str(tmp_path / "nope.json"),
        "--out-dir", str(tmp_path),
    )
    assert result.returncode == 2
    assert "unreadable coverage report" in result.stdout


def test_missing_required_args_exits_two(tmp_path):
    result = run_cli("--root", str(FIXTURES / "covered"), "--out-dir", str(tmp_path))
    assert result.returncode == 2
