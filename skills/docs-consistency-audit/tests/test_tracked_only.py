"""Regression tests for tracked-path doc reference resolution."""

import json
import shutil
import subprocess

from helpers import load_module, read_findings


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def _commit(root, *paths):
    _git(root, "add", *paths)
    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=a@b.test",
            "-c",
            "user.name=Tester",
            "commit",
            "-m",
            "fixture",
        ],
        text=True,
        capture_output=True,
        check=True,
    )


def _run(root, out, capsys, *extra_args):
    mod = load_module()
    rc = mod.main(["--root", str(root), "--out-dir", str(out), *extra_args])
    status = json.loads(capsys.readouterr().out)
    findings = read_findings(out)
    return rc, status, findings


def _path_findings(findings):
    return [f for f in findings if f["metric"]["name"] == "doc_path_missing"]


def test_default_git_mode_reports_untracked_present_path_missing(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "README.md").write_text("See `docs/untracked.md`.\n")
    (root / "docs" / "untracked.md").write_text("present but untracked\n")
    _git(root, "init")
    _commit(root, "README.md")

    out = tmp_path / "out"
    _, status, findings = _run(root, out, capsys)

    paths = _path_findings(findings)
    assert status["path_resolution"] == "tracked"
    assert "path_resolution: tracked" in (
        out / "docs-consistency_report.md"
    ).read_text()
    assert len(paths) == 1
    assert paths[0]["location"]["symbol"] == "docs/untracked.md"


def test_filesystem_paths_opt_out_resolves_untracked_present_path(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "README.md").write_text("See `docs/untracked.md`.\n")
    (root / "docs" / "untracked.md").write_text("present but untracked\n")
    _git(root, "init")
    _commit(root, "README.md")

    out = tmp_path / "out"
    _, status, findings = _run(root, out, capsys, "--filesystem-paths")

    assert status["path_resolution"] == "filesystem"
    assert _path_findings(findings) == []


def test_tracked_file_reference_resolves_in_both_modes(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "README.md").write_text("See `docs/tracked.md`.\n")
    (root / "docs" / "tracked.md").write_text("tracked\n")
    _git(root, "init")
    _commit(root, "README.md", "docs/tracked.md")

    default_out = tmp_path / "default-out"
    _, default_status, default_findings = _run(root, default_out, capsys)
    fs_out = tmp_path / "fs-out"
    _, fs_status, fs_findings = _run(root, fs_out, capsys, "--filesystem-paths")

    assert default_status["path_resolution"] == "tracked"
    assert fs_status["path_resolution"] == "filesystem"
    assert _path_findings(default_findings) == []
    assert _path_findings(fs_findings) == []


def test_tracked_directory_prefix_resolves_to_tracked_child(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pkg").mkdir()
    (root / "README.md").write_text("Package: `pkg/`.\n")
    (root / "pkg" / "x.py").write_text("VALUE = 1\n")
    _git(root, "init")
    _commit(root, "README.md", "pkg/x.py")
    shutil.rmtree(root / "pkg")

    default_out = tmp_path / "default-out"
    _, default_status, default_findings = _run(root, default_out, capsys)
    fs_out = tmp_path / "fs-out"
    _, fs_status, fs_findings = _run(root, fs_out, capsys, "--filesystem-paths")

    assert default_status["path_resolution"] == "tracked"
    assert fs_status["path_resolution"] == "filesystem"
    assert _path_findings(default_findings) == []
    fs_paths = _path_findings(fs_findings)
    assert len(fs_paths) == 1
    assert fs_paths[0]["location"]["symbol"] == "pkg/"


def test_non_git_root_falls_back_to_filesystem_paths(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "README.md").write_text("See `docs/present.md`.\n")
    (root / "docs" / "present.md").write_text("present\n")

    out = tmp_path / "out"
    _, status, findings = _run(root, out, capsys)

    assert status["path_resolution"] == "filesystem"
    assert "path_resolution: filesystem" in (
        out / "docs-consistency_report.md"
    ).read_text()
    assert _path_findings(findings) == []
