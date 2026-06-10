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


def test_advisory_findings_are_idempotent(tmp_path):
    """Two advisory runs produce byte-identical dependency_findings.json."""
    mod = load_module()
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    adv = FIXTURES / "advisory.json"
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out1),
        "--advisory-report", str(adv),
    ])
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out2),
        "--advisory-report", str(adv),
    ])
    f1 = (out1 / "dependency_findings.json").read_bytes()
    f2 = (out2 / "dependency_findings.json").read_bytes()
    assert f1 == f2, (
        "dependency_findings.json should be byte-identical across advisory runs"
    )


def test_clean_findings_are_idempotent(tmp_path):
    """Two clean runs produce byte-identical (empty) dependency_findings.json."""
    mod = load_module()
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out1)])
    mod.main(["--root", str(FIXTURES / "clean"), "--out-dir", str(out2)])
    f1 = (out1 / "dependency_findings.json").read_bytes()
    f2 = (out2 / "dependency_findings.json").read_bytes()
    assert f1 == f2, (
        "empty findings should be byte-identical across runs"
    )


def test_no_manifest_idempotent(tmp_path):
    """Two no-manifest runs produce byte-identical (empty) dependency_findings.json."""
    mod = load_module()
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    mod.main(["--root", str(FIXTURES / "no_manifest"), "--out-dir", str(out1)])
    mod.main(["--root", str(FIXTURES / "no_manifest"), "--out-dir", str(out2)])
    f1 = (out1 / "dependency_findings.json").read_bytes()
    f2 = (out2 / "dependency_findings.json").read_bytes()
    assert f1 == f2, (
        "no-manifest findings should be byte-identical across runs"
    )
