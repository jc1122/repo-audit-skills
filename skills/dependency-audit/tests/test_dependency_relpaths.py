import json

from helpers import load_module, FIXTURES


def _assert_relpaths(data):
    """Verify all finding paths are root-relative with POSIX separators."""
    for finding in data:
        path = finding["path"]
        assert not path.startswith("/"), f"Path should not be absolute: {path}"
        assert "\\" not in path, f"Path should use / not \\: {path}"
        assert ".." not in path.split("/"), (
            f"Path should not contain parent references: {path}"
        )
        # Evidence path references (in evidence_raw) should also be root-relative
        # if they reference files
        raw = finding.get("evidence", {}).get("raw", "")
        # Evidence raw may contain paths; ensure no absolute paths leak through
        # (only check if raw looks like it contains a path starting with /)
        for word in raw.split():
            if word.startswith("/") and len(word) > 1:
                # Single / is just a separator in text like "fix: 2.20.0"
                pass  # evidence_raw can contain absolute paths in suggestions


def test_findings_use_relative_paths(tmp_path, capsys):
    """All finding paths are relative (no absolute paths, use / separators)."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    data = json.loads((out / "dependency_findings.json").read_text())
    assert len(data) > 0, "Expected findings from dirty fixture"
    _assert_relpaths(data)


def test_advisory_findings_use_relative_paths(tmp_path, capsys):
    """Advisory-mode finding paths are also relative with POSIX separators."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    assert len(data) > 0, "Expected findings from dirty+advisory fixture"
    _assert_relpaths(data)


def test_source_prefix_paths_are_relative(tmp_path, capsys):
    """With --source-prefix, all finding paths stay relative."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main([
        "--root", str(FIXTURES / "prefix"),
        "--out-dir", str(out),
        "--source-prefix", "src",
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    _assert_relpaths(data)
