"""Test file #3 — calculator class tests.

Some overlap with unique tests and some purely unique.
"""
from fixtures.my_math import Calculator, is_even, reverse_string


def test_calc_add():
    c = Calculator(10)
    assert c.add(5) == 15


def test_calc_subtract():
    c = Calculator(10)
    assert c.subtract(3) == 7


def test_calc_chain():
    c = Calculator(10)
    c.add(5)
    c.subtract(3)
    assert c.value == 12


def test_calc_reset():
    c = Calculator(100)
    c.add(50)
    c.reset()
    assert c.value == 0


# Duplicate is_even tests from test_math2
def test_is_even_true():
    assert is_even(4) is True


def test_is_even_false():
    assert is_even(5) is False


# Unique test
def test_reverse_long():
    assert reverse_string("abcdef") == "fedcba"
