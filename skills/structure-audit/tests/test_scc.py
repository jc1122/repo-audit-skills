import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "_scc.py"


def load_scc_module():
    spec = importlib.util.spec_from_file_location("_scc", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scc = load_scc_module()


def sorted_components(edges):
    return sorted(scc.strongly_connected_components(sorted(edges), edges))


def test_tarjan_returns_singleton_components_for_acyclic_graph():
    edges = {"a": ["b"], "b": ["c"], "c": [], "d": []}
    assert sorted_components(edges) == [["a"], ["b"], ["c"], ["d"]]


def test_tarjan_finds_three_node_cycle_with_tail():
    edges = {"a": ["b"], "b": ["c"], "c": ["a"], "d": ["c"], "e": []}
    assert sorted_components(edges) == [["a", "b", "c"], ["d"], ["e"]]


def test_tarjan_keeps_closed_successor_out_of_later_component():
    edges = {"a": ["b", "c"], "b": [], "c": ["b"]}
    assert sorted_components(edges) == [["a"], ["b"], ["c"]]


def test_tarjan_handles_self_loop_and_separate_cycle():
    edges = {"a": ["a"], "b": ["c"], "c": ["b"], "d": []}
    assert sorted_components(edges) == [["a"], ["b", "c"], ["d"]]
