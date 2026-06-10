"""Dirty tests: internal imports, private calls, exact-eq, expected literals."""

# BAD: internal import patterns trigger white-box detection
#   "from src.core import" ends with .core before import -- matches default pattern
from src.core import engine as eng_mod
import src.core.engine  # matches "import ... .core" default pattern


def test_process_returns_aggregate():
    """Implementation-coupled: directly imports internal module."""
    engine = eng_mod.DataEngine([10.0, 20.0, 30.0])
    result = engine.process(scale=2.0)
    # BAD: exact equality assert on a value with expected/want/target/snapshot/golden
    want = {"aggregate": 40.0, "count": 3}
    assert result == want


def test_private_method_call():
    """Calling private methods directly."""
    engine = eng_mod.DataEngine([5.0, 15.0])
    # BAD: calling private _methods on the object under test
    normalized = engine._normalize_value(120.0)
    assert normalized == 100.0
    engine._compute_aggregate()


# BAD: expected literal pattern signals change-indicator tests
expected = (10, 20, 30)


def test_with_expected_literal():
    engine = eng_mod.DataEngine(list(expected))
    result = engine.process()
    # BAD: exact equality assert on expected
    assert result["count"] == expected[2]


def test_internal_helper_validation():
    """Tests internal helper which is an implementation detail."""
    engine = eng_mod.DataEngine([1.0])
    helper = eng_mod.InternalHelper(engine)
    # BAD: calling private _validate method
    assert helper._validate() is True


# BAD: no marks at all on any test function
