"""The Exploratory Turing Machine (ETM) of epsilon-star.

Source of the rules: `sources/literature/epsilon_star_author_preprint.txt`,
Section 3-B: Definition 3.1 (the 7-tuple), the state transition graph (Fig. 4),
Algorithm 1 (``Update wp(k)``), Eq. (4) (computing sets), Eq. (5) (waypoint
choice inside a candidate set), and the two Remark 3.3 / 3.2 obligations.

Machine states kept: ST, CP0..CPL, WT, FN.  A local extremum at level 0 climbs
the MAPS one level at a time, and the first level with a positive coarse
potential provides the waypoint by the function I(.), which selects an
*unexplored epsilon-cell inside that coarse cell uniformly at random* -- never
the nearest cell.

Two explicit model adaptations, both switchable and both recorded in
specs/epsilon_star_adaptation.md:

``credit="transit"`` (default, required by the current model)
    every traversed cell that is a pending target is credited immediately, so
    the ETM's MAPS and the real ledger stay identical.  Consequence: the WT
    "task here" branch (Algorithm 1 line 6) can no longer fire, because a cell
    reached is already explored.

``credit="waypoint"`` (diagnostic only, NOT the deliverable mode)
    the paper's move/task separation is simulated: the MAPS only credits the
    cell the ETM actually tasks.  Physical coverage is still recorded on every
    traversed cell for the auditor.  This mode exists to show what the original
    branching would do and to quantify the difference; it must never be reported
    as the adapted result.

The connector: Remark 3.3 allows any shortest-path method at higher levels and
the paper uses Bug2.  Because the executed motion must be four-neighbour on the
published free grid, every waypoint is realised through the common legal
connector ``src/common_geometry.GridMetric``; the candidate neighbourhood stays
the paper's large neighbourhood, and the four-neighbour action is defined
separately.
"""
import math
import random
from dataclasses import dataclass, field

from common_geometry import GridMetric


@dataclass
class Decision:
    step: int
    lam: tuple
    level: int
    rule: str
    waypoint: tuple
    potential: float
    note: str = ""


@dataclass
class Trace:
    decisions: list = field(default_factory=list)
    levels_used: dict = field(default_factory=dict)
    tasks: int = 0
    moves: int = 0
    extremum_escapes: int = 0
    terminal: str = ""
    failures: list = field(default_factory=list)

    def record(self, decision):
        self.decisions.append(decision)
        key = str(decision.level)
        self.levels_used[key] = self.levels_used.get(key, 0) + 1


class ETM:
    """Supervisor. One physical four-neighbour step per outer iteration."""

    def __init__(self, maps, current, seed=0, credit="transit",
                 travel_cost=1.0, turn_cost=0.0, metric=None):
        self.maps = maps
        self.current = tuple(current)
        self.rng = random.Random(seed)
        self.credit = credit
        self.travel_cost = float(travel_cost)
        self.turn_cost = float(turn_cost)
        self.metric = metric or GridMetric(maps.free)
        self.state = "ST"
        self.wp_previous = None          # the cell actually chosen last time
        self.heading = None              # (dx, dy) of the last physical move
        self.route = [self.current]
        self.physically_covered = set()
        self.trace = Trace()
        self.iterations = 0
        self.start()

    # ------------------------------------------------------------------ setup
    def start(self):
        """ST: all cells start unresolved, potentials come from B; then ip1."""
        self.state = "ST"
        self.credit_cell(self.current)
        self.state = "CP0"

    def credit_cell(self, p):
        if p not in self.maps.targets or p not in self.maps.free:
            return False
        fresh = p not in self.physically_covered
        self.physically_covered.add(p)
        if self.credit == "transit":
            changed = self.maps.mark_covered(p)
            if changed:
                self.maps.recompute_coarse()
            return changed
        return fresh

    # ------------------------------------------------------- Algorithm 1
    def computing_set(self, level, lam):
        hood = self.maps.neighbourhood(lam, level)
        if level == 0:
            positive = [q for q in hood if self.maps.E0.get(q, -1) > 0]
            reachable = self.maps.directly_reachable(lam, positive)
            return sorted(reachable)
        out = []
        for block in hood:
            if self.maps.E[level].get(block.key(), 0.0) > 0:
                out.append(block)
        return out

    def choose_waypoint_level0(self, lam):
        """Algorithm 1, lines 1-12."""
        candidates = self.computing_set(0, lam)
        d0 = set(candidates)
        if lam in d0:
            up = (lam[0], lam[1] + 1)
            down = (lam[0], lam[1] - 1)
            if up in d0 and down in d0:
                return {up, down}, "line5_up_down_unexplored", {}
            return {lam}, "line6_task_here", {}
        if d0:
            best = max(self.maps.E0[q] for q in d0)
            joint = {q for q in d0 if self.maps.E0[q] == best}
            return joint, "line8_argmax_potential", {"equipotential_size": len(joint)}
        if self.wp_previous is not None and self.maps.E0.get(self.wp_previous, -1) > 0:
            return {self.wp_previous}, "line10_keep_previous_waypoint", {}
        return set(), "line11_local_extremum", {}

    def choose_waypoint_level(self, level, lam):
        """Algorithm 1, lines 13-18, plus the I(.) random fine-cell selection."""
        if level not in self.maps.E:
            return None, "no_such_level", {}
        candidates = self.computing_set(level, lam)
        if not candidates:
            return None, "line17_empty_at_level", {}
        best = max(self.maps.E[level][b.key()] for b in candidates)
        chosen = [b for b in candidates if self.maps.E[level][b.key()] == best]
        block = chosen[0] if len(chosen) == 1 else self.rng.choice(sorted(chosen, key=lambda b: b.key()))
        inside = sorted(p for p in block.cells_inclusive
                        if self.maps.E0.get(p, 0) > 0)
        if not inside:
            return None, "line17_no_unexplored_cell_in_block", {"block": block.key()}
        cell = self.rng.choice(inside)
        return {cell}, "line16_random_unexplored_in_block", {
            "block": block.key(), "block_level": block.level,
            "positive_inside": len(inside), "equipotential_blocks": len(chosen)}

    def choose_waypoint(self, lam):
        """Full Algorithm 1 with the level-by-level escape of Fig. 4."""
        wp, rule, note = self.choose_waypoint_level0(lam)
        if wp:
            self.trace.record(Decision(self.iterations, lam, 0, rule,
                                       next(iter(sorted(wp))), self.maps.E0.get(lam, 0), str(note)))
            return wp, 0, rule, note
        for level in range(1, self.maps.max_depth + 1):
            wp, rule, note = self.choose_waypoint_level(level, lam)
            if wp:
                self.trace.extremum_escapes += 1
                cell = next(iter(wp))
                potential = self.maps.E[level].get(note.get("block"), 0.0) if note.get("block") else 0.0
                self.trace.record(Decision(self.iterations, lam, level, rule, cell,
                                           float(potential), str(note)))
                return wp, level, rule, note
        self.trace.record(Decision(self.iterations, lam, -1, "FN_no_positive_potential",
                                   lam, 0.0, ""))
        return set(), -1, "FN_no_positive_potential", {}

    # ------------------------------------------------- Eq. (5) cell choice
    def pick_cell(self, wp, lam):
        if len(wp) == 1:
            cell = next(iter(wp))
            self.wp_previous = cell
            return cell
        scored = []
        for q in sorted(wp):
            distance = self.metric.distance(lam, q)
            turn = 0.0
            if self.heading is not None:
                dx, dy = q[0] - lam[0], q[1] - lam[1]
                norm = math.hypot(dx, dy) or 1.0
                hx, hy = self.heading
                cosang = max(-1.0, min(1.0, (dx * hx + dy * hy) / norm))
                turn = math.degrees(math.acos(cosang))
            scored.append((distance * self.travel_cost + turn * self.turn_cost, q))
        best_cost = min(cost for cost, _ in scored)
        tied = [q for cost, q in scored if abs(cost - best_cost) < 1e-9]
        cell = tied[0] if len(tied) == 1 else self.rng.choice(tied)
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
        return self.credit_cell(next_cell)

    def run(self, max_steps=20000):
        """Algorithm 4's outer loop, one physical step per iteration."""
        seen = set()
        while True:
            self.iterations += 1
            if self.iterations > max_steps:
                self.trace.terminal = "step_limit"
                break
            if not any(self.maps.outstanding(p) for p in self.maps.targets):
                self.state = "FN"
                self.trace.terminal = "FN_no_unexplored_cell"
                break
            key = (self.current, len(self.physically_covered))
            if key in seen:
                self.trace.terminal = "state_cycle"
                self.trace.failures.append(f"repeated state {key}")
                break
            seen.add(key)

            wp, level, rule, note = self.choose_waypoint(self.current)
            if not wp:
                self.state = "FN"
                self.trace.terminal = "FN_no_positive_potential"
                break
            if level == 0 and rule == "line6_task_here":
                # WT: the ETM waits while the vehicle tasks the current cell.
                self.state = "WT"
                if self.current not in self.physically_covered or self.credit == "waypoint":
                    self.credit_cell(self.current)
                    self.trace.tasks += 1
                self.state = "CP0"
                continue
            target = self.pick_cell(wp, self.current)
            path = self.metric.path(self.current, target)
            if len(path) < 2:
                self.trace.failures.append(f"waypoint equal to current: {target}")
                self.trace.terminal = "no_progress"
                break
            self.move(path[1])
        self.finish()
        return self

    def finish(self):
        """The paper stops at FN; the current model requires a return to base."""
        self.return_to_base()

    def return_to_base(self, base=None):
        if base is None:
            return
        route = self.metric.path(self.current, tuple(base))
        for cell in route[1:]:
            self.move(cell)

    def summary(self):
        return {
            "terminal": self.trace.terminal,
            "iterations": self.iterations,
            "moves": self.trace.moves,
            "tasks": self.trace.tasks,
            "extremum_escapes": self.trace.extremum_escapes,
            "levels_used": self.trace.levels_used,
            "states_visited": self.train_states,
            "physically_covered": len(self.physically_covered),
            "steps": len(self.route) - 1,
            "credit_mode": self.credit,
            "failures": self.trace.failures[:8],
        }

    train_states = ("ST", "CP0", "WT", "FN")
