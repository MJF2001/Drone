"""C* Algorithms 1--4 on the current model, as an explicitly labelled adaptation.

Ported from ``sources/cstar_historical/cstar_strict/planner.py``.  The control
flow, the goal order, the retreat fallback, the coverage-hole detection and the
densify + nearest-neighbour + 2-opt TSP are the historical ones.  The differences
are exactly the adaptations listed in ``specs/cstar_adaptation.md``:

* the graph is sampled from the *published* map (or from the historical ray
  sensor over it) instead of from open-ended exploration;
* every traversed RCG edge is executed as a legal four-neighbour cell path via
  ``common_geometry.GridMetric``; the graph metric itself keeps the paper's
  ``1``/``sqrt(2)`` lap geometry;
* retreat adjacency is refreshed per executed unit cell step, because the
  current model moves one cell at a time instead of sweeping a continuous
  segment;
* the outer loop carries a wall-clock cap (a hard safety cap, never a natural
  stop) and records a hand-traceable decision record per iteration;
* there is no continuous circular coverage audit: footprint radius 0 means the
  caller's route ledger decides coverage.  ``CStar`` therefore stops when the
  RCG is exhausted and returns its own sweep; the adapter adds only the fixed
  base return and reports ``coverage_incomplete`` if the sweep missed a target.
  It never appends a target-completion pass to the graded route.
"""
from __future__ import annotations

import math
import random
import time

from common_geometry import GridMetric

from .public_map import dist, lap_points, point_segment_distance
from .rcg import RCG, RCGCut


class WallClockCap(Exception):
    """The hard safety cap fired.  Never a natural termination."""


def optimize_tsp(points, start, end, cost):
    """Fixed-start nearest neighbour then exhaustive improving 2-opt.

    A free end (``end is None``) is optimized directly, not via the infeasible
    dummy-node case.  ``points`` must contain ``start`` and, when fixed, ``end``.
    This is the historical Algorithm-3 solver, unchanged; the three end cases
    are the three call shapes used by ``cover_holes`` and by the adapter's
    optional, non-default ``completion_tsp`` variant.
    """
    remaining = set(points) - {start}
    if end is not None:
        remaining.discard(end)
    route = [start]
    while remaining:
        q = min(remaining, key=lambda p: (cost[route[-1], p], p))
        route.append(q)
        remaining.remove(q)
    if end is not None and (len(route) > 1 or end != start):
        route.append(end)

    def length(seq):
        return sum(cost[a, b] for a, b in zip(seq, seq[1:]))

    before = length(route)
    improved = True
    while improved:
        improved = False
        stop = len(route) - 1 if end is not None else len(route)
        for i in range(1, stop - 1):
            for j in range(i + 1, stop):
                old = cost[route[i - 1], route[i]]
                new = cost[route[i - 1], route[j]]
                if j + 1 < len(route):
                    old += cost[route[j], route[j + 1]]
                    new += cost[route[i], route[j + 1]]
                if new < old - 1e-9:
                    route[i:j + 1] = reversed(route[i:j + 1])
                    improved = True
    return route, before, length(route)


class CStar:
    """RCG-based coverage planner (Algorithms 1--4), current-model adaptation."""

    def __init__(self, start, known, sensor=None, seed=0, holes=True,
                 deadline=None, wall_clock=None, graph_factory=RCG):
        self.map = known
        self.sensor = sensor
        self.graph = graph_factory(self.map)
        self.current = tuple(start)
        self.start = tuple(start)
        self.rng = random.Random(seed)
        self.holes_enabled = holes
        self.path = [tuple(start)]
        self.modes = ["start"]
        self.observations = []
        self.retreat = set()
        self.events = []
        self.history = []
        self.iterations = 0
        self.retreat_count = 0
        self.keep_open_count = 0
        self.deadline = deadline
        self._clock = wall_clock or time.perf_counter
        self._metric = None
        self._metric_version = -1
        self.iterations_trace = []
        self.status = "running"
        self.error = ""
        self.component_sizes = None
        if self.sensor is not None:
            self.sense(self.current)
        new = self.graph.sample_front(self.current)
        self.initial_samples = [tuple(p) for p in sorted(new)]
        self.initial_known_free = len(self.map.free)

    # -- sensing / navigation -------------------------------------------
    def sense(self, p):
        if self.sensor is None:
            return {}
        fresh = self.map.update(self.sensor.observe(p))
        self.observations.append([[x, y, int(v)] for (x, y), v in sorted(fresh.items())])
        return fresh

    def metric(self):
        """Four-neighbour connector over what the planner currently knows."""
        if self._metric is None or self._metric_version != self.map.version:
            self._metric = GridMetric(frozenset(self.map.free))
            self._metric_version = self.map.version
        return self._metric

    def _check_deadline(self):
        if self.deadline is not None and self._clock() > self.deadline:
            raise WallClockCap("wall clock cap")

    def refresh_retreat(self, a=None, b=None):
        self.retreat = {p for p in self.retreat if self.graph.is_open(p)}
        if a is None:
            a = b = self.current
        for p in sorted(self.graph.nodes):
            if self.graph.is_open(p) and point_segment_distance(p, a, b) <= math.sqrt(2) + 1e-9:
                self.retreat.add(p)

    def register_new_retreats(self, new):
        # New frontier/link points can lie beside the just-traversed segment,
        # although the robot has already left it when the graph is expanded.
        segments = list(zip(self.path, self.path[1:])) or [(self.current, self.current)]
        for p in sorted(new):
            if self.graph.is_open(p) and any(
                    point_segment_distance(p, a, b) <= math.sqrt(2) + 1e-9 for a, b in segments):
                self.retreat.add(p)

    def navigate(self, route, mode):
        """Execute an RCG node route as four-neighbour unit-cell motion.

        The graph edge ``(a, b)`` keeps its Euclidean weight for graph search;
        the executed step uses ``GridMetric.path(a, b)``, so a diagonal graph
        edge becomes two legal unit steps.  Sensing (when a sensor is present)
        happens after every executed step, at spacing <= w/2 by construction.
        """
        if not route:
            return 0
        assert route[0] == self.current, f"route must start at current: {route[0]} != {self.current}"
        moved = 0
        for a, b in zip(route, route[1:]):
            assert b in self.graph.edges[a], f"Motion outside RCG: {a},{b}"
            assert self.map.feasible(a, b), "Motion through unknown/obstacle"
            cells = self.metric().path(a, b)
            for u, v in zip(cells, cells[1:]):
                self._check_deadline()
                self.refresh_retreat(u, v)
                self.path.append(v)
                self.modes.append(mode)
                moved += 1
                if self.sensor is not None:
                    self.sense(v)
            self.current = b
        return moved

    # -- Algorithm 1 -----------------------------------------------------
    def select_goal(self):
        p = self.current
        opened = [q for q in self.graph.edges[p] if self.graph.is_open(q)]
        groups = [("left", sorted(q for q in opened if q[0] < p[0])),
                  ("up", sorted(q for q in opened if q[0] == p[0] and q[1] > p[1])),
                  ("down", sorted(q for q in opened if q[0] == p[0] and q[1] < p[1])),
                  ("right", sorted(q for q in opened if q[0] > p[0]))]
        for name, group in groups:
            if group:
                goal = self.rng.choice(group)
                why = {"group": name, "order": ["left", "up", "down", "right"],
                       "options": [list(q) for q in group], "chosen": list(goal),
                       "seeded_choice": len(group) > 1}
                return goal, [p, goal], False, why
        self.refresh_retreat()
        candidates = sorted(self.retreat - {p})
        if candidates:
            routes = [self.graph.path(p, q) for q in candidates]
            route, _ = min(routes, key=lambda pair: (pair[1], pair[0][-1]))
            why = {"group": "retreat", "order": ["left", "up", "down", "right"],
                   "options": [list(q) for q in candidates], "chosen": list(route[-1]),
                   "rcg_path_cost": min(pair[1] for pair in routes)}
            return route[-1], route, True, why
        others = [q for q in self.graph.nodes if q != p and self.graph.is_open(q)]
        if others:
            raise ValueError(f"Open graph but no retreat nodes: {others[:5]}")
        self.graph.nodes[p].state = "Cl"
        why = {"group": "exhausted", "order": ["left", "up", "down", "right"],
               "options": [], "chosen": None, "open_nodes_left": 0}
        return None, None, False, why

    # -- coverage holes (III-B4d, Algorithm 3) ----------------------------
    def detect_holes(self, goal):
        candidates = {p for p in self.graph.nodes if self.graph.is_open(p)} - {self.current, goal}
        checked, holes = set(), set()
        for start in sorted(set(self.graph.edges[self.current]) & candidates):
            if start in checked:
                continue
            comp, stack = {start}, [start]
            while stack:
                p = stack.pop()
                for q in self.graph.edges[p]:
                    if q in candidates and q not in comp:
                        comp.add(q)
                        stack.append(q)
            checked.update(comp)
            if not any(self.map.unknown_adjacent(p) for p in comp):
                holes.update(comp)
        return holes

    def densify(self, holes, goal):
        points = set(holes) | {self.current, goal}
        additions = set()
        for p in sorted(points):
            for q in self.graph.edges[p]:
                if p[0] == q[0] and q in points:
                    additions.update(lap_points(p, q))
        new = additions - set(self.graph.nodes)
        for p in sorted(new):
            self.graph.insert(p, "tsp")
        self.graph.expand(new)
        return points | additions

    def cover_holes(self, holes, goal):
        start = self.current
        points = self.densify(holes, goal)

        def open_outside(p):
            return any(self.graph.is_open(q) and q not in points for q in self.graph.edges[p])

        retain_start = self.graph.is_open(start) and open_outside(start)
        if open_outside(goal) or self.map.unknown_adjacent(goal):
            end, case = goal, 1
        elif open_outside(start):
            end, case = start, 2
        else:
            end, case = None, 3
        paths, costs = {}, {}
        for a in sorted(points):
            for b in sorted(points):
                if (a, b) in paths:
                    continue
                path, cost = self.graph.path(a, b)
                paths[a, b] = path
                paths[b, a] = path[::-1]
                costs[a, b] = costs[b, a] = cost
        order, before, after = optimize_tsp(points, start, end, costs)
        event = dict(type="tsp", step=len(self.path) - 1, case=case,
                     targets=len(points), nn_length=before, opt_length=after,
                     hole_nodes=[list(p) for p in sorted(holes)],
                     dense_nodes=[list(p) for p in sorted(points)],
                     order=[list(p) for p in order], end=(list(end) if end is not None else None))
        self.events.append(event)
        moved = 0
        for a, b in zip(order, order[1:]):
            moved += self.navigate(paths[a, b], "tsp")
        for p in points:
            self.graph.nodes[p].state = "Cl"
        # Do not erase unresolved lap obligations at the entry and exit.
        if retain_start:
            self.graph.nodes[start].state = "Op"
        self.graph.nodes[self.current].state = "Op"
        self.refresh_retreat()
        event["moved_steps"] = moved
        return event

    # -- trace -----------------------------------------------------------
    def snapshot(self, iteration):
        snap = self.graph.snapshot()
        self.history.append(dict(iteration=iteration, step=len(self.path) - 1,
                                 nodes=snap["nodes"], edges=snap["edges"],
                                 known=len(self.map.free), retreat=len(self.retreat)))

    # -- Algorithm 4 -----------------------------------------------------
    def run(self, max_iterations=400):
        try:
            for i in range(max_iterations):
                self._check_deadline()
                self.iterations = i + 1
                new = self.graph.sample_front()
                self.register_new_retreats(new)
                self.graph.prune(self.current)
                self.graph.validate(self.current)
                self.refresh_retreat()
                self.snapshot(i)
                snap = self.history[-1]
                record = {
                    "iteration": i,
                    "step": len(self.path) - 1,
                    "known_free": len(self.map.free),
                    "new_samples": [list(p) for p in sorted(new)],
                    "node_count": len(snap["nodes"]),
                    "edge_count": len(snap["edges"]),
                    "nodes": snap["nodes"],
                    "edges": snap["edges"],
                    "retreat_count": len(self.retreat),
                }
                goal, route, is_retreat, why = self.select_goal()
                record["goal"] = list(goal) if goal is not None else None
                record["why"] = why
                record["retreat_used"] = bool(is_retreat)
                if goal is None:
                    self.status = "graph_exhausted"
                    record["move"] = None
                    record["path_steps"] = len(self.path) - 1
                    self.iterations_trace.append(record)
                    break
                record["state_update"] = self.graph.update_state(self.current, goal)
                if self.graph.is_open(self.current):
                    self.keep_open_count += 1
                holes = self.detect_holes(goal) if self.holes_enabled else set()
                record["holes"] = [list(p) for p in sorted(holes)]
                record["tsp"] = None
                if holes:
                    event = self.cover_holes(holes, goal)
                    record["tsp"] = event
                else:
                    if is_retreat:
                        self.retreat_count += 1
                        self.events.append(dict(type="retreat", step=len(self.path) - 1,
                                                goal=list(goal)))
                    # link insertion might split the originally selected edge.
                    if not is_retreat and goal not in self.graph.edges[self.current]:
                        route, _ = self.graph.path(self.current, goal)
                    before = len(self.path) - 1
                    self.navigate(route, "retreat" if is_retreat else "sweep")
                    record["move"] = {"mode": "retreat" if is_retreat else "sweep",
                                      "steps": (len(self.path) - 1) - before,
                                      "end": list(self.current)}
                record["path_steps"] = len(self.path) - 1
                self.iterations_trace.append(record)
            else:
                self.status = "iteration_limit"
        except WallClockCap as error:
            self.status = "wall_clock_cap"
            self.error = str(error)
            self._record_failure(error)
        except RCGCut as error:
            self.status = "rcg_disconnected"
            self.error = str(error)
            self.component_sizes = [len(c) for c in self.graph.components()] if self.graph.nodes else []
            self._record_failure(error)
        except (ValueError, AssertionError) as error:
            import traceback
            self.status = "invariant_failure"
            self.error = traceback.format_exc()
            self._record_failure(error)
        return self

    def _record_failure(self, error):
        record = {
            "iteration": self.iterations - 1 if self.iterations else 0,
            "step": len(self.path) - 1,
            "known_free": len(self.map.free),
            "node_count": len(self.graph.nodes),
            "edge_count": sum(len(v) for v in self.graph.edges.values()) // 2,
            "goal": None,
            "why": {"group": "failure", "options": [], "chosen": None,
                    "error": str(error)[:400]},
            "retreat_used": False,
            "holes": [],
            "tsp": None,
            "move": None,
            "path_steps": len(self.path) - 1,
        }
        self.iterations_trace.append(record)
