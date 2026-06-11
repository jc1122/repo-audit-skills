import json

from helpers import FIXTURES, load_module, read_findings, run_cli


def test_help_exits_zero():
    proc = run_cli("--help")
    assert proc.returncode == 0


def test_missing_required_args(capsys):
    mod = load_module()
    rc = mod.main([])
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"


def test_missing_out_dir(tmp_path, capsys):
    mod = load_module()
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"


def test_clean_fixture_exit_zero(tmp_path, capsys):
    mod = load_module()
    out_dir = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out_dir)])
    assert rc == 0
    status = json.loads(capsys.readouterr().out)
    assert status == {"status": "ok", "findings": 0, "leaf": "security"}
    assert read_findings(out_dir) == []
