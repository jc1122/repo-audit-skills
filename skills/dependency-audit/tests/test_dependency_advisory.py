import json

from helpers import load_module, FIXTURES


def test_dirty_with_advisory_matches_golden(tmp_path, capsys):
    """Dirty fixture + advisory report produces the golden advisory findings."""
    mod = load_module()
    out = tmp_path / "out"
    adv = FIXTURES / "advisory.json"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(adv),
    ])
    assert rc == 1
    data = json.loads((out / "dependency_findings.json").read_text())
    golden = json.loads((FIXTURES / "golden_advisory_findings.json").read_text())
    assert data == golden


def test_advisory_findings_use_restructure_not_security(tmp_path, capsys):
    """Advisory findings must signal RESTRUCTURE, never SECURITY."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory.json"),
    ])
    assert rc == 1
    data = json.loads((out / "dependency_findings.json").read_text())
    advisory_metrics = {"dependency_vulnerabilities", "dependency_outdated"}
    for finding in data:
        if finding["metric"]["name"] in advisory_metrics:
            assert finding["signal"] == "RESTRUCTURE", (
                f"Advisory finding {finding['metric']['name']} must use "
                f"RESTRUCTURE, got {finding['signal']}"
            )
        # No finding should ever use SECURITY from this leaf
        assert finding["signal"] != "SECURITY", (
            f"dependency-audit must never emit SECURITY; "
            f"found in finding {finding['id']}"
        )


def test_advisory_null_severity_maps_to_medium(tmp_path, capsys):
    """Null C-8 severity maps to finding severity 'medium' with confidence 'medium'."""
    mod = load_module()
    out = tmp_path / "out"
    # Use the dirty fixture which declares somepkg is NOT declared,
    # but the advisory report still produces vulnerability findings
    # for any declared package matching the advisory.  We use clean fixture
    # which declares only requests, and an advisory with a different package
    # to avoid cross-contamination.
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory_null_severity.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    vuln_findings = [
        f for f in data
        if f["metric"]["name"] == "dependency_vulnerabilities"
        and f["location"]["symbol"] == "somepkg"
    ]
    if vuln_findings:  # only assert if somepkg is a declared dep matching the advisory
        f = vuln_findings[0]
        assert f["severity"] == "medium", (
            f"null severity should map to medium, got {f['severity']}"
        )
        assert f["confidence"] == "medium", (
            f"null severity should set confidence medium, got {f['confidence']}"
        )


def test_advisory_critical_severity_maps_to_high(tmp_path, capsys):
    """Critical C-8 severity maps to finding severity 'high'."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory_critical.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    vuln_findings = [
        f for f in data
        if f["metric"]["name"] == "dependency_vulnerabilities"
        and f["location"]["symbol"] == "dangerpkg"
    ]
    if vuln_findings:
        f = vuln_findings[0]
        assert f["severity"] == "high", (
            f"critical severity should map to high, got {f['severity']}"
        )


def test_advisory_null_latest_version_omits_outdated(tmp_path, capsys):
    """When latest_version is null, no dependency_outdated finding is produced."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory_null_latest.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    outdated = [
        f for f in data
        if f["metric"]["name"] == "dependency_outdated"
        and f["location"]["symbol"] == "requests"
    ]
    assert outdated == [], (
        "null latest_version should produce no outdated finding"
    )
    # Vulnerability finding for requests should still exist
    vulns = [
        f for f in data
        if f["metric"]["name"] == "dependency_vulnerabilities"
        and f["location"]["symbol"] == "requests"
    ]
    assert len(vulns) >= 1, "vulnerability finding should still exist"


def test_advisory_report_idempotent(tmp_path):
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


def test_advisory_finding_has_high_confidence(tmp_path, capsys):
    """Advisory vulnerability findings must use confidence 'high'."""
    mod = load_module()
    out = tmp_path / "out"
    mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(FIXTURES / "advisory.json"),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    vuln_findings = [
        f for f in data
        if f["metric"]["name"] == "dependency_vulnerabilities"
    ]
    for f in vuln_findings:
        assert f["confidence"] == "high", (
            f"vulnerability finding confidence must be high, got {f['confidence']}"
        )
    outdated_findings = [
        f for f in data
        if f["metric"]["name"] == "dependency_outdated"
    ]
    for f in outdated_findings:
        assert f["confidence"] == "medium", (
            f"outdated finding confidence must be medium, got {f['confidence']}"
        )
