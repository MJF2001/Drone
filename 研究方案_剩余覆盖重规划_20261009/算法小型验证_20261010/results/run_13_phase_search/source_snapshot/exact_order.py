"""Exact fixed-visit ordering oracle, not an area-coverage optimum."""
from array import array
from model import DeadlineExceeded


def held_karp(start, between, end, check_time=lambda: None, empty_cost=0):
    n = len(start)
    if n > 14:
        raise ValueError('oracle limited to fourteen complete visit instances')
    if len(end) != n or len(between) != n or any(len(row) != n for row in between):
        raise ValueError('matrix dimensions')
    if n == 0:
        check_time()
        return [], empty_cost
    inf = 10**15
    size = (1 << n)*n
    values = array('q', [inf])*size
    parents = array('b', [-1])*size
    for j in range(n):
        values[(1 << j)*n+j] = start[j]
    full = (1 << n)-1
    for mask in range(1, full+1):
        check_time()
        members = mask
        while members:
            bit = members & -members
            j = bit.bit_length()-1
            members ^= bit
            cost = values[mask*n+j]
            if cost == inf:
                continue
            rest = full ^ mask
            while rest:
                bit_k = rest & -rest
                k = bit_k.bit_length()-1
                rest ^= bit_k
                index = (mask | bit_k)*n+k
                trial = cost+between[j][k]
                if trial < values[index]:
                    values[index] = trial
                    parents[index] = j
    check_time()
    last = min(range(n), key=lambda j: (values[full*n+j]+end[j], j))
    optimum = values[full*n+last]+end[last]
    mask, order = full, []
    while last >= 0:
        order.append(last)
        previous = parents[mask*n+last]
        mask ^= 1 << last
        last = previous
    order.reverse()
    return order, optimum
