"""Persistent RCG: III-B2/3 expansion, Def. III.8/9 pruning, Alg. 2, RCG A*.

Ported from ``sources/cstar_historical/cstar_strict/rcg.py``.  The structural
code (insertion, same-lap re-zipping with long-edge splitting, sqrt(2) cross-lap
expansion, essential-node classification, pruning, state update with the
leftward link-node insertion, Euclidean A*) is kept line-for-line in behaviour;
only the map type and the trace/exception reporting are adapted.  See
``specs/cstar_adaptation.md`` for the mechanism-to-source table.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import heapq
import math

from .public_map import dist, lap_points


class RCGCut(ValueError):
    """The RCG lost the paper's P3 (connected) property."""

    def __init__(self, message, connected=None, total=None, isolated=None):
        super().__init__(message)
        self.connected = connected
        self.total = total
        self.isolated = list(isolated or ())


@dataclass
class Node:
    state: str = "Op"
    kind: str = "frontier"
    reason: str = ""


class RCG:
    def tick(self,stage):
        getattr(self,'checkpoint',lambda stage:None)(stage)
    def __init__(self, known):
        self.map = known
        self.nodes = {}
        self.edges = {}
        self.sampled = set()
        self.processed = set()
        self.total_added = 0
        self.total_pruned = 0
        self.frontier_added = 0
        self.link_count = 0
        self.tsp_count = 0
        self.start_anchor = False

    # -- construction ----------------------------------------------------
    def insert(self, p, kind="frontier", state="Op"):
        if p in self.nodes:
            return
        self.nodes[p] = Node(state, kind)
        self.edges[p] = {}
        self.sampled.add(p)
        self.total_added += 1
        if kind == "link":
            self.link_count += 1
        elif kind == "tsp":
            self.tsp_count += 1
        elif kind == "frontier":
            self.frontier_added += 1

    def connect(self, a, b):
        if a != b and self.map.feasible(a, b):
            self.edges[a][b] = self.edges[b][a] = dist(a, b)

    def remove_edge(self, a, b):
        self.edges[a].pop(b, None)
        self.edges[b].pop(a, None)

    def expand(self, new):
        """Only affected columns and edges incident to new nodes are expanded."""
        new = set(new)
        columns = {p[0] for p in new}
        by_col = defaultdict(list)
        for p in self.nodes:
            self.tick('rcg_expand')
            if p[0] in columns:
                by_col[p[0]].append(p)
        for column in sorted(by_col):
            nodes = sorted(by_col[column], key=lambda p: p[1])
            # Split an old long vertical edge when a new node lies inside it.
            for p in nodes:
                for q in list(self.edges[p]):
                    if p[0] == q[0]:
                        self.remove_edge(p, q)
            for a, b in zip(nodes, nodes[1:]):
                self.connect(a, b)
        for p in sorted(new):
            for dx in (-1, 1):
                for dy in (-1, 0, 1):
                    q = (p[0] + dx, p[1] + dy)
                    if q in self.nodes:
                        self.connect(p, q)

    def sample_front(self, start=None):
        """III-B2 sampling front -> frontier samples -> new RCG nodes.

        Sample positions are the w-spaced integer lattice anchored at p0, so
        iterating all newly discovered free cells is equivalent to the minimum
        integer delta.  ``start`` is inserted unconditionally, as in the
        historical code; if the whole published map is already observed the
        start need not be a frontier cell, and the node is tagged ``start``
        (adaptation A5, see the spec).
        """
        new=set()
        for p in sorted(self.map.new_free):
            self.tick('rcg_sample')
            if p not in self.sampled and self.map.frontier(p):new.add(p)
        if start is not None:
            if start in self.nodes:
                pass
            elif self.map.frontier(start) or self.map.unknown_adjacent(start):
                new.add(start)
            else:
                self.insert(start, kind="start")
                self.start_anchor = True
                new.add(start)
        for p in sorted(new):
            self.insert(p)
        # Discovery may bridge two old partial laps even if the newly exposed
        # interior candidates are not frontier samples.  Re-evaluate those laps.
        changed_columns = {p[0] for p in self.map.new_free}
        affected = new | {p for p in self.nodes if p[0] in changed_columns}
        self.expand(affected)
        self.processed.update(self.map.new_free)
        self.map.new_free.clear()
        return new

    # -- Def. III.8 / III.9 ----------------------------------------------
    def essential(self):
        ends = {p for p in self.nodes if self.map.endpoint(p)}
        reasons = {p: ("unknown" if self.map.unknown_adjacent(p) else "lap_end")
                   for p in self.nodes if p in ends or self.map.unknown_adjacent(p)}
        transitions = set()
        for p in sorted(ends):
            self.tick('rcg_essential')
            groups = defaultdict(list)
            for q in self.edges[p]:
                if p[0] != q[0]:
                    groups[q[0]].append(q)
            for column in sorted(groups):
                candidates = groups[column]
                end_neighbors = [q for q in candidates if q in ends]
                if end_neighbors:
                    chosen = end_neighbors  # III.9 2a
                elif len(candidates) == 1:
                    chosen = candidates    # III.8 3a / III.9 2b-i
                else:
                    chosen = [min(candidates, key=lambda q: self.map.clearance_score(p, q))]
                for q in chosen:
                    reasons.setdefault(q, "end_connector")
                    transitions.add(tuple(sorted((p, q))))
        return reasons, transitions

    def prune(self, current):
        """Def. III.8/9, retaining current and open link nodes as execution anchors.

        A full classification pass is intentional: the historical reference does
        not claim the paper's frontier-local complexity, and the graph is never
        rebuilt.
        """
        reasons, transitions = self.essential()
        reasons[current] = "current_anchor"
        for p in getattr(self, "task_protected", set()):
            if p in self.nodes:reasons.setdefault(p, "task_anchor")
        for p in sorted(self.nodes):
            node = self.nodes[p]
            if node.kind in ("link", "tsp") and node.state == "Op":
                reasons.setdefault(p, node.kind)
        for p in sorted(set(self.nodes) - set(reasons)):
            self.tick('rcg_prune_remove')
            vertical = sorted(q for q in self.edges[p] if q[0] == p[0])
            if len(vertical) == 2:
                self.connect(*vertical)
            for q in list(self.edges[p]):
                self.remove_edge(p, q)
            del self.nodes[p], self.edges[p]
            self.total_pruned += 1
        for p in self.nodes:
            self.nodes[p].reason = reasons[p]
        for p in sorted(self.nodes):
            for q in list(self.edges[p]):
                self.tick('rcg_prune_edges')
                if p[0] != q[0] and tuple(sorted((p, q))) not in transitions:
                    # Preserve execution-anchor edges during the current action.
                    def protected(n):
                        return (self.nodes[n].kind in ("link", "tsp") and self.is_open(n)) or n in getattr(self, "task_protected", set())
                    if p != current and q != current and not protected(p) and not protected(q):
                        self.remove_edge(p, q)

    # -- state -----------------------------------------------------------
    def vertical(self, p):
        up = next((q for q in self.edges[p] if q[0] == p[0] and q[1] > p[1]), None)
        down = next((q for q in self.edges[p] if q[0] == p[0] and q[1] < p[1]), None)
        return up, down

    def is_open(self, p):
        return p in self.nodes and self.nodes[p].state == "Op"

    def update_state(self, current, goal):
        """Alg. 2, with the paper's prose reading of the Open condition.

        Prose / Lemma IV.6: close unless *both* vertical neighbours are Open
        (III-B4b).  Missing vertical neighbours are therefore treated as not
        Open.  Line 2 of the pseudocode reads "if q(U)=Cl or q(D)=Cl"; for the
        binary state domain both forms agree, as recorded in the historical
        SPEC.
        """
        up, down = self.vertical(current)
        if not (self.is_open(up) and self.is_open(down)):
            self.nodes[current].state = "Cl"
        inserted = []
        if goal[0] < current[0] and not self.is_open(current):
            for q in (up, down):
                if self.is_open(q):
                    p = (current[0], current[1] + (1 if q[1] > current[1] else -1))
                    if p not in self.nodes:
                        self.insert(p, "link")
                        inserted.append(p)
                    else:
                        # An existing sample at exactly w is the same link anchor;
                        # do not let the next pruning pass erase it.
                        self.nodes[p].kind = "link"
            self.expand(inserted)
        return {"closed": self.nodes[current].state, "up": list(up) if up else None,
                "down": list(down) if down else None, "link_inserted": [list(p) for p in inserted]}

    # -- graph search ----------------------------------------------------
    def path(self, start, goal):
        """Euclidean A* on the actual RCG, not an occupancy-grid fallback.

        Edge weights keep the paper's lap geometry (1 on a lap, sqrt(2) across
        adjacent laps).  The executed motion never uses these weights: the
        adapter realises every traversed edge with ``GridMetric.path``.
        """
        queue = [(dist(start, goal), 0.0, start)]
        costs, parent = {start: 0.0}, {}
        while queue:
            self.tick('rcg_search')
            _, g, p = heapq.heappop(queue)
            if g > costs[p] + 1e-9:
                continue
            if p == goal:
                result = [p]
                while p != start:
                    p = parent[p]
                    result.append(p)
                return result[::-1], costs[goal]
            for q, w in sorted(self.edges[p].items()):
                ng = g + w
                if ng < costs.get(q, math.inf) - 1e-9:
                    costs[q], parent[q] = ng, p
                    heapq.heappush(queue, (ng + dist(q, goal), ng, q))
        raise ValueError(f"RCG disconnected: {start} -> {goal}")

    def components(self):
        seen, sizes = set(), []
        for p in sorted(self.nodes):
            if p in seen:
                continue
            comp, todo = {p}, [p]
            seen.add(p)
            while todo:
                n = todo.pop()
                for q in self.edges[n]:
                    if q not in seen:
                        seen.add(q)
                        comp.add(q)
                        todo.append(q)
            sizes.append(sorted(comp))
        return sizes

    def validate(self, current):
        if current not in self.nodes:
            raise RCGCut(f"current node missing from RCG: {current}")
        seen, todo = {current}, [current]
        while todo:
            p = todo.pop()
            if p in self.edges[p]:
                raise RCGCut(f"self loop at {p}")
            for q, w in self.edges[p].items():
                if q not in self.nodes or self.edges[q].get(p) != w:
                    raise RCGCut(f"asymmetric edge {p} <-> {q}")
                if not self.map.feasible(p, q):
                    raise RCGCut(f"invalid edge {p} <-> {q}")
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        if seen != set(self.nodes):
            raise RCGCut(
                f"RCG lost connectivity: {len(seen)}/{len(self.nodes)}",
                connected=len(seen), total=len(self.nodes),
                isolated=sorted(set(self.nodes) - seen)[:16])

    def snapshot(self):
        return {
            "nodes": [[p[0], p[1], n.state, n.kind, n.reason] for p, n in sorted(self.nodes.items())],
            "edges": [[list(p), list(q)] for p in sorted(self.edges) for q in sorted(self.edges[p]) if p < q],
        }
