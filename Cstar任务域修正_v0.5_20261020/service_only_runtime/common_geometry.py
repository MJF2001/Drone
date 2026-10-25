"""Common legal connector and grid metric for the newly adapted methods.

The frozen baselines keep their historical ``UnifiedGeometry`` connector so that
their behaviour is unchanged.  ``CSTAR`` and ``EPSILON_STAR`` were never part of
that suite, so they need a connector of their own; this module provides one with
the *same policy* (exact BFS distance, one canonical geometry per unordered
endpoint pair, four-neighbour steps only), implemented independently of the
frozen code so that a bug there cannot silently validate itself here.

``tests/test_connector_equivalence.py`` asserts equal distances and equal route
lengths against ``UnifiedGeometry`` on every micro fixture.
"""
from collections import deque

STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def neighbours(p):
    return ((p[0] + 1, p[1]), (p[0], p[1] + 1), (p[0] - 1, p[1]), (p[0], p[1] - 1))


class NoPath(Exception):
    pass


class GridMetric:
    """Four-neighbour exact metric with a canonical shortest-path geometry.

    ``path(a, b)`` always returns a tuple starting at ``a`` and ending at ``b``;
    ``path(b, a)`` is exactly its reverse, because the geometry is computed once
    for the ordered pair ``sorted((a, b))``.  That removes the historical
    "which endpoint was queried first" ambiguity.
    """

    def __init__(self, free, deadline=None, checkpoint=None):
        self.free = frozenset(free)
        self.deadline = deadline
        self._rows = {}
        self._paths = {}
        self.builds = 0
        self.checkpoint=checkpoint or (lambda stage:None)

    # -- helpers ---------------------------------------------------------
    def _tick(self, clock):
        if self.deadline is not None and clock() > self.deadline:
            raise TimeoutError("connector deadline")

    def _row(self, start):
        row = self._rows.get(start)
        if row is not None:
            return row
        row = {start: 0}
        parent = {start: None}
        queue = deque([start])
        free = self.free
        while queue:
            self.checkpoint('bfs_expand')
            p = queue.popleft()
            for q in neighbours(p):
                if q in free and q not in row:
                    row[q] = row[p] + 1
                    parent[q] = p
                    queue.append(q)
        self._rows[start] = row
        self._parents = getattr(self, "_parents", {})
        self._parents[start] = parent
        self.builds += 1
        return row

    def reachable(self, start):
        return set(self._row(start))

    def distance(self, a, b):
        if a == b:
            return 0
        if a not in self.free or b not in self.free:
            raise NoPath(f"endpoint_not_free: {a if a not in self.free else b}")
        row = self._row(a)
        if b not in row:
            raise NoPath(f"no_path: {a} -> {b}")
        return row[b]

    def path(self, a, b):
        self.checkpoint('bfs_path')
        if a not in self.free or b not in self.free:
            raise NoPath(f"endpoint_not_free: {a if a not in self.free else b}")
        if a == b:
            return (a,)
        key = (a, b) if a <= b else (b, a)
        cached = self._paths.get(key)
        if cached is None:
            lo, hi = key
            self._row(lo)
            parent = self._parents[lo]
            if hi not in parent:
                raise NoPath(f"no_path: {lo} -> {hi}")
            reverse = [hi]
            while reverse[-1] != lo:
                self.checkpoint('bfs_reconstruct')
                reverse.append(parent[reverse[-1]])
            cached = tuple(reversed(reverse))
            self._paths[key] = cached
        return cached if a <= b else tuple(reversed(cached))


def assert_legal(free, route):
    """Four-neighbour legality of an explicit cell sequence."""
    free = set(free)
    if not route:
        raise ValueError("empty route")
    if route[0] not in free:
        raise ValueError(f"start not free: {route[0]}")
    for p in route:
        if p not in free:
            raise ValueError(f"cell not free: {p}")
    for a, b in zip(route, route[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise ValueError(f"illegal step {a} -> {b}")
    return True


def chain(metric, points):
    """Concatenate the canonical connectors through ``points``."""
    if not points:
        return ()
    route = [points[0]]
    for a, b in zip(points, points[1:]):
        route.extend(metric.path(a, b)[1:])
    return tuple(route)
