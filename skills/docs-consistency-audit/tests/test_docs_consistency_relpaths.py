"""Relative-path assertions for docs-consistency-audit findings.

All finding paths must be root-relative POSIX strings with no absolute paths.
"""

import json

from helpers import FIXTURES, load_module, read_findings


def test_findings_have_relative_posix_paths(tmp_path):
    """Every finding path is root-relative and uses POSIX separators."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    assert rc == 1
    data = read_findings(out)
    assert len(data) > 0
    for f in data:
        p = f["path"]
        assert not p.startswith("/"), f"absolute path: {p}"
        assert "\\" not in p, f"non-POSIX separator: {p}"
        assert not p.startswith(".."), f"parent reference: {p}"
