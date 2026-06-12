import importlib.util
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
STRUCTURE_AUDIT = SCRIPT_DIR / "structure_audit.py"


def load_module(name, path):
    sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sa = load_module("structure_audit", STRUCTURE_AUDIT)


def test_cycle_findings_include_multi_node_and_self_loop_cycles():
    module_file = {"a": "a.py", "b": "b.py", "c": "c.py"}
    edges = {"a": ["b"], "b": ["a"], "c": ["c"]}
    findings = sa._cycle_findings(module_file, edges, sorted(module_file))
    symbols = {f.symbol for f in findings}
    assert symbols == {"cycle:a|b", "cycle:c"}
    assert {f.metric_name for f in findings} == {"import_cycle_size"}


def test_fan_findings_report_outbound_and_inbound_threshold_breaches():
    module_file = {"hub": "hub.py", "a": "a.py", "b": "b.py"}
    edges = {"hub": ["a", "b"], "a": ["b"], "b": []}
    thresholds = {"max_fan_out": 1, "max_fan_in": 1}
    findings = sa._fan_findings(module_file, edges, sorted(module_file), thresholds)
    keyed = {(f.symbol, f.metric_name): f for f in findings}
    assert keyed[("hub", "fan_out")].metric_value == 2
    assert keyed[("b", "fan_in")].metric_value == 2


def test_layer_findings_report_only_lower_to_higher_imports():
    module_file = {"pkg.high": "high.py", "pkg.low": "low.py", "pkg.peer": "peer.py"}
    edges = {"pkg.high": ["pkg.low"], "pkg.low": ["pkg.high", "pkg.peer"], "pkg.peer": []}
    configured_layers = ["pkg.high", "pkg.low"]

    findings = sa._layer_findings(
        module_file, edges, sorted(module_file), configured_layers
    )

    assert [f.symbol for f in findings] == ["pkg.low->pkg.high"]
    assert findings[0].metric_name == "layer_violation"
