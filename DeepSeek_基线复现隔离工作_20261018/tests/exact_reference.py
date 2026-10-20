"""Exact reference for micro instances.

Independent of every planner: a uniform-cost search over the state
(position, mask of covered pending targets).  The mask counts only *pending*
targets at the start; the ledger ``C`` is folded into the initial mask.  All
states are four-neighbour steps, so the first time the goal state (base, full
mask) is popped the cost is the true optimum for "complete the remaining tasks
and return to the base".

This is deliberately exponential and must only be used on micro instances.
"""
import heapq
from collections import deque

STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def exact_optimum(request, max_states=4_000_000):
    pending = sorted(request.pending)
    index = {p: i for i, p in enumerate(pending)}
    full = (1 << len(pending)) - 1
    free = set(request.free)
    start = (tuple(request.current), 0)
    start_mask = 0
    for p, bit in index.items():
        if p == start[0]:
            start_mask |= 1 << bit
    start = (start[0], start_mask)
    base = tuple(request.base)

    frontier = deque([(start, 0)])
    seen = {start: 0}
    states = 0
    while frontier:
        (position, mask), cost = frontier.popleft()
        states += 1
        if states > max_states:
            return {"status": "state_limit", "limit": max_states, "states": states}
        if position == base and mask == full:
            return {"status": "optimal", "steps": cost, "states": states}
        for dx, dy in STEPS:
            nxt = (position[0] + dx, position[1] + dy)
            if nxt not in free:
                continue
            nmask = mask
            bit = index.get(nxt)
            if bit is not None:
                nmask = mask | (1 << bit)
            key = (nxt, nmask)
            if key not in seen:
                seen[key] = cost + 1
                frontier.append((key, cost + 1))
    return {"status": "infeasible", "states": states}


def exact_with_path(request, max_states=2_000_000):
    """Same search but keeping parents, for diagnosing a gap on a tiny instance."""
    pending = sorted(request.pending)
    index = {p: i for i, p in enumerate(pending)}
    full = (1 << len(pending)) - 1
    free = set(request.free)
    mask0 = 0
    for p, bit in index.items():
        if p == tuple(request.current):
            mask0 |= 1 << bit
    start = (tuple(request.current), mask0)
    base = tuple(request.base)
    frontier = deque([start])
    parent = {start: None}
    states = 0
    while frontier:
        state = frontier.popleft()
        states += 1
        if states > max_states:
            return {"status": "state_limit", "states": states}
        position, mask = state
        if position == base and mask == full:
            route = [position]
            node = state
            while parent[node] is not None:
                node = parent[node]
                route.append(node[0])
            route.reverse()
            return {"status": "optimal", "steps": len(route) - 1, "route": tuple(route),
                    "states": states}
        for dx, dy in STEPS:
            nxt = (position[0] + dx, position[1] + dy)
            if nxt not in free:
                continue
            nmask = mask
            bit = index.get(nxt)
            if bit is not None:
                nmask = mask | (1 << bit)
            node = (nxt, nmask)
            if node not in parent:
                parent[node] = state
                frontier.append(node)
    return {"status": "infeasible", "states": states}


def reach_lower_bound(request):
    """Valid but weak bound: the route must reach the farthest pending target.

    Used only to check that no reported cost is below a proven bound; it is not
    an optimum and must never be reported as one.
    """
    from common_geometry import GridMetric
    metric = GridMetric(request.free)
    current = tuple(request.current)
    pending = list(request.pending)
    if not pending:
        return metric.distance(current, tuple(request.base))
    return max(metric.distance(current, p) for p in pending)
