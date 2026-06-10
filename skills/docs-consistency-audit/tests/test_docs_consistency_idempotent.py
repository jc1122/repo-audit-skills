"""Idempotence test for docs-consistency-audit.

Two runs on the same inputs must produce byte-identical findings JSON.
"""

from pathlib import Path

from helpers import FIXTURES, load_module


def test_byte_identical_across_runs(tmp_path):
    """Two runs → byte-identical docs-consistency_findings.json."""
    mod = load_module()
    a = tmp_path / "a"
    b = tmp_path / "b"
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(a)])
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(b)])
    assert (a / "docs-consistency_findings.json").read_bytes() == (
        b / "docs-consistency_findings.json"
    ).read_bytes()
