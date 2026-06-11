import json
from pathlib import Path
from types import SimpleNamespace

from helpers import load_module, read_findings


def _write_py(path: Path, has_entrypoint: bool) -> None:
    content = [
        "def helper():",
        "    return 42",
        "",
    ]
    if has_entrypoint:
        content.extend(["", "if __name__ == '__main__':", "    print(helper())", ""])
    path.write_text("\n".join(content), encoding="utf-8")


def _fake_radon_mi_run(mi: float, path: Path):
    payload = {
        str(path.resolve()): {
            "mi": mi,
            "rank": "B",
        }
    }

    def _fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    return _fake_run


def test_entrypoint_mi_between_floor_and_threshold_is_suppressed(
    tmp_path, capsys, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    module = repo / "entrypoint.py"
    _write_py(module, has_entrypoint=True)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"mi_low": 65}), encoding="utf-8")
    mod = load_module()
    monkeypatch.setattr(mod, "_lizard_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(mod.subprocess, "run", _fake_radon_mi_run(30.0, module))

    rc = mod.main(
        [
            "--root",
            str(repo),
            "--source-prefix",
            "entrypoint.py",
            "--out-dir",
            str(tmp_path / "out"),
            "--config",
            str(config),
        ]
    )

    status = json.loads(capsys.readouterr().out)
    data = read_findings(tmp_path / "out")
    assert rc == 0
    assert status["entrypoint_mi_relaxed"] == 1
    assert status["findings"] == 0
    assert data == []
    assert "entrypoint_mi_relaxed: 1" in (tmp_path / "out" / "complexity_report.md").read_text(
        encoding="utf-8"
    )


def test_entrypoint_mi_below_floor_is_not_suppressed(tmp_path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    module = repo / "entrypoint.py"
    _write_py(module, has_entrypoint=True)
    mod = load_module()
    monkeypatch.setattr(mod, "_lizard_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(mod.subprocess, "run", _fake_radon_mi_run(10.0, module))

    rc = mod.main(
        [
            "--root",
            str(repo),
            "--source-prefix",
            "entrypoint.py",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    status = json.loads(capsys.readouterr().out)
    data = read_findings(tmp_path / "out")
    assert rc == 1
    assert status["entrypoint_mi_relaxed"] == 0
    assert status["findings"] == 1
    assert any(item["metric"]["name"] == "maintainability_index" for item in data)


def test_non_entrypoint_module_not_eligible_for_relaxation(tmp_path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    module = repo / "library.py"
    _write_py(module, has_entrypoint=False)
    mod = load_module()
    monkeypatch.setattr(mod, "_lizard_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(mod.subprocess, "run", _fake_radon_mi_run(30.0, module))

    rc = mod.main(
        [
            "--root",
            str(repo),
            "--source-prefix",
            "library.py",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    status = json.loads(capsys.readouterr().out)
    data = read_findings(tmp_path / "out")
    assert rc == 1
    assert status["entrypoint_mi_relaxed"] == 0
    assert any(item["metric"]["name"] == "maintainability_index" for item in data)


def test_none_entrypoint_floor_disables_relaxation(tmp_path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    module = repo / "entrypoint.py"
    _write_py(module, has_entrypoint=True)
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps({"mi_entrypoint_low": None, "mi_low": 65}), encoding="utf-8"
    )
    mod = load_module()
    monkeypatch.setattr(mod, "_lizard_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(mod.subprocess, "run", _fake_radon_mi_run(30.0, module))

    rc = mod.main(
        [
            "--root",
            str(repo),
            "--source-prefix",
            "entrypoint.py",
            "--out-dir",
            str(tmp_path / "out"),
            "--config",
            str(config),
        ]
    )

    status = json.loads(capsys.readouterr().out)
    data = read_findings(tmp_path / "out")
    assert rc == 1
    assert status["entrypoint_mi_relaxed"] == 0
    assert any(item["metric"]["name"] == "maintainability_index" for item in data)
