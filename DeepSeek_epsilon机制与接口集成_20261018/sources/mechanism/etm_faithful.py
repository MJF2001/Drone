"""The ETM, rebuilt against Section 3-B of the author preprint.

State machine (paper, Fig. 4 and Section 3-B)::

    ST -> CP0 <-> WT
           ^  |
           |  v
          CP1 -> CP2 -> ... -> CPL -> FN

    "In each iteration of state CP0 ... i) reads the potentials from the local
     neighborhood N^0(lambda) of lambda to compute the new waypoint, ii) changes
     the head state to WT if waypoint is reached otherwise stays in CP0 ...
     If the head gets stuck in a local extremum ... then it switches to CP1 ...
     If no waypoint is found even at the highest level then the ETM halts in
     state FN and the coverage is complete."

Two credit modes, selected explicitly and recorded in every trace:

``credit="task"`` (default, paper semantics)
    The MAPS only learns that a cell is explored when the ETM *tasks* it, i.e. in
    WT ("the ETM waits while the vehicle performs task at lambda ... the ETM
    updates the state of the current cell to E").  Traversal alone changes
    nothing in the MAPS.  Adaptive consequence of this project's user model: the
    vehicle reports the task as complete at once for a cell it is standing on, so
    WT never blocks -- but the decision "task here, or move first" is still taken
    by the ETM exactly as in Algorithm 1 lines 3-6.

``credit="transit"`` (the previous adaptation, kept for comparison only)
    Every traversed pending target is credited immediately.  Then lambda always
    has potential 0 at CP0, so ``lambda in D^0`` is never true and Algorithm 1
    lines 3-6 can never fire.  The step traces show this directly; it is why this
    mode is no longer the deliverable mode.
"""
import math
import random
from dataclasses import dataclass, field

from common_geometry import GridMetric

MODES = ("task", "transit")


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

    def __init__(self, maps, current, seed=0, credit="task", travel_cost=1.0,
                 turn_cost=1.0, metric=None, deadline=None, neighbourhood_probe=False):
        if credit not in MODES:
            raise ValueError(f"credit mode must be one of {MODES}")
        self.maps = maps
        self.current = tuple(current)
        self.rng = random.Random(seed)
        self.credit = credit
        self.travel_cost = float(travel_cost)
        self.turn_cost = float(turn_cost)
        self.metric = metric or GridMetric(maps.free)
        self.deadline = deadline
        self.state = "ST"
        self.wp_previous = None
        self.heading = None
        self.route = [self.current]
        self.physically_covered = set()
        self.tasked = set()
        self.trace = Trace()
        self.iterations = 0
        self.keep_recording = bool(neighbourhood_probe)
        self.start()

    # ------------------------------------------------------------------ setup
    def start(self):
        """ST: MAPS is initialised with every cell U; ``wp = lambda``.

        Paper: "the ETM ... initializes the waypoint wp = lambda.  Then it updates
        the symbolic encoding ... Then the ETM transitions to the computing state
        q = CP0".  Nothing is tasked here, so nothing is marked explored.
        """
        self.state = "ST"
        self.wp_previous = self.current
        if self.credit == "transit":
            # previous adaptation started by crediting the start cell; kept only
            # so the old behaviour can be reproduced for comparison
            self._mark(self.current)
        self.state = "CP0"

    def _mark(self, p):
        if p not in self.maps.targets or p not in self.maps.free:
            return False
        return self.maps.set_explored(p)

    # ------------------------------------------------------- Algorithm 1
    def computing_set(self, level, lam):
        """Eq. (4): D^0 needs positive potential AND direct reachability; D^l, l>=1,
        only needs a positive coarse potential."""
        hood = self.maps.neighbourhood(lam, level)
        if level == 0:
            positive = [q for q in hood if self.maps.E0.get(q, -1) > 0]
            return sorted(self.maps.directly_reachable(lam, positive))
        return [block for block in hood
                if self.maps.E[level].get(block.key(), 0.0) > 0]

    def update_waypoint(self, lam):
        """Algorithm 1, lines 1-18.  Returns (set, level, rule, note)."""
        d0 = self.computing_set(0, lam)
        potential = self.maps.E0.get(lam, -1.0)
        if lam in d0:                                   # line 3
            up = (lam[0], lam[1] + 1)
            down = (lam[0], lam[1] - 1)
            if up in d0 and down in d0:                 # line 4
                return {up, down}, 0, "line5_up_down_unexplored", {"D0": len(d0)}
            return {lam}, 0, "line6_task_here", {"D0": len(d0)}       # line 6
        if d0:                                          # line 7
            best = max(self.maps.E0[q] for q in d0)
            joint = {q for q in d0 if self.maps.E0[q] == best}
            return joint, 0, "line8_argmax_potential", {"D0": len(d0),
                                                       "equipotential": len(joint)}
        if self.wp_previous is not None and self.maps.E0.get(self.wp_previous, -1) > 0:
            return {self.wp_previous}, 0, "line10_keep_previous_waypoint", {}   # line 10
        # lines 11-18: local extremum, climb the MAPS one level at a time
        for level in range(1, self.maps.L + 1):
            candidates = self.computing_set(level, lam)
            if not candidates:
                continue
            best = max(self.maps.E[level][b.key()] for b in candidates)
            joint = [b for b in candidates if abs(self.maps.E[level][b.key()] - best) < 1e-12]
            block = joint[0] if len(joint) == 1 else self.rng.choice(
                sorted(joint, key=lambda b: b.key()))
            inside = sorted(p for p in block.cells() if self.maps.E0.get(p, 0) > 0)
            if not inside:                              # line 17, information gap
                continue
            cell = self.rng.choice(inside)              # line 16, I(.)
            return {cell}, level, "line16_I_unexplored_in_block", {
                "block": block.key(), "block_level": block.level,
                "positive_inside": len(inside), "D_level": len(candidates),
                "equipotential_blocks": len(joint)}
        return set(), -1, "FN_no_positive_potential", {}                 # line 17 at L
        _ = potential

    # --------------------------------------------------- Eq. (5) cell choice
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

    def _tick(self):
        if self.deadline is not None:
            self.deadline.check()

    # ------------------------------------------------------------------ loop
    def run(self, max_steps=20000):
        seen = set()
        while True:
            self._tick()
            self.iterations += 1
            if self.iterations > max_steps:
                self.trace.terminal = "step_limit"
                self.trace.failures.append("artificial step cap reached")
                break
            key = (self.current, self.wp_previous, self.heading,
                   len(self.tasked), len(self.physically_covered))
            if key in seen:
                self.trace.terminal = "state_cycle"
                self.trace.failures.append(f"artificial safety truncation: key repeated {key}")
                break
            seen.add(key)

            lam = self.current
            waypoint_set, level, rule, note = self.update_waypoint(lam)
            record = Decision(self.iterations, self.state, level, rule, lam,
                              float(self.maps.E0.get(lam, -1.0)),
                              tuple(sorted(waypoint_set)),
                              tuple(sorted(waypoint_set))[0] if waypoint_set else (),
                              str(note))
            self.trace.record(record)

            if not waypoint_set:
                self.state = "FN"
                self.trace.terminal = "FN_no_positive_potential"
                break

            if level == 0 and rule == "line6_task_here":
                # WT: the vehicle tasks at lambda; the ETM then sets it to E
                self.state = "WT"
                self.tasked.add(lam)
                self.trace.tasks += 1
                self._mark(lam)
                self.state = "CP0"
                continue

            if level >= 1:
                self.trace.extremum_escapes += 1
            target = self.pick_cell(waypoint_set, lam)
            record.chosen = target
            self._tick()
            path = self.metric.path(lam, target)
            if len(path) < 2:
                self.trace.failures.append(f"waypoint equal to current: {target}")
                self.trace.terminal = "no_progress"
                break
            self.move(path[1])

        self.state = "FN" if self.trace.terminal.startswith("FN") else self.state
        return self

    # -------------------------------------------------------------- finishing
    def return_to_base(self, base=None, deadline=None):
        if base is None:
            return
        limit = deadline or self.deadline
        self._tick()
        route = self.metric.path(self.current, tuple(base))
        for cell in route[1:]:
            if limit is not None:
                limit.check()
            self.move(cell)

    def summary(self):
        return {
            "terminal": self.trace.terminal,
            "credit_mode": self.credit,
            "iterations": self.iterations,
            "moves": self.trace.moves,
            "tasks": self.trace.tasks,
            "extremum_escapes": self.trace.extremum_escapes,
            "levels_used": dict(sorted(self.trace.levels_used.items(), key=lambda kv: int(kv[0]))),
            "rules": dict(sorted(self.trace.rules.items())),
            "physically_covered_targets": len(self.physically_covered),
            "tasked_targets": len(self.tasked),
            "steps": len(self.route) - 1,
            "failures": self.trace.failures[:6],
        }
