from helpers import FIXTURES, load_module

da = load_module()
DEFAULTS = da.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = da.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_flags_cross_file_extract():
    findings = da.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings, "expected at least one duplication finding"
    assert any(f.signal == "EXTRACT" for f in findings)
    f = next(f for f in findings if f.signal == "EXTRACT")
    assert f.metric_name == "duplicate_tokens"
    assert f.metric_value >= DEFAULTS["min_tokens"]
    assert f.confidence == "high"
    assert {f.path, f.symbol.split(":")[0]} == {"pkg/a.py", "pkg/b.py"}
