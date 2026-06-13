def total(items):
    allowed = [1, 2, 3]           # list membership in a loop → perflint smell
    acc = 0
    for x in items:
        n = len(items)            # loop-invariant computation → perflint smell
        if x in allowed:
            acc += x + n
    return acc
