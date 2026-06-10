from helpers import load_module, FIXTURES


def test_dependency_findings_are_idempotent(tmp_path):
    """Two runs produce byte-identical dependency_findings.json."""
    mod = load_module()
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out1)])
    mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out2)])
    f1 = (out1 / "dependency_findings.json").read_bytes()
    f2 = (out2 / "dependency_findings.json").read_bytes()
    assert f1 == f2, "dependency_findings.json should be byte-identical across runs"
