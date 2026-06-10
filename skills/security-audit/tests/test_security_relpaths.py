import importlib.util
import json

from helpers import FIXTURES, load_module, read_findings


def test_findings_paths_are_relative_posix(tmp_path):
    mod = load_module()
    out_dir = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out_dir)])
    assert rc == 1
    findings = read_findings(out_dir)
    assert findings
    for f in findings:
        assert not f["path"].startswith("/")
        assert "\\" not in f["path"]
        assert ".." not in f["path"].split("/")


def test_bandit_missing_exits_two(tmp_path, capsys, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(tmp_path / "o")])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert "bandit" in payload["message"]
