from pathlib import Path

from helpers import FIXTURES, load_module

ca = load_module()
DEFAULTS = ca.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = ca.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_flags_high_complexity_and_params():
    findings = ca.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    signals = sorted({f.signal for f in findings})
    assert "DECOMPOSE" in signals  # high cyclomatic complexity
    assert "SIMPLIFY" in signals   # too many parameters
    cc = [f for f in findings if f.metric_name == "cyclomatic_complexity"]
    assert cc and cc[0].metric_value > 10
    assert cc[0].symbol == "tangled"
    assert cc[0].confidence == "high"


def test_thresholds_are_configurable():
    relaxed = dict(DEFAULTS, cc_medium=999, cc_high=999, max_params=999, nloc_medium=9999)
    findings = ca.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=relaxed)
    # Only the maintainability-index check could still fire; complexity/params suppressed.
    assert all(f.metric_name != "cyclomatic_complexity" for f in findings)
