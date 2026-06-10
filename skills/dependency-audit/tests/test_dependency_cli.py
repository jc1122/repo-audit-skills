import json

from helpers import load_module, run_cli, FIXTURES


def test_help_exits_zero():
    """Subprocess smoke test: --help prints usage and exits 0."""
    result = run_cli("--help")
    assert result.returncode == 0


def test_missing_root_and_outdir_exits_two(capsys):
    """Missing --root and --out-dir -> exit 2 + status-error."""
    mod = load_module()
    rc = mod.main([])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_missing_root_exits_two(capsys):
    """Missing --root -> exit 2 + status-error."""
    mod = load_module()
    rc = mod.main(["--out-dir", "/tmp/no_such"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_missing_outdir_exits_two(capsys):
    """Missing --out-dir -> exit 2 + status-error."""
    mod = load_module()
    rc = mod.main(["--root", str(FIXTURES / "clean")])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_invalid_config_exits_two(tmp_path, capsys):
    """Invalid --config JSON -> exit 2 + status-error."""
    mod = load_module()
    cfg = tmp_path / "bad.json"
    cfg.write_text("{not valid json")
    rc = mod.main([
        "--root", str(FIXTURES / "clean"),
        "--out-dir", str(tmp_path / "out"),
        "--config", str(cfg),
    ])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_malformed_advisory_exits_two(tmp_path, capsys):
    """Malformed --advisory-report -> exit 2 + status-error."""
    mod = load_module()
    adv = tmp_path / "bad_adv.json"
    adv.write_text("{not valid json")
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(tmp_path / "out"),
        "--advisory-report", str(adv),
    ])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_missing_advisory_file_exits_two(tmp_path, capsys):
    """Non-existent --advisory-report -> exit 2 + status-error."""
    mod = load_module()
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(tmp_path / "out"),
        "--advisory-report", str(tmp_path / "no_such_file.json"),
    ])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"


def test_status_line_is_valid_json_on_success(tmp_path, capsys):
    """Stdout is valid JSON with expected keys on a successful run."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out)])
    assert rc == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    assert "findings" in payload
    assert payload["leaf"] == "dependency"


def test_report_md_is_written(tmp_path, capsys):
    """dependency_report.md is written to --out-dir."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    report = out / "dependency_report.md"
    assert report.exists(), "dependency_report.md should be written"
    content = report.read_text()
    assert "# dependency-audit report" in content


def test_format_flag_is_accepted(tmp_path, capsys):
    """--format json (default) and --format md are accepted."""
    mod = load_module()
    out = tmp_path / "out"
    # json format (default)
    rc = mod.main([
        "--root", str(FIXTURES / "clean"),
        "--out-dir", str(out),
        "--format", "json",
    ])
    assert rc == 0
    # md format
    out2 = tmp_path / "out2"
    rc = mod.main([
        "--root", str(FIXTURES / "clean"),
        "--out-dir", str(out2),
        "--format", "md",
    ])
    assert rc == 0
    # findings JSON should still be written regardless of format
    assert (out / "dependency_findings.json").exists()
    assert (out2 / "dependency_findings.json").exists()


def test_clean_run_writes_empty_findings_array(tmp_path, capsys):
    """Clean fixture writes [] to dependency_findings.json."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out)])
    assert rc == 0
    data = json.loads((out / "dependency_findings.json").read_text())
    assert data == []
