"""Tiny module under test for the redundancy triage golden fixture."""


def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


def reverse_string(s: str) -> str:
    return s[::-1]


def is_even(n: int) -> bool:
    return n % 2 == 0


class Calculator:
    def __init__(self, initial: int = 0):
        self.value = initial

    def add(self, n: int) -> int:
        self.value += n
        return self.value

    def subtract(self, n: int) -> int:
        self.value -= n
        return self.value

    def reset(self) -> None:
        self.value = 0
