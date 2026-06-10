"""Clean tests: public API, pytest marks, no internal imports."""

import pytest

from src.calculator import Calculator, add, compute_ratio


@pytest.mark.smoke
@pytest.mark.unit
def test_add_positive():
    """Behavior-focused: verify add returns correct sum."""
    result = add(2, 3)
    assert result == 5


@pytest.mark.unit
def test_add_negative():
    result = add(-1, -1)
    assert result == -2


@pytest.mark.smoke
def test_compute_ratio_happy_path():
    result = compute_ratio(10, 2)
    assert result == 5.0


def test_compute_ratio_zero_denominator():
    with pytest.raises(ValueError, match="must not be zero"):
        compute_ratio(10, 0)


@pytest.mark.smoke
def test_calculator_add():
    calc = Calculator(10)
    result = calc.add(5)
    assert result == 15


def test_calculator_subtract():
    calc = Calculator(20)
    result = calc.subtract(5)
    assert result == 15
