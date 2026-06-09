def tangled(a, b, c, d, e, f):
    total = 0
    for i in range(a):
        if i % 2 == 0:
            if b > 0:
                total += 1
            elif c > 0:
                total += 2
            else:
                total += 3
        elif i % 3 == 0:
            if d > 0:
                total += 4
            elif e > 0:
                total += 5
            else:
                total += 6
        else:
            if f > 0:
                total += 7
            else:
                total += 8
    while total > 100:
        total -= 10
        if total % 7 == 0:
            total -= 1
    return total
