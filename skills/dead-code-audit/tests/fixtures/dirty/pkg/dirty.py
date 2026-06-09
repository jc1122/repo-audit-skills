import os


def public_entry():
    return _helper()


def _helper():
    return 1


def never_called():
    return 99


def leaky():
    unused_local = 123
    return 5
