"""More dirty tests with additional signals."""

# Another internal import -- matches default pattern (ends with .internal before import)
from src.core.internal import helper as internal_helper  # type: ignore[import-untyped]
import src.core.engine  # matches default import pattern


# BAD: another expected literal
expected = (100, 200, 300)


def test_another_expected_literal():
    engine = __import__("src").core.engine.DataEngine(list(expected))
    snapshot = engine.process()
    # BAD: exact equality assert on snapshot
    assert snapshot["count"] == expected[2]


# BAD: broad exception tuple in pytest.raises
def test_broad_raises():
    engine = __import__("src").core.engine.DataEngine([10.0])
    with __import__("pytest").raises((ValueError, TypeError)):
        engine.process()


# BAD: pytest.raises without match=
def test_raises_no_match():
    engine = __import__("src").core.engine.DataEngine([])
    with __import__("pytest").raises(ValueError):
        engine.process()


# BAD: calling private method
def test_private_cache_access():
    engine = __import__("src").core.engine.DataEngine([5.0])
    # BAD: accessing private attribute
    cached = engine._cache.get("last")  # This will be caught as private method call
    assert cached is None
