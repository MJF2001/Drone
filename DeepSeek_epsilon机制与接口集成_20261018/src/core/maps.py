"""MAPS for epsilon-star, rebuilt against the author preprint.

Every rule below quotes the source text it implements; the mapping is tabulated in
``reports/原文对应表.md``.

Section 3-A, p.3::

    The epsilon-cell tiling T of the search area forms the finest level of MST and
    is referred as T^0.  ... If n is even, then the axis is divided into two
    regions of n/2 elements each.  If n is odd, ... n' and n'-1 ... 2n'-1 = n.
    This procedure is repeated along the y-axis over all columns to generate 4
    coarse cells in total, which form the coarsest tiling, i.e. T^L.  Now, again
    let n be the maximum number of epsilon-cells along the x-axis in a coarse
    cell.  Then ... each of these four coarse cells are further divided ...
    This procedure is repeated until n/2 < 2 or n'-1 < 2.

Consequences that the previous implementation got wrong and that are properties of
this module (asserted in ``tools/probe_structure.py``):

* ``L`` is the number of split rounds; ``T^L`` is the *four-cell* split of the
  whole area, ``T^1`` is the finest coarse tiling.  The whole area is **not** a
  coarse cell, and the finest coarse tiling is **not** level 0.
* Every ``T^l`` is a partition of the tiled area: pairwise disjoint, exact cover.
* ``N^0`` is the 7x7 window of epsilon-cells; ``N^l`` for ``l >= 1`` is the 3x3
  array of level-``l`` cells around the one containing lambda (paper, Results:
  "the neighborhood was chosen to contain 7x7 cells at the lowest level and 3x3
  cells at higher levels").  The window is indexed in *cells*, not padded by
  ``max(width, height)``, which broke on non-square blocks.
"""
import math
from dataclasses import dataclass

TILE_LEVEL0_HALFWIDTH = 3          # 7x7 window, paper's experiment setting
TILE_LEVEL_HALFWIDTH = 1           # 3x3 window at every coarse level

OBSTACLE, FORBIDDEN, EXPLORED, UNEXPLORED = "O", "F", "E", "U"


def split_sizes(n):
    """Paper's halving: n even -> n/2 + n/2; n odd -> n' + (n'-1)."""
    if n <= 0:
        return (n,)
    if n % 2 == 0:
        return (n // 2, n // 2)
    nprime = (n + 1) // 2
    return (nprime, nprime - 1)


def splittable(n):
    """Stop when n/2 < 2 (even) or n'-1 < 2 (odd)."""
    if n % 2 == 0:
        return n // 2 >= 2
    return ((n + 1) // 2 - 1) >= 2


@dataclass(frozen=True)
class Block:
    x0: int
    x1: int
    y0: int
    y1: int
    depth: int
    level: int

    @property
    def width(self):
        return self.x1 - self.x0 + 1

    @property
    def height(self):
        return self.y1 - self.y0 + 1

    def contains(self, p):
        return self.x0 <= p[0] <= self.x1 and self.y0 <= p[1] <= self.y1

    def key(self):
        return (self.x0, self.x1, self.y0, self.y1)

    def cells(self):
        for x in range(self.x0, self.x1 + 1):
            for y in range(self.y0, self.y1 + 1):
                yield (x, y)


def _children(xa, xb, ya, yb):
    """Split one rectangle with the paper's rule; empty when it cannot split."""
    w, h = xb - xa + 1, yb - ya + 1
    if not (splittable(w) or splittable(h)):
        return []
    xs = split_sizes(w) if splittable(w) else (w,)
    ys = split_sizes(h) if splittable(h) else (h,)
    out = []
    cx = xa
    for part_x in xs:
        cy = ya
        for part_y in ys:
            out.append((cx, cx + part_x - 1, cy, cy + part_y - 1))
            cy += part_y
        cx += part_x
    return out


def build_tilings(x0, x1, y0, y1):
    """Return `{level: [Block, ...]}` and `L`.

    `L` is the number of refinement rounds of the deepest branch, `T^L` is the
    first split (the four coarse cells) and `T^1` the finest coarse tiling.
    Because the paper's stopping rule can fire earlier on a small sibling, the
    frontier of a finer tiling keeps such a block rather than dropping it: a block
    that cannot split is a member of every finer tiling, which keeps every `T^l`
    a partition of the tiled rectangle.
    """
    depths = {}

    def walk(node, depth):
        depths[node] = depth
        for child in _children(*node):
            walk(child, depth + 1)

    walk((x0, x1, y0, y1), 0)
    L = max(depths.values())
    if L == 0:
        return {}, 0

    tilings = {}
    for level in range(1, L + 1):
        target = L - level + 1
        frontier = []

        def walk_front(node, depth):
            if depth >= target or not _children(*node):
                frontier.append((node, depth))
                return
            for child in _children(*node):
                walk_front(child, depth + 1)

        walk_front((x0, x1, y0, y1), 0)
        blocks = [Block(*node, depth=depth, level=level) for node, depth in frontier]
        blocks.sort(key=lambda b: (b.y0, b.x0))
        tilings[level] = blocks
    return tilings, L


def check_partition(tilings, x0, x1, y0, y1):
    """Every tiling must be an exact partition of the tiled rectangle."""
    problems = []
    for level, blocks in sorted(tilings.items()):
        seen = set()
        overlap = 0
        for block in blocks:
            for cell in block.cells():
                if cell in seen:
                    overlap += 1
                seen.add(cell)
        area = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
        if overlap:
            problems.append(f"level {level}: {overlap} overlapping cells")
        if seen != area:
            problems.append(f"level {level}: missing {len(area - seen)} cells, "
                            f"extra {len(seen - area)}")
        widths = {block.width for block in blocks}
        heights = {block.height for block in blocks}
        if max(widths) - min(widths) > 1 or max(heights) - min(heights) > 1:
            problems.append(f"level {level}: block sizes vary too much "
                            f"widths={sorted(widths)} heights={sorted(heights)}")
    return problems


class MAPS:
    """Potentials, scales, neighbourhoods and the level-0 direct reachability set."""

    def __init__(self, free, published_targets, covered, forbidden_ring=0,
                 level0_halfwidth=TILE_LEVEL0_HALFWIDTH,
                 level_halfwidth=TILE_LEVEL_HALFWIDTH, deadline=None):
        self.free = frozenset(free)
        self.targets = frozenset(published_targets)
        self.covered = frozenset(covered)
        self.deadline = deadline
        self.level0_halfwidth = int(level0_halfwidth)
        self.level_halfwidth = int(level_halfwidth)
        self._tick()

        cells = set(self.free) | set(self.targets)
        if not cells:
            raise ValueError("empty current published region")
        self.x0 = min(p[0] for p in cells)
        self.x1 = max(p[0] for p in cells)
        self.y0 = min(p[1] for p in cells)
        self.y1 = max(p[1] for p in cells)

        self.forbidden = self._build_forbidden(int(forbidden_ring))
        self.tilings, self.L = build_tilings(self.x0, self.x1, self.y0, self.y1)
        self._index_levels()

        # Exogenous field B, Eq. (2) caption: plateau +1 per column toward the
        # leftmost column (Fig. 3), so B_max sits on the left.
        self.bmax = self.x1 - self.x0 + 1
        self.B = {x: self.x1 - x + 1 for x in range(self.x0, self.x1 + 1)}

        self.state = {}
        self.E0 = {}
        for x in range(self.x0, self.x1 + 1):
            self._tick()
            for y in range(self.y0, self.y1 + 1):
                p = (x, y)
                self.state[p] = self._initial_state(p)
                self.E0[p] = self._potential0(p)
        self.E = {0: self.E0}
        for level in range(1, self.L + 1):
            self.E[level] = self._coarse_all(level)

        self.counters = {"level0_refresh": 0, "coarse_block_updates": 0,
                         "neighbourhood_calls": 0}

    # ------------------------------------------------------------------ setup
    def _tick(self):
        if self.deadline is not None:
            self.deadline.check()

    def _build_forbidden(self, ring):
        if ring <= 0:
            return set()
        blocked = {(x, y) for x in range(self.x0 - ring, self.x1 + ring + 1)
                   for y in range(self.y0 - ring, self.y1 + ring + 1)} - set(self.free)
        out = set()
        for bx, by in blocked:
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if (bx + dx, by + dy) in self.free:
                        out.add((bx + dx, by + dy))
        return out

    def _index_levels(self):
        """Cell size per level, used to locate lambda's block without a tree walk."""
        self._level_origin = {}
        self._level_shape = {}
        for level, blocks in self.tilings.items():
            xs = sorted({(b.x0, b.x1) for b in blocks})
            ys = sorted({(b.y0, b.y1) for b in blocks})
            self._level_origin[level] = (xs, ys)
            self._level_shape[level] = (len(xs), len(ys))
        self._by_key = {level: {b.key(): b for b in blocks}
                        for level, blocks in self.tilings.items()}

    def _initial_state(self, p):
        if p not in self.free or p in self.forbidden:
            return OBSTACLE
        return UNEXPLORED if self.outstanding(p) else EXPLORED

    def _potential0(self, p):
        """Eq. (2): -1 for O or F, 0 for E, +B for U."""
        symbol = self.state[p]
        if symbol in (OBSTACLE, FORBIDDEN):
            return -1
        if symbol == EXPLORED:
            return 0
        return self.B[p[0]]

    # ------------------------------------------------------------------ views
    def outstanding(self, p):
        return p in self.targets and p in self.free and p not in self.covered

    def unexplored(self, p):
        return self.state.get(p) == UNEXPLORED

    def any_unexplored(self):
        return any(symbol == UNEXPLORED for symbol in self.state.values())

    # ------------------------------------------------------- incremental update
    def set_explored(self, p):
        """E^l <- E for one cell: Eq. (2) at level 0, Eq. (3) on its ancestors."""
        if self.state.get(p) != UNEXPLORED:
            return False
        self.state[p] = EXPLORED
        self.E0[p] = 0.0
        self.counters["level0_refresh"] += 1
        self.covered = frozenset(set(self.covered) | {p})
        for level in range(1, self.L + 1):
            block = self.block_at(p, level)
            if block is None:
                continue
            self.E[level][block.key()] = self._coarse_one(block)
            self.counters["coarse_block_updates"] += 1
        return True

    def _coarse_one(self, block):
        """Eq. (3): E = pU * mean(B) over the block."""
        cells = list(block.cells())
        total = len(cells)
        if not total:
            return 0.0
        unexplored = sum(1 for p in cells if self.state.get(p) == UNEXPLORED)
        mean_b = sum(self.B[p[0]] for p in cells) / total
        return (unexplored / total) * mean_b

    def _coarse_all(self, level):
        return {block.key(): self._coarse_one(block)
                for block in self.tilings.get(level, ())}

    # ------------------------------------------------------------------ scales
    def block_at(self, p, level):
        """Coarse cell of level ``level`` that contains ``p`` (None if outside)."""
        if level < 1 or level > self.L:
            return None
        xs, ys = self._level_origin[level]
        xr = next((rng for rng in xs if rng[0] <= p[0] <= rng[1]), None)
        yr = next((rng for rng in ys if rng[0] <= p[1] <= rng[1]), None)
        if xr is None or yr is None:
            return None
        return self._by_key[level].get((xr[0], xr[1], yr[0], yr[1]))

    def neighbourhood0(self, p):
        """N^0(lambda): the 7x7 window of epsilon-cells, including lambda."""
        self.counters["neighbourhood_calls"] += 1
        r = self.level0_halfwidth
        out = []
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                q = (p[0] + dx, p[1] + dy)
                if q in self.state:
                    out.append(q)
        return out

    def neighbourhood(self, p, level):
        """N^l(lambda): the 3x3 array of level-l cells containing/around lambda.

        The window is counted in coarse cells (paper: 3x3 at higher levels), not by
        padding with the block's longest side, which produced non-3x3 windows on
        non-square blocks.
        """
        if level == 0:
            return self.neighbourhood0(p)
        self.counters["neighbourhood_calls"] += 1
        block = self.block_at(p, level)
        if block is None:
            return []
        xs, ys = self._level_origin[level]
        half = self.level_halfwidth
        xi = next(i for i, rng in enumerate(xs) if rng == (block.x0, block.x1))
        yi = next(i for i, rng in enumerate(ys) if rng == (block.y0, block.y1))
        out = []
        for i in range(xi - half, xi + half + 1):
            if not (0 <= i < len(xs)):
                continue
            for j in range(yi - half, yi + half + 1):
                if not (0 <= j < len(ys)):
                    continue
                found = self._by_key[level].get((xs[i][0], xs[i][1], ys[j][0], ys[j][1]))
                if found is not None:
                    out.append(found)
        return out

    # --------------------------------------------------- direct reachability
    def directly_reachable(self, p, candidates):
        """Definition 3.2: the centroid segment must not be obstructed."""
        return {q for q in candidates if self._clear(p, q)}

    def _clear(self, a, b):
        for cell in segment_cells(a, b):
            if cell not in self.free or cell in self.forbidden:
                return False
        return True

    # ------------------------------------------------------------------ report
    def describe(self):
        return {
            "bounding_box": [self.x0, self.x1, self.y0, self.y1],
            "L": self.L,
            "cells_per_level": {str(level): len(blocks)
                                for level, blocks in sorted(self.tilings.items())},
            "block_sizes": {str(level): sorted({(b.width, b.height) for b in blocks})
                            for level, blocks in sorted(self.tilings.items())},
            "bmax": self.bmax,
            "forbidden_cells": len(self.forbidden),
            "unexplored_level0": sum(1 for s in self.state.values() if s == UNEXPLORED),
            "counters": dict(self.counters),
        }


def segment_cells(a, b):
    """Every closed unit square the segment touches (touching counts)."""
    if a == b:
        return (a,)
    ax, ay = a
    bx, by = b
    hits = []
    for x in range(int(math.floor(min(ax, bx))) - 1, int(math.ceil(max(ax, bx))) + 2):
        for y in range(int(math.floor(min(ay, by))) - 1, int(math.ceil(max(ay, by))) + 2):
            interval = _box_interval(ax, ay, bx, by, x, y)
            if interval is not None:
                hits.append((interval, (x, y)))
    hits.sort()
    return tuple(cell for _, cell in hits)


def _box_interval(ax, ay, bx, by, cx, cy):
    lo, hi = 0.0, 1.0
    for start, delta, centre in ((ax, bx - ax, cx), (ay, by - ay, cy)):
        low, high = centre - 0.5, centre + 0.5
        if abs(delta) < 1e-12:
            if not low <= start <= high:
                return None
        else:
            u, v = (low - start) / delta, (high - start) / delta
            if u > v:
                u, v = v, u
            lo, hi = max(lo, u), min(hi, v)
            if lo > hi + 1e-12:
                return None
    return lo
