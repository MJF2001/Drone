"""Planner-side map for the adapted C* port.

Source of the mechanisms in this file
-------------------------------------
``sources/cstar_historical/cstar_strict/geometry.py``:

* ``box_hit`` / ``supercover`` / ``segment_free`` -- exact closed-square ray and
  segment geometry, no corner cutting;
* ``KnownMap`` -- occupancy accumulated only from observations, with a
  ``new_free`` set that drives progressive sampling (III-B2);
* ``World.observe`` -- the historical ideal-grid ray sensor (used by the
  adapter's ``mode="sensed"``).

What changed for the current model
----------------------------------
1. The footprint radius is 0.  The historical continuous circular coverage
   device (``coverage_audit``, radius ``r_c``) is not reproduced here: in the
   current model a target is completed by *being at* its cell, so coverage is a
   ledger recomputed from the executed cell route by the caller.
2. ``PublicMap`` replaces ``KnownMap`` unchanged in behaviour but is named after
   what the current model actually publishes: one current free-cell set.  In
   ``mode="public_map"`` it is filled by a single bulk ``update`` at k=0; in
   ``mode="sensed"`` it is filled incrementally by ``PublishedWorld.observe``.
3. Only free cells and *published blocked targets* are observed.  Everything
   else stays unknown, so the RCG's unknown-adjacency test (Def. III.8.1) still
   has a meaning at the published-region boundary.  This choice is what makes
   the frontier sampler degenerate to the boundary ring in ``public_map`` mode;
   the concrete numbers are in ``specs/cstar_adaptation.md``.

The sensor model in ``PublishedWorld.observe`` is copied from the historical
``World`` (same radius offsets, same entry-time tie group treatment, same
opaque-square blocking).  It senses the *currently published* map only, so it
cannot leak future information.
"""
from __future__ import annotations

import math
from functools import lru_cache

CARDINAL = ((-1, 0), (0, 1), (0, -1), (1, 0))
AROUND = tuple((x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if x or y)


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) if dx or dy else 0.0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def box_hit(a, b, cell, pad=0.0):
    """Liang-Barsky interval: does the segment intersect the closed square?"""
    lo, hi = 0.0, 1.0
    for axis in (0, 1):
        d = b[axis] - a[axis]
        low, high = cell[axis] - 0.5 - pad, cell[axis] + 0.5 + pad
        if abs(d) < 1e-12:
            if not low <= a[axis] <= high:
                return None
        else:
            u, v = (low - a[axis]) / d, (high - a[axis]) / d
            if u > v:
                u, v = v, u
            lo, hi = max(lo, u), min(hi, v)
            if lo > hi + 1e-12:
                return None
    return lo, hi


@lru_cache(maxsize=100000)
def supercover(a, b):
    """All closed cells touched by the segment, ordered by entry distance.

    Includes both side cells at an exact diagonal corner: no corner cutting.
    This is what makes a diagonal RCG edge conservative: the executed
    four-neighbour path can always use one of the two side cells.
    """
    cells = []
    for x in range(math.floor(min(a[0], b[0]) - 0.5), math.ceil(max(a[0], b[0]) + 0.5) + 1):
        for y in range(math.floor(min(a[1], b[1]) - 0.5), math.ceil(max(a[1], b[1]) + 0.5) + 1):
            interval = box_hit(a, b, (x, y))
            if interval is not None:
                cells.append((interval[0], (x, y)))
    return tuple(p for _, p in sorted(cells))


def segment_free(a, b, free):
    return all(p in free for p in supercover(tuple(a), tuple(b)))


def lap_points(a, b):
    assert a[0] == b[0]
    return [(a[0], y) for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)]


class PublicMap:
    """Occupancy known to the planner, accumulated only from observations.

    ``free`` is the known-free set, ``new_free`` holds free cells discovered
    since the last sampling pass (the sampling front driver of III-B2), and
    ``cells`` holds every observed cell with its occupancy value.  A cell that
    is absent from ``cells`` is unknown.
    """

    def __init__(self):
        self.cells = {}
        self.free = set()
        self.new_free = set()
        self.version = 0  # increments when known-free grows; invalidates connectors

    def update(self, observation):
        if any(p in self.cells and self.cells[p] != v for p, v in observation.items()):
            raise ValueError("static-world observation changed occupancy")
        fresh = {p: v for p, v in observation.items() if p not in self.cells}
        self.cells.update(observation)
        f = {p for p, v in fresh.items() if v}
        self.new_free.update(f)
        self.free.update(f)
        if f:
            self.version += 1
        return fresh

    def frontier(self, p):
        # B(p, w) with w = 1 intersects any of the eight neighbouring closed squares.
        return any(add(p, d) not in self.free for d in AROUND)

    def unknown_adjacent(self, p):
        return any(add(p, d) not in self.cells for d in AROUND)

    def endpoint(self, p):
        return any(add(p, d) not in self.free for d in ((0, 1), (0, -1)))

    def feasible(self, a, b):
        return segment_free(a, b, self.free)

    def clearance_score(self, a, b):
        """Def. III.8/9 proximity tie-break: 5 samples, nearest blocked square.

        Unknown counts as blocked, exactly as in the historical reproduction.
        Ties fall back to edge length and coordinates, so the choice is
        deterministic.
        """
        samples = [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])) for t in (0, 0.25, 0.5, 0.75, 1)]
        values = []
        for x, y in samples:
            best = math.inf
            for xx in range(math.floor(x) - 2, math.floor(x) + 3):
                for yy in range(math.floor(y) - 2, math.floor(y) + 3):
                    if (xx, yy) not in self.free:
                        dd = math.hypot(max(abs(x - xx) - 0.5, 0), max(abs(y - yy) - 0.5, 0))
                        best = min(best, dd)
            values.append(best)
        return (sum(values) / len(values), dist(a, b), b)


def published_observation(free, published_targets):
    """Observation of the whole currently published map, made once at k=0.

    Free cells are observed free; published targets that are not free are
    observed blocked (they are the deferred targets, published *and* known to be
    obstructed).  No other cell is observed, so the complement of the published
    region remains unknown to the planner.
    """
    observation = {tuple(p): True for p in free}
    for p in published_targets:
        if p not in free:
            observation[tuple(p)] = False
    return observation


class PublishedWorld:
    """Ground truth exposed only through ``observe``: the published map itself.

    The historical ``World`` is reused verbatim, with ``free`` fixed to the
    currently published free set and every other cell inside the sensing radius
    treated as an opaque, no-fly square.  ``radius`` is an adapter parameter the
    current model does not specify (default 2.0 cells).
    """

    def __init__(self, free, published_targets=(), radius=2.0):
        self.free = frozenset(tuple(p) for p in free)
        self.published_targets = frozenset(tuple(p) for p in published_targets)
        self.radius = float(radius)
        span = range(-math.ceil(self.radius), math.ceil(self.radius) + 1)
        self.offsets = tuple((x, y) for x in span for y in span
                             if x * x + y * y <= self.radius * self.radius)

    def observe(self, pose):
        # Ideal grid ray sensor. Same-radius center tests, opaque square obstacles.
        origin = (int(round(pose[0])), int(round(pose[1])))
        observed = {}
        for dx, dy in self.offsets:
            q = (origin[0] + dx, origin[1] + dy)
            if dist(pose, q) > self.radius:
                continue
            # At a corner several closed cells have the same entry distance.
            # Test the whole group before exposing free cells: coordinate-order
            # tie breaking could leak a free cell behind an opaque corner.
            ray = supercover(tuple(pose), q)
            index = 0
            while index < len(ray):
                entry = box_hit(pose, q, ray[index])[0]
                group = []
                while index < len(ray) and abs(box_hit(pose, q, ray[index])[0] - entry) < 1e-10:
                    group.append(ray[index])
                    index += 1
                blocked = [p for p in group if p not in self.free]
                if blocked:
                    observed.update({p: False for p in blocked})
                    break
                observed.update({p: True for p in group})
        return observed
