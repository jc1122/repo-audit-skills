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
