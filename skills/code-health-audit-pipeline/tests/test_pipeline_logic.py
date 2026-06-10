from helpers import finding, load_module

ch = load_module()


def test_merge_dedupes_by_path_line_metric():
    a = finding(leaf="quality")
    b = finding(leaf="dead-code")  # same path/line/metric → duplicate
    merged = ch.merge_and_dedupe([a, b])
    assert len(merged) == 1


def test_rank_orders_by_score_desc():
    cheap_high = finding(signal="DELETE", severity="high", confidence="high",
                         path="pkg/a.py", metric={"name": "m1", "value": 0, "threshold": 0})
    costly_low = finding(signal="RESTRUCTURE", severity="low", confidence="low",
                         path="pkg/b.py", metric={"name": "m2", "value": 0, "threshold": 0})
    ranked = ch.rank([costly_low, cheap_high])
    assert ranked[0]["signal"] == "DELETE"


def test_decide_pass_when_no_findings():
    decision, code = ch.decide([], {"complexity": 0}, ch.DEFAULT_GATE)
    assert (decision, code) == ("PASS", 0)


def test_decide_advise_when_findings_no_gate():
    f = finding(signal="LINT", severity="low", metric={"name": "E711", "value": 0, "threshold": 0})
    decision, code = ch.decide([f], {"quality": 1}, ch.DEFAULT_GATE)
    assert (decision, code) == ("ADVISE", 1)


def test_decide_gate_on_errored_leaf():
    decision, code = ch.decide([], {"quality": 2}, ch.DEFAULT_GATE)
    assert (decision, code) == ("GATE", 2)


def test_decide_gate_on_import_cycle():
    f = finding(signal="RESTRUCTURE", metric={"name": "import_cycle_size", "value": 2, "threshold": 1})
    decision, code = ch.decide([f], {"structure": 1}, ch.DEFAULT_GATE)
    assert (decision, code) == ("GATE", 2)


def test_test_signal_has_effort_weight():
    assert ch.EFFORT["TEST"] == 3
