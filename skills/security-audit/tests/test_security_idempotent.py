from helpers import FIXTURES, load_module


def test_two_runs_byte_identical(tmp_path):
    mod = load_module()
    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    assert mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out1)]) == 1
    assert mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out2)]) == 1
    b1 = (out1 / "security_findings.json").read_bytes()
    b2 = (out2 / "security_findings.json").read_bytes()
    assert b1 == b2
