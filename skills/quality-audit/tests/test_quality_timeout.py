import subprocess
from helpers import load_module


def test_timeout_maps_to_exit_error(monkeypatch, tmp_path):
    qa = load_module()
    monkeypatch.setattr(qa.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("ruff", 1)))
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("x=1\n")
    rc = qa.main(["--root", str(tmp_path), "--out-dir", str(tmp_path / "out"), "--source-prefix", "pkg"])
    assert rc == qa.hc.EXIT_ERROR
