"""Multiscale Adaptive Potential Surfaces (MAPS) for epsilon-star.

Source of the rules: `sources/literature/epsilon_star_author_preprint.txt`
(Song & Gupta, "epsilon-star: An Online Coverage Path Planning Algorithm"),
Section 3-A (Eq. 2, Eq. 3) and Section 3-B (Algorithm 1, Eq. 4).

Original mechanism kept:
  * hierarchical multiscale tiling (MST) built by recursive halving: along x the
    axis is halved as n/2+n/2 when n is even and n'+(n'-1) with 2n'-1 = n when n
    is odd, then the same along y, producing four coarse cells per split, and the
    procedure is repeated until n/2 < 2 or n'-1 < 2;
  * level-0 potential from Eq. (2): -1 for obstacle/forbidden, 0 for explored,
    +B for unexplored, with B an exogenous column plateau field that increases by
    one unit per column toward the leftmost column (Fig. 3);
  * coarse potential from Eq. (3): E = pU * mean exogenous potential;
  * the directly-reachable set DR at level 0 (Definition 3.2) using the exact
    segment/supercover blocking test, i.e. no corner cutting.

Model adaptations (recorded in specs/epsilon_star_adaptation.md):
  * "allowed cell to be covered" = a currently published target that is free and
    not in the real ledger.  A free non-target cell keeps potential 0 (nothing to
    task) but stays passable;
  * the paper's forbidden buffer F around obstacles is empty here, because the
    footprint radius is 0 and the model has no inertia;
  * the tiling covers only the currently published bounding box, so no future
    extension can leak into the scale construction.
"""
import math
from dataclasses import dataclass


def _split_count(n):
    """Paper's halving rule: n even -> n/2 + n/2, n odd -> n' + (n'-1)."""
    if n <= 0:
        return (n,)
    if n % 2 == 0:
        return (n // 2, n // 2)
    nprime = (n + 1) // 2
    return (nprime, nprime - 1)


def _splittable(n):
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

    @property
    def cells_inclusive(self):
        for x in range(self.x0, self.x1 + 1):
            for y in range(self.y0, self.y1 + 1):
                yield (x, y)

    def contains(self, p):
        return self.x0 <= p[0] <= self.x1 and self.y0 <= p[1] <= self.y1

    def key(self):
        return (self.x0, self.x1, self.y0, self.y1)


def build_tree(x0, x1, y0, y1):
    """Recursive halving; returns (root, nodes_by_depth, max_depth)."""
    counter = {"next": 0}
    nodes_by_depth = {}

    def make(xa, xb, ya, yb, depth):
        node = Block(xa, xb, ya, yb, depth, 0)
        nodes_by_depth.setdefault(depth, []).append(node)
        children = []
        w, h = node.width, node.height
        if _splittable(w) or _splittable(h):
            xs = _split_count(w) if _splittable(w) else (w,)
            ys = _split_count(h) if _splittable(h) else (h,)
            cx = xa
            for part in xs:
                cy = ya
                for other in ys:
                    children.append(make(cx, cx + part - 1, cy, cy + other - 1, depth + 1))
                    cy += other
                cx += part
        counter["next"] += 1
        return {"node": node, "children": children}

    tree = make(x0, x1, y0, y1, 0)
    return tree, nodes_by_depth, max(nodes_by_depth)


def _retag(tree, max_depth):
    """Assign level = max_depth - depth, in place, returning a node index."""
    index = {}
    stack = [tree]
    while stack:
        entry = stack.pop()
        node = entry["node"]
        levelled = Block(node.x0, node.x1, node.y0, node.y1, node.depth, max_depth - node.depth)
        entry["node"] = levelled
        index[levelled.key()] = entry
        stack.extend(entry["children"])
    return index


class MAPS:
    """Potentials, scales and the level-0 direct-reachability set."""

    def __init__(self, free, published_targets, covered, forbidden_ring=0,
                 neighbourhood0_halfwidth=3):
        self.free = frozenset(free)
        self.targets = frozenset(published_targets)
        self.covered = frozenset(covered)
        self.forbidden_ring = int(forbidden_ring)
        self.neighbourhood0_halfwidth = int(neighbourhood0_halfwidth)

        cells = set(self.free) | set(self.targets)
        if not cells:
            raise ValueError("empty current published region")
        self.x0 = min(p[0] for p in cells)
        self.x1 = max(p[0] for p in cells)
        self.y0 = min(p[1] for p in cells)
        self.y1 = max(p[1] for p in cells)

        self.tree, self.by_depth, self.max_depth = build_tree(self.x0, self.x1, self.y0, self.y1)
        self.index = _retag(self.tree, self.max_depth)
        self.nodes_by_level = {}
        for key, entry in self.index.items():
            self.nodes_by_level.setdefault(entry["node"].level, []).append(entry["node"])

        # --- exogenous field B: plateaus +1 per column toward the leftmost column
        self.bmax = self.x1 - self.x0 + 1
        self.B = {x: self.x1 - x + 1 for x in range(self.x0, self.x1 + 1)}

        # --- forbidden buffer (empty unless the caller asks for one)
        self.forbidden = set()
        if self.forbidden_ring > 0:
            reach = self.forbidden_ring
            blocked = {(x, y) for x in range(self.x0 - reach, self.x1 + reach + 1)
                       for y in range(self.y0 - reach, self.y1 + reach + 1)} - set(self.free)
            for bx, by in blocked:
                for dx in range(-reach, reach + 1):
                    for dy in range(-reach, reach + 1):
                        if (bx + dx, by + dy) in self.free:
                            self.forbidden.add((bx + dx, by + dy))

        # --- level-0 symbolic state and potential, Eq. (2)
        self.state = {}
        for x in range(self.x0, self.x1 + 1):
            for y in range(self.y0, self.y1 + 1):
                p = (x, y)
                if p not in self.free or p in self.forbidden:
                    self.state[p] = "O"
                elif self.outstanding(p):
                    self.state[p] = "U"
                else:
                    self.state[p] = "E"
        self.E0 = {}
        self.refresh_level0()
        self.E = {0: self.E0}
        for level in range(1, self.max_depth + 1):
            self.E[level] = self._coarse(level)

    # -- ledger view -----------------------------------------------------
    def outstanding(self, p):
        return p in self.targets and p in self.free and p not in self.covered

    # -- potentials ------------------------------------------------------
    def refresh_level0(self, cells=None):
        targets = self.targets
        covered = self.covered
        free = self.free
        forbidden = self.forbidden
        E0 = self.E0
        if cells is None:
            cells = [(x, y) for x in range(self.x0, self.x1 + 1)
                     for y in range(self.y0, self.y1 + 1)]
        for p in cells:
            if p not in free or p in forbidden:
                E0[p] = -1
            elif p not in targets or p in covered:
                E0[p] = 0
            else:
                E0[p] = self.B[p[0]]
        self.state = {p: ("O" if v < 0 else "E" if v == 0 else "U") for p, v in E0.items()}

    def mark_covered(self, p):
        """Update the potential surface from the real ledger, not from a claim."""
        if p in self.E0 and self.outstanding(p):
            self.covered = frozenset(set(self.covered) | {p})
            self.refresh_level0([p])
            return True
        return False

    def _coarse_cells(self, block):
        return [c for c in block.cells_inclusive]

    def _coarse(self, level):
        """Eq. (3): E = pU * mean exogenous potential, over the block."""
        out = {}
        for block in self.nodes_by_level.get(level, ()):
            cells = self._coarse_cells(block)
            total = len(cells)
            unexplored = sum(1 for p in cells if self.state.get(p) == "U")
            mean_b = sum(self.B[p[0]] for p in cells if p[0] in self.B) / total
            out[block.key()] = (unexplored / total) * mean_b if total else 0.0
        return out

    def recompute_coarse(self):
        for level in range(1, self.max_depth + 1):
            self.E[level] = self._coarse(level)

    # -- scales ----------------------------------------------------------
    def block_at(self, p, level):
        """Block containing p at the given level; falls back to the finest block."""
        if level == 0:
            return Block(p[0], p[0], p[1], p[1], self.max_depth, 0)
        entry = self.tree
        while True:
            node = entry["node"]
            if node.level <= level or not entry["children"]:
                return node
            nxt = None
            for child in entry["children"]:
                if child["node"].contains(p):
                    nxt = child
                    break
            if nxt is None:
                return node
            entry = nxt

    def neighbourhood(self, p, level):
        """N^level(p): level blocks inside the local window, including p's block."""
        if level == 0:
            r = self.neighbourhood0_halfwidth
            return [q for q in self.E0
                    if abs(q[0] - p[0]) <= r and abs(q[1] - p[1]) <= r]
        block = self.block_at(p, level)
        if block.level > level:
            return [block]
        pad = max(block.width, block.height)
        window = (block.x0 - pad, block.x1 + pad, block.y0 - pad, block.y1 + pad)
        out = []
        for other in self.nodes_by_level.get(level, ()):
            if (other.x1 < window[0] or other.x0 > window[1]
                    or other.y1 < window[2] or other.y0 > window[3]):
                continue
            out.append(other)
        return out

    # -- direct reachability, Definition 3.2 -----------------------------
    def directly_reachable(self, p, candidates):
        """Definition 3.2.  N^0 includes p itself, and p is trivially reachable."""
        free = self.free
        return {q for q in candidates if self._clear(p, q, free)}

    def _clear(self, a, b, free):
        """True when the closed segment a-b touches only free cells."""
        for cell in segment_cells(a, b):
            if cell not in free:
                return False
        return True

    def describe(self):
        return {
            "bounding_box": [self.x0, self.x1, self.y0, self.y1],
            "bmax": self.bmax, "max_level": self.max_depth,
            "blocks_per_level": {str(l): len(v) for l, v in sorted(self.nodes_by_level.items())},
            "forbidden_cells": len(self.forbidden),
            "unexplored_level0": sum(1 for v in self.E0.values() if v > 0),
        }


def segment_cells(a, b):
    """Every closed unit square the segment touches, via Liang-Barsky intervals.

    Touching counts, so a segment through an exact corner touches all four
    squares and no corner can be cut.
    """
    if a == b:
        return (a,)
    ax, ay = a
    bx, by = b
    lo_x, hi_x = min(ax, bx), max(ax, bx)
    lo_y, hi_y = min(ay, by), max(ay, by)
    hits = []
    for x in range(int(math.floor(lo_x)) - 1, int(math.ceil(hi_x)) + 2):
        for y in range(int(math.floor(lo_y)) - 1, int(math.ceil(hi_y)) + 2):
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
