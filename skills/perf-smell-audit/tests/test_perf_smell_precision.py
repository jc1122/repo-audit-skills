"""Phase 3 C2: the leaf keeps only perflint's high-precision codes."""

from helpers import FIXTURES, load_module

ps = load_module()

KEEP = {"W8101", "W8102", "W8204", "W8301", "W8401", "W8402", "W8403"}
DROP = {"W8201", "W8202", "W8205", "R8203"}


def test_high_precision_set_keeps_concrete_drops_heuristics():
    assert KEEP <= ps._PERFLINT_HIGH_PRECISION
    assert ps._PERFLINT_HIGH_PRECISION.isdisjoint(DROP)
    # exactly the 7 keep codes, nothing else
    assert ps._PERFLINT_HIGH_PRECISION == KEEP


def test_dirty_fixture_drops_loop_invariant_keeps_container():
    # the dirty fixture triggers BOTH W8201 (loop-invariant, dropped) and
    # W8301 (use-tuple-over-list, kept).
    findings = ps.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"])
    codes = {f.metric_name for f in findings}
    assert "W8301" in codes          # kept high-precision code still detected
    assert "W8201" not in codes      # heuristic loop-invariant dropped
    assert "C0114" not in codes      # pylint-core noise never leaks through
