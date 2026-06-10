"""Simple public calculator module."""


class Calculator:
    def __init__(self, value: float = 0):
        self.value = value

    def add(self, x: float) -> float:
        self.value += x
        return self.value

    def subtract(self, x: float) -> float:
        self.value -= x
        return self.value


def add(a: float, b: float) -> float:
    return a + b


def compute_ratio(a: float, b: float) -> float:
    """Compute ratio with zero-division guard."""
    if b == 0:
        raise ValueError("b must not be zero")
    return a / b
