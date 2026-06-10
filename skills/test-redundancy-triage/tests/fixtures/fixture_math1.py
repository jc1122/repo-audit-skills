"""Test file #1 — has redundant add tests and overlap with test_math2."""
from fixtures.my_math import add, multiply, reverse_string


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-2, -3) == -5


def test_add_zero():
    assert add(0, 5) == 5
    assert add(5, 0) == 5


def test_add_large():
    assert add(1000, 2000) == 3000


def test_multiply_basic():
    assert multiply(3, 4) == 12


def test_multiply_zero():
    assert multiply(5, 0) == 0


def test_reverse_hello():
    assert reverse_string("hello") == "olleh"


def test_reverse_empty():
    assert reverse_string("") == ""
