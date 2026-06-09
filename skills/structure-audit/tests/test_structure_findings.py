from helpers import FIXTURES, load_module

sa = load_module()
DEFAULTS = sa.DEFAULT_THRESHOLDS


def test_clean_fixture_yields_no_findings():
    findings = sa.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    assert findings == []


def test_dirty_fixture_detects_import_cycle():
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=DEFAULTS)
    cycles = [f for f in findings if f.metric_name == "import_cycle_size"]
    assert cycles, "expected an import cycle finding"
    assert cycles[0].signal == "RESTRUCTURE"
    assert cycles[0].severity == "high"
    assert "pkg.a" in cycles[0].symbol and "pkg.b" in cycles[0].symbol


def test_fan_out_is_flagged_with_low_threshold():
    thresholds = dict(DEFAULTS, max_fan_out=1)
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=thresholds)
    fan = [f for f in findings if f.metric_name == "fan_out" and f.symbol == "pkg.hub"]
    assert fan and fan[0].metric_value == 2


def test_tarjan_finds_two_node_scc():
    edges = {"x": ["y"], "y": ["x"], "z": []}
    sccs = sa._strongly_connected_components(sorted(edges), edges)
    multi = [c for c in sccs if len(c) > 1]
    assert multi == [["x", "y"]]


def test_layers_violation_detected():
    # pkg.b (treated as "low") imports pkg.a (treated as "high") -> violation
    thresholds = dict(DEFAULTS, layers=["pkg.a", "pkg.b"])
    findings = sa.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"], thresholds=thresholds)
    violations = [f for f in findings if f.metric_name == "layer_violation"]
    assert any("pkg.b" in v.symbol and "pkg.a" in v.symbol for v in violations)
