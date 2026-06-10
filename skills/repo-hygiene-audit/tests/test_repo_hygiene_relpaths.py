import json

from helpers import load_module, make_dirty_repo


def test_findings_use_root_relative_posix_paths(tmp_path):
    """All finding paths are root-relative POSIX (no absolute, no backslashes)."""
    repo = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"max_tracked_file_bytes": 1024}')

    mod = load_module()
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)]
    )
    assert rc == 1

    data = json.loads((out / "repo-hygiene_findings.json").read_text())
    assert len(data) > 0, "expected at least one finding"

    for f in data:
        path = f["path"]
        assert not path.startswith("/"), (
            f"absolute path (starts with /): {path!r}"
        )
        assert "\\" not in path, (
            f"backslash in path (not POSIX): {path!r}"
        )
        # Paths should use / as separator
        assert "/" in path or path == path.lower(), (
            f"path should use forward slashes: {path!r}"
        )
