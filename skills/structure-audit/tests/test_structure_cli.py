from helpers import FIXTURES, read_findings, run_cli


def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--source-prefix" in result.stdout


def test_clean_exits_zero(tmp_path):
    result = run_cli("--root", str(FIXTURES / "clean"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 0
    assert read_findings(tmp_path) == []


def test_dirty_exits_one_with_cycle(tmp_path):
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(tmp_path))
    assert result.returncode == 1
    data = read_findings(tmp_path)
    assert any(d["metric"]["name"] == "import_cycle_size" for d in data)
    assert (tmp_path / "structure_report.md").exists()


def test_output_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/", "--out-dir", str(b))
    assert (a / "structure_findings.json").read_bytes() == (b / "structure_findings.json").read_bytes()


def test_bad_config_exits_two(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    result = run_cli("--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                     "--out-dir", str(tmp_path), "--config", str(bad))
    assert result.returncode == 2
