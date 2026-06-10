"""Test file #2 — DELIBERATELY REDUNDANT with test_math1.

Has near-duplicate add tests and identical multiply tests.
"""
from fixtures.my_math import add, multiply, reverse_string, is_even


# These are near-duplicates of test_math1 add tests
def test_add_pos():
    """Same test as test_add_positive but different name."""
    assert add(2, 3) == 5


def test_add_neg():
    """Same test as test_add_negative but different name."""
    assert add(-2, -3) == -5


def test_add_with_zero():
    """Same logic as test_add_zero but structured differently."""
    assert add(0, 5) == 5
    assert add(5, 0) == 5


# Identical to test_math1 multiply tests
def test_multiply_basic():
    assert multiply(3, 4) == 12


def test_multiply_zero():
    assert multiply(5, 0) == 0


# New unique tests
def test_is_even_true():
    assert is_even(4) is True


def test_is_even_false():
    assert is_even(5) is False


def test_reverse_hello():
    """Identical name to test_math1 version."""
    assert reverse_string("hello") == "olleh"
