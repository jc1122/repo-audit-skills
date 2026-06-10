"""Idempotence tests: two runs produce byte-identical JSON output."""

from helpers import FIXTURES, run_cli


def test_byte_identical_across_runs(tmp_path):
    """Two runs over the same fixture produce byte-identical JSON."""
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    run_cli("--root", str(FIXTURES / "dirty"), "--json-out", str(a))
    run_cli("--root", str(FIXTURES / "dirty"), "--json-out", str(b))
    assert a.read_bytes() == b.read_bytes()


def test_byte_identical_clean(tmp_path):
    """Two runs over clean fixture produce byte-identical JSON."""
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    run_cli("--root", str(FIXTURES / "clean"), "--json-out", str(a))
    run_cli("--root", str(FIXTURES / "clean"), "--json-out", str(b))
    assert a.read_bytes() == b.read_bytes()
