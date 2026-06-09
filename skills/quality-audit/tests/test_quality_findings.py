from helpers import FIXTURES, load_module

qa = load_module()
DEFAULTS = qa.DEFAULT_CONFIG


def test_clean_fixture_yields_no_findings():
    findings = qa.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], config=DEFAULTS)
    assert findings == []


def test_dirty_fixture_emits_lint_format_and_type():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    signals = {f.signal for f in findings}
    assert "LINT" in signals
    assert "FORMAT" in signals
    assert "TYPE" in signals


def test_owned_codes_are_never_reported():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    codes = {f.metric_name for f in findings if f.signal == "LINT"}
    assert codes.isdisjoint({"F401", "F811", "F841", "C901"})


def test_type_findings_are_high_severity():
    findings = qa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], config=DEFAULTS)
    type_findings = [f for f in findings if f.signal == "TYPE"]
    assert type_findings and all(f.severity == "high" for f in type_findings)
