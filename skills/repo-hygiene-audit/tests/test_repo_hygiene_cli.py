import json

from helpers import load_module, make_clean_repo, make_dirty_repo, read_findings, run_cli


def test_help_exits_zero():
    """Subprocess smoke: --help exits 0 and mentions --source-prefix."""
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--source-prefix" in result.stdout


def test_clean_exits_zero(tmp_path):
    """Clean repo produces exit 0 and [] findings."""
    repo = make_clean_repo(tmp_path)
    out = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 0
    assert read_findings(out) == []
    assert (out / "repo-hygiene_report.md").exists()


def test_dirty_exits_one_with_config(tmp_path):
    """Dirty repo with max_tracked_file_bytes=1024 produces exit 1 with
    the exact expected metric-name set."""
    repo, symlink_ok = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"max_tracked_file_bytes": 1024}')
    mod = load_module()
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)]
    )
    assert rc == 1
    data = read_findings(out)
    assert (out / "repo-hygiene_report.md").exists()

    metric_names = {f["metric"]["name"] for f in data}
    expected = {
        "tracked_artifact",
        "tracked_ignored",
        "tracked_file_bytes",
        "conflicting_configs",
        "version_mismatch",
        "ci_missing",
        "license_missing",
    }
    if symlink_ok:
        expected.add("broken_symlink")
    assert metric_names == expected, f"unexpected metric names: {metric_names ^ expected}"


def test_missing_required_args_returns_error(tmp_path, capsys):
    """Missing --root and --out-dir returns exit 2 and status-error JSON."""
    mod = load_module()
    rc = mod.main([])
    assert rc == 2
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert "required" in payload["message"].lower() or "--root" in payload["message"]


def test_missing_out_dir_returns_error(tmp_path, capsys):
    """Missing --out-dir returns exit 2 and status-error JSON."""
    repo, _ = make_dirty_repo(tmp_path)
    mod = load_module()
    rc = mod.main(["--root", str(repo)])
    assert rc == 2
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["status"] == "error"


def test_invalid_config_exits_two(tmp_path):
    """Invalid JSON config returns exit 2."""
    repo, _ = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    mod = load_module()
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--config", str(bad)]
    )
    assert rc == 2


def test_non_git_root_degrades(tmp_path, capsys):
    """Plain dir with release problems: status JSON includes 'git': false,
    release/config findings still appear, and git ls-files findings do not."""
    # Create a plain dir (no git) with pyproject version and no LICENSE/.github
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "pyproject.toml").write_text(
        '[project]\nversion = "2.0.0"\n\n[tool.pytest.ini_options]\n'
    )
    (plain / "CHANGELOG.md").write_text("## 1.0.0\n\nOld.\n")
    (plain / "pytest.ini").write_text("[pytest]\n")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(plain), "--out-dir", str(out)])
    # Non-git root still runs release/config checks; can exit 0 or 1
    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)
    assert payload.get("git") is False

    findings_file = out / "repo-hygiene_findings.json"
    assert findings_file.exists(), "expected findings file on non-git root with problems"
    data = json.loads(findings_file.read_text())

    # Release/config findings MUST still appear
    metric_names = {f["metric"]["name"] for f in data}
    assert "conflicting_configs" in metric_names, (
        "missing conflicting_configs finding on non-git root"
    )
    assert "version_mismatch" in metric_names, (
        "missing version_mismatch finding on non-git root"
    )
    assert "ci_missing" in metric_names, (
        "missing ci_missing finding on non-git root"
    )
    assert "license_missing" in metric_names, (
        "missing license_missing finding on non-git root"
    )

    # git ls-files findings MUST be absent
    git_signals = {"tracked_artifact", "tracked_ignored", "tracked_file_bytes", "broken_symlink"}
    for f in data:
        assert f["metric"]["name"] not in git_signals, (
            f"unexpected git-based finding on non-git root: {f}"
        )


def test_git_missing_exits_two(tmp_path, capsys, monkeypatch):
    """When git binary is missing, exit 2 with status-error containing 'git'."""
    mod = load_module()

    def _mock_run(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(mod, "_git", _mock_run)

    repo, _ = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 2
    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)
    assert payload["status"] == "error"
    assert "git" in payload["message"].lower()
