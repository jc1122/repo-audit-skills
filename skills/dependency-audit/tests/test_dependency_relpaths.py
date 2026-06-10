import json

from helpers import load_module, FIXTURES


def test_findings_use_relative_paths(tmp_path, capsys):
    """All finding paths are relative (no absolute paths, use / separators)."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    data = json.loads((out / "dependency_findings.json").read_text())
    for finding in data:
        path = finding["path"]
        assert not path.startswith("/"), f"Path should not be absolute: {path}"
        assert "\\" not in path, f"Path should use / not \\: {path}"
