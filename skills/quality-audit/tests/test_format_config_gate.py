import json

from helpers import load_module, read_findings


def _write_drifted_fixture(tmp_path, config_name=None, config_text=""):
    root = tmp_path / "repo"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "dirty.py").write_text('value={"a":1}\n', encoding="utf-8")
    if config_name:
        (root / config_name).write_text(config_text, encoding="utf-8")
    return root


def _run_main(mod, capsys, root, out_dir):
    rc = mod.main(
        [
            "--root",
            str(root),
            "--source-prefix",
            "pkg/",
            "--out-dir",
            str(out_dir),
        ]
    )
    stdout = capsys.readouterr().out
    return rc, json.loads(stdout)


def _format_findings(out_dir):
    return [
        finding
        for finding in read_findings(out_dir)
        if finding["signal"] == "FORMAT" or finding["metric_name"] == "format_drift"
    ]


def test_no_format_config_suppresses_format_drift(tmp_path, capsys):
    mod = load_module()
    root = _write_drifted_fixture(tmp_path)
    out_dir = tmp_path / "out"

    _rc, payload = _run_main(mod, capsys, root, out_dir)

    assert _format_findings(out_dir) == []
    assert payload["format_check"] == "skipped (no declared standard)"
    assert payload["suppressed_format_files"] > 0


def test_pyproject_ruff_config_enables_format_drift(tmp_path, capsys):
    mod = load_module()
    root = _write_drifted_fixture(
        tmp_path, "pyproject.toml", "[tool.ruff]\nline-length = 88\n"
    )
    out_dir = tmp_path / "out"

    _rc, payload = _run_main(mod, capsys, root, out_dir)

    assert _format_findings(out_dir)
    assert payload["format_check"] == "checked"
    assert payload["suppressed_format_files"] == 0


def test_ruff_toml_config_enables_format_drift(tmp_path, capsys):
    mod = load_module()
    root = _write_drifted_fixture(tmp_path, ".ruff.toml", "line-length = 88\n")
    out_dir = tmp_path / "out"

    _rc, payload = _run_main(mod, capsys, root, out_dir)

    assert _format_findings(out_dir)
    assert payload["format_check"] == "checked"
    assert payload["suppressed_format_files"] == 0
