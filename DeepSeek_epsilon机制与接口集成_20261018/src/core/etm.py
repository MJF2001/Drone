"""The ETM, integrated for this round.

Rules come from Section 3-B of the author preprint; the clause-by-clause mapping
lives in ``reports/原文机制与场景适配对应表.md``.  Compared with the mechanism
reference version this file adds only *observation*, not decisions:

* event indices and event times on the same clock as the public call
  (``index_first_physical_complete``, ``index_control_fn``, ``index_return_start``,
  ``index_return_end``) so the two ledgers can be compared afterwards;
* a deadline check *after* every connector call, not only before it;
* connector statistics (path calls, cache hits, BFS row builds) taken from the
  connector's own counters, so "one call" is never confused with "one BFS".

The control ledger and the physical ledger remain separate:

``control``
    the MAPS state.  A cell stays ``U`` until the ETM tasks it in WT.  ``U`` means
    *control-pending*, not *not physically collected*.
``physical``
    what the route has actually visited.  The independent auditor recomputes it;
    ``move`` also records it here so the events can be indexed.

No decision rule was changed in this file.
"""
import math
import random
from dataclasses import dataclass, field

from common_geometry import GridMetric


@dataclass
class Decision:
    step: int
    state: str
    level: int
    rule: str
    lam: tuple
    lam_potential: float
    waypoint_set: tuple
    chosen: tuple
    note: str = ""
    block: tuple = ()
    block_level: int = -1
    positive_inside: int = 0
    candidate_blocks: int = 0


@dataclass
class Trace:
    decisions: list = field(default_factory=list)
    rules: dict = field(default_factory=dict)
    levels_used: dict = field(default_factory=dict)
    tasks: int = 0
    moves: int = 0
    extremum_escapes: int = 0
    terminal: str = ""
    failures: list = field(default_factory=list)

    def record(self, decision):
        self.decisions.append(decision)
        self.rules[decision.rule] = self.rules.get(decision.rule, 0) + 1
        key = str(decision.level)
        self.levels_used[key] = self.levels_used.get(key, 0) + 1


class ETM:
    """One physical four-neighbour step per outer iteration."""

    def __init__(self, maps, current, pending, seed=0, credit="task", travel_cost=1.0,
                 turn_cost=1.0, metric=None, deadline=None, time_source=None,
                 max_steps=20000):
        self.maps = maps
        self.current = tuple(current)
        self.pending = frozenset(pending)
        self.rng = random.Random(seed)
        self.credit = credit
        self.travel_cost = float(travel_cost)
        self.turn_cost = float(turn_cost)
        self.metric = metric or GridMetric(maps.free)
        self.deadline = deadline
        self.time_source = time_source or (lambda: 0.0)
        self.max_steps = int(max_steps)
        self.state = "ST"
        self.wp_previous = None
        self.heading = None
        self.route = [self.current]
        self.physically_covered = set()
        self.tasked = set()
        self.trace = Trace()
        self.iterations = 0
        self.events = {
            "index_first_physical_complete": None,
            "time_first_physical_complete": None,
            "index_control_fn": None,
            "time_control_fn": None,
            "index_return_start": None,
            "index_return_end": None,
            "time_return_end": None,
            "extra_steps_physical_to_fn": None,
            "return_steps": None,
            "control_tasked": 0,
            "decision_count": 0,
        }
        self.start()

    # ------------------------------------------------------------------ setup
    def start(self):
        """ST: MAPS initialised with every cell U; ``wp = lambda``; nothing tasked."""
        self.state = "ST"
        self.wp_previous = self.current
        if self.credit == "transit":
            self._mark(self.current)
        self.state = "CP0"
        if not self.pending:
            self.events["index_first_physical_complete"] = 0
            self.events["time_first_physical_complete"] = self.time_source()

    def _mark(self, p):
        if p not in self.maps.targets or p not in self.maps.free:
            return False
        return self.maps.set_explored(p)

    def _tick(self):
        if self.deadline is not None:
            self.deadline.check()

    def _physical_complete(self):
        covered = set(self.maps.covered) | self.physically_covered | set(self.route)
        return self.pending <= covered

    # ------------------------------------------------------- Algorithm 1
    def computing_set(self, level, lam):
        hood = self.maps.neighbourhood(lam, level)
        if level == 0:
            positive = [q for q in hood if self.maps.E0.get(q, -1) > 0]
            return sorted(self.maps.directly_reachable(lam, positive))
        return [block for block in hood
                if self.maps.E[level].get(block.key(), 0.0) > 0]

    def update_waypoint(self, lam):
        """Algorithm 1 lines 1-18: (set, level, rule, note, block info)."""
        d0 = self.computing_set(0, lam)
        info = {"block": (), "block_level": -1, "positive_inside": 0,
                "candidate_blocks": 0}
        if lam in d0:
            up = (lam[0], lam[1] + 1)
            down = (lam[0], lam[1] - 1)
            if up in d0 and down in d0:
                return {up, down}, 0, "line5_up_down_unexplored", {"D0": len(d0)}, info
            return {lam}, 0, "line6_task_here", {"D0": len(d0)}, info
        if d0:
            best = max(self.maps.E0[q] for q in d0)
            joint = {q for q in d0 if self.maps.E0[q] == best}
            return joint, 0, "line8_argmax_potential", {"D0": len(d0),
                                                       "equipotential": len(joint)}, info
        if self.wp_previous is not None and self.maps.E0.get(self.wp_previous, -1) > 0:
            return {self.wp_previous}, 0, "line10_keep_previous_waypoint", {}, info
        for level in range(1, self.maps.L + 1):
            candidates = self.computing_set(level, lam)
            if not candidates:
                continue
            best = max(self.maps.E[level][b.key()] for b in candidates)
            joint = [b for b in candidates if abs(self.maps.E[level][b.key()] - best) < 1e-12]
            block = joint[0] if len(joint) == 1 else self.rng.choice(
                sorted(joint, key=lambda b: b.key()))
            inside = sorted(p for p in block.cells() if self.maps.E0.get(p, 0) > 0)
            if not inside:
                continue
            cell = self.rng.choice(inside)
            info = {"block": block.key(), "block_level": block.level,
                    "positive_inside": len(inside),
                    "candidate_blocks": len(candidates)}
            return {cell}, level, "line16_I_unexplored_in_block", {
                "block": block.key(), "block_level": block.level,
                "positive_inside": len(inside), "D_level": len(candidates),
                "equipotential_blocks": len(joint)}, info
        return set(), -1, "FN_no_positive_potential", {}, info

    def pick_cell(self, waypoint_set, lam):
        if len(waypoint_set) == 1:
            cell = next(iter(waypoint_set))
            self.wp_previous = cell
            return cell
        scored = []
        for q in sorted(waypoint_set):
            distance = self.metric.distance(lam, q)
            turn = 0.0
            if self.heading is not None and self.turn_cost:
                dx, dy = q[0] - lam[0], q[1] - lam[1]
                norm = math.hypot(dx, dy) or 1.0
                hx, hy = self.heading
                cos = max(-1.0, min(1.0, (dx * hx + dy * hy) / norm))
                turn = math.degrees(math.acos(cos))
            scored.append((distance * self.travel_cost + turn * self.turn_cost, q))
        best = min(cost for cost, _ in scored)
        tied = [q for cost, q in scored if abs(cost - best) < 1e-9]
        cell = tied[0] if len(tied) == 1 else self.rng.choice(sorted(tied))
        self.wp_previous = cell
        return cell

    # ------------------------------------------------------------- execution
    def move(self, next_cell):
        if abs(next_cell[0] - self.current[0]) + abs(next_cell[1] - self.current[1]) != 1:
            raise ValueError(f"non four-neighbour move {self.current} -> {next_cell}")
        self.heading = (next_cell[0] - self.current[0], next_cell[1] - self.current[1])
        self.current = next_cell
        self.route.append(next_cell)
        self.trace.moves += 1
        if self.current in self.maps.targets and self.current in self.maps.free:
            self.physically_covered.add(self.current)
        if self.credit == "transit":
            self._mark(self.current)
        if (self.events["index_first_physical_complete"] is None
                and self._physical_complete()):
            self.events["index_first_physical_complete"] = len(self.route) - 1
            self.events["time_first_physical_complete"] = self.time_source()

    def run(self):
        seen = set()
        while True:
            self._tick()
            self.iterations += 1
            if self.iterations > self.max_steps:
                self.trace.terminal = "step_limit"
                self.trace.failures.append("artificial control-iteration cap reached")
                break
            key = (self.current, self.wp_previous, self.heading,
                   len(self.tasked), len(self.physically_covered))
            if key in seen:
                self.trace.terminal = "state_cycle"
                self.trace.failures.append(
                    "artificial safety truncation: repeat of a key that does NOT "
                    f"include the RNG state: {key}")
                break
            seen.add(key)

            lam = self.current
            waypoint_set, level, rule, note, info = self.update_waypoint(lam)
            self.trace.record(Decision(
                self.iterations, self.state, level, rule, lam,
                float(self.maps.E0.get(lam, -1.0)), tuple(sorted(waypoint_set)),
                tuple(sorted(waypoint_set))[0] if waypoint_set else (),
                str(note), tuple(info["block"]), int(info["block_level"]),
                int(info["positive_inside"]), int(info["candidate_blocks"])))

            if not waypoint_set:
                self.state = "FN"
                self.trace.terminal = "FN_no_positive_potential"
                self.events["index_control_fn"] = len(self.route) - 1
                self.events["time_control_fn"] = self.time_source()
                break

            if level == 0 and rule == "line6_task_here":
                self.state = "WT"
                self.tasked.add(lam)
                self.trace.tasks += 1
                self._mark(lam)
                self.state = "CP0"
                continue

            if level >= 1:
                self.trace.extremum_escapes += 1
            target = self.pick_cell(waypoint_set, lam)
            self._tick()
            path = self.metric.path(lam, target)
            self._tick()                       # the connector may itself overrun
            if len(path) < 2:
                self.trace.failures.append(f"waypoint equal to current: {target}")
                self.trace.terminal = "no_progress"
                break
            self.move(path[1])

        self.events["control_tasked"] = len(self.tasked)
        self.events["decision_count"] = len(self.trace.decisions)
        if (self.events["index_control_fn"] is not None
                and self.events["index_first_physical_complete"] is not None):
            self.events["extra_steps_physical_to_fn"] = (
                self.events["index_control_fn"]
                - self.events["index_first_physical_complete"])
        self.state = "FN" if self.trace.terminal.startswith("FN") else self.state
        return self

    # -------------------------------------------------------------- finishing
    def return_to_base(self, base=None):
        if base is None:
            return
        self._tick()
        self.events["index_return_start"] = len(self.route) - 1
        route = self.metric.path(self.current, tuple(base))
        self._tick()
        for cell in route[1:]:
            self._tick()
            self.move(cell)
        self.events["index_return_end"] = len(self.route) - 1
        self.events["time_return_end"] = self.time_source()
        self.events["return_steps"] = len(route) - 1

    def connector_stats(self):
        metric = self.metric
        return {"row_builds": getattr(metric, "builds", None),
                "cached_paths": len(getattr(metric, "_paths", {})),
                "cached_rows": len(getattr(metric, "_rows", {}))}

    def summary(self):
        return {
            "terminal": self.trace.terminal,
            "credit_mode": self.credit,
            "iterations": self.iterations,
            "moves": self.trace.moves,
            "tasks": self.trace.tasks,
            "extremum_escapes": self.trace.extremum_escapes,
            "levels_used": dict(sorted(self.trace.levels_used.items(),
                                       key=lambda kv: int(kv[0]))),
            "rules": dict(sorted(self.trace.rules.items())),
            "physically_covered_targets": len(self.physically_covered),
            "control_tasked_targets": len(self.tasked),
            "steps": len(self.route) - 1,
            "events": dict(self.events),
            "connector": self.connector_stats(),
            "turn_cost": self.turn_cost,
            "travel_cost": self.travel_cost,
            "initial_heading": None,
            "failures": self.trace.failures[:6],
            "decisions": [{"step": d.step, "state": d.state, "level": d.level,
                            "rule": d.rule, "lam": list(d.lam),
                            "lam_potential": d.lam_potential,
                            "waypoint_set": [list(p) for p in d.waypoint_set],
                            "chosen": list(d.chosen), "note": d.note,
                            "block": list(d.block), "block_level": d.block_level,
                            "positive_inside": d.positive_inside,
                            "candidate_blocks": d.candidate_blocks}
                           for d in self.trace.decisions],
        }
