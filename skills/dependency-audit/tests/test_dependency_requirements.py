import json

from helpers import load_module, FIXTURES


def test_requirements_txt_is_recognized_as_manifest(tmp_path, capsys):
    """requirements.txt is recognized as a dependency manifest."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "reqs"),
        "--out-dir", str(out),
    ])
    # Should have findings (not exit 0 = no-manifest)
    assert rc == 1, (
        f"Expected exit 1 (findings present), got {rc}"
    )
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    # When manifest exists, "manifest" key should be absent
    # (or if present, it should not be False)
    manifest_val = payload.get("manifest")
    assert manifest_val is not False, (
        f"requirements.txt should be detected as manifest, "
        f"got manifest={manifest_val!r}"
    )
    assert payload["status"] == "ok"
    assert payload["leaf"] == "dependency"


def test_requirements_txt_finds_undeclared_import(tmp_path, capsys):
    """requirements.txt manifest: imported yaml (not in reqs) is undeclared."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "reqs"),
        "--out-dir", str(out),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    undeclared = [
        f for f in data
        if f["metric"]["name"] == "import_undeclared"
    ]
    symbols = {f["location"]["symbol"] for f in undeclared}
    assert "yaml" in symbols, (
        f"yaml is imported but not in requirements.txt; "
        f"should be undeclared. Got symbols: {symbols}"
    )


def test_requirements_txt_finds_unused_declared(tmp_path, capsys):
    """requirements.txt manifest: left-pad-py is declared but unused."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "reqs"),
        "--out-dir", str(out),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    unused = [
        f for f in data
        if f["metric"]["name"] == "declared_unused"
    ]
    symbols = {f["location"]["symbol"] for f in unused}
    assert "left-pad-py" in symbols, (
        f"left-pad-py is in requirements.txt but not imported; "
        f"should be unused. Got symbols: {symbols}"
    )


def test_requirements_txt_findings_have_correct_signal(tmp_path, capsys):
    """requirements.txt findings use correct signals: DELETE for unused, RESTRUCTURE for undeclared."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "reqs"),
        "--out-dir", str(out),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    for finding in data:
        if finding["metric"]["name"] == "declared_unused":
            assert finding["signal"] == "DELETE", (
                f"declared_unused must signal DELETE, got {finding['signal']}"
            )
        elif finding["metric"]["name"] == "import_undeclared":
            assert finding["signal"] == "RESTRUCTURE", (
                f"import_undeclared must signal RESTRUCTURE, got {finding['signal']}"
            )
        # No manifest findings should use SECURITY
        assert finding["signal"] != "SECURITY", (
            "dependency-audit must never emit SECURITY"
        )


def test_requirements_txt_idempotent(tmp_path):
    """Two requirements.txt runs produce byte-identical findings."""
    mod = load_module()
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    mod.main(["--root", str(FIXTURES / "reqs"), "--out-dir", str(out1)])
    mod.main(["--root", str(FIXTURES / "reqs"), "--out-dir", str(out2)])
    f1 = (out1 / "dependency_findings.json").read_bytes()
    f2 = (out2 / "dependency_findings.json").read_bytes()
    assert f1 == f2, (
        "requirements.txt findings should be byte-identical across runs"
    )


def test_requirements_txt_with_advisory(tmp_path, capsys):
    """requirements.txt manifest combined with advisory report."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "reqs"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    # Should include advisory findings for requests
    vuln = [
        f for f in data
        if f["metric"]["name"] == "dependency_vulnerabilities"
        and f["location"]["symbol"] == "requests"
    ]
    assert len(vuln) >= 1, (
        "Advisory should produce vulnerability finding for requests"
    )
    # Advisory findings must use RESTRUCTURE
    for f in vuln:
        assert f["signal"] == "RESTRUCTURE", (
            f"Advisory finding must use RESTRUCTURE, got {f['signal']}"
        )
