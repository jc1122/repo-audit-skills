from helpers import FIXTURES, load_module

dc = load_module()
DEFAULTS = dc.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = dc.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    assert findings == []


def test_dirty_fixture_flags_unused_function_via_vulture():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    names = {f.symbol for f in findings if f.evidence_tool == "vulture"}
    assert "never_called" in names
    assert all(f.signal == "DELETE" for f in findings)


def test_dirty_fixture_flags_unused_import_and_local_via_ruff():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    codes = {f.metric_name for f in findings if f.evidence_tool == "ruff"}
    assert "F401" in codes  # unused import os
    assert "F841" in codes  # unused_local


def test_vulture_does_not_report_imports_or_variables():
    findings = dc.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS, allowlist=None)
    vulture_kinds = {f.metric_name for f in findings if f.evidence_tool == "vulture"}
    assert vulture_kinds <= {"dead_code_confidence"}
    # the unused import is owned by ruff (F401), never duplicated by vulture
    vulture_symbols = {f.symbol for f in findings if f.evidence_tool == "vulture"}
    assert "os" not in vulture_symbols
