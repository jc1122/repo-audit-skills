def used(value):
    return value + 1


def unused_branchy(value):
    if value > 0:
        value = value - 1
    if value > 10:
        value = value - 10
    return value
