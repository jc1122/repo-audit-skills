from helpers import FIXTURES, load_module

cg = load_module()
DEFAULTS = cg.DEFAULT_THRESHOLDS


def _analyze(tree, *reports):
    return cg.analyze_tree(
        FIXTURES / tree,
        source_prefixes=["pkg/"],
        thresholds=DEFAULTS,
        coverage_jsons=[str(FIXTURES / tree / r) for r in reports],
    )


def test_fully_covered_tree_yields_no_findings():
    assert _analyze("covered", "coverage_full.json") == []


def test_untested_file_is_high_severity_zero_percent():
    findings = {f.path: f for f in _analyze("uncovered", "coverage_partial.json")}
    f = findings["pkg/uncovered.py"]
    assert f.signal == "TEST"
    assert f.severity == "high"
    assert f.confidence == "high"
    assert f.metric_name == "file_coverage_percent"
    assert f.metric_value == 0.0
    assert f.symbol == "<file>"


def test_partially_covered_file_is_medium_severity():
    findings = {f.path: f for f in _analyze("uncovered", "coverage_partial.json")}
    f = findings["pkg/partial.py"]
    assert f.severity == "medium"
    assert f.metric_value == 25.0
    assert f.metric_threshold == 50.0


def test_covered_file_is_not_flagged():
    findings = {f.path for f in _analyze("uncovered", "coverage_partial.json")}
    assert "pkg/covered.py" not in findings
    assert findings == {"pkg/partial.py", "pkg/uncovered.py"}


def test_multiple_reports_merge_by_union():
    findings = {
        f.path
        for f in _analyze("uncovered", "coverage_partial.json", "coverage_extra.json")
    }
    assert findings == {"pkg/uncovered.py"}  # partial.py reaches 8/8 after the union
