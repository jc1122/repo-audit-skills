def total(items):
    allowed = [1, 2, 3]           # list membership in a loop → perflint smell
    acc = 0
    for x in items:
        n = len(items)            # W8201 loop-invariant: load-bearing — asserted-dropped by test_perf_smell_precision
        if x in allowed:
            acc += x + n
    return acc
