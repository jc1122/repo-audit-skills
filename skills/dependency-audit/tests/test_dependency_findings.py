import json

from helpers import load_module, FIXTURES


def test_dirty_fixture_matches_golden(tmp_path, capsys):
    """Dirty fixture produces exactly the golden findings."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    assert rc == 1  # EXIT_FINDINGS
    data = json.loads((out / "dependency_findings.json").read_text())
    golden = json.loads((FIXTURES / "golden_findings.json").read_text())
    assert data == golden


def test_clean_fixture_returns_empty(tmp_path, capsys):
    """Clean fixture produces zero findings."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out)])
    assert rc == 0  # EXIT_CLEAN
    data = json.loads((out / "dependency_findings.json").read_text())
    assert data == []


def test_no_manifest_returns_zero_with_manifest_false(tmp_path, capsys):
    """No manifest -> exit 0, [] findings, stdout includes 'manifest': false."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "no_manifest"), "--out-dir", str(out)])
    assert rc == 0
    data = json.loads((out / "dependency_findings.json").read_text())
    assert data == []
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["manifest"] is False


def test_pyproject_without_project_table_is_no_manifest(tmp_path, capsys):
    """pyproject.toml without [project] is not a dependency manifest."""
    root = tmp_path / "root"
    (root / "src").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[tool.black]\nline-length = 88\n",
        encoding="utf-8",
    )
    (root / "src" / "app.py").write_text(
        "import requests\n",
        encoding="utf-8",
    )
    mod = load_module()
    out = tmp_path / "out"

    rc = mod.main(["--root", str(root), "--out-dir", str(out)])

    assert rc == 0
    data = json.loads((out / "dependency_findings.json").read_text())
    assert data == []
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["manifest"] is False
