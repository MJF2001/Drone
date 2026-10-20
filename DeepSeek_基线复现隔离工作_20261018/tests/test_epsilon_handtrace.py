"""Hand-computable epsilon-star evidence.

The point of this module is not "the final route is legal" (that is checked
elsewhere) but that every hierarchical number and every state-machine choice can
be recomputed by hand on a 4x2 map.

Hand calculation for free = published targets = {(x,y): 0<=x<=3, 0<=y<=1},
ledger empty, current = (0,0), base = (0,0):

  bounding box        x0=0, x1=3, y0=0, y1=1
  exogenous field     B(x) = x1 - x + 1  =>  B(0)=4, B(1)=3, B(2)=2, B(3)=1
  halving of x        n=4 even -> 2+2 ; y: n=2 even -> 1+1 < 2? stop
                      so the root splits once along x into two 2x2 blocks
  max level           L = 1  (root at level 1, the two blocks at level 0)
  Eq. (2)             every cell unexplored -> E0 = B(x)
  Eq. (3) at L=1      pU = 1, mean B = (4+3+2+1)/4 = 2.5 -> E1 = 2.5
  start               the ETM credits the start cell (transit crediting), so
                      E0(0,0) becomes 0 and D0 excludes it
  Algorithm 1 step 1  D0 = the other seven cells; argmax E0 = 4 at (0,1)
  Algorithm 1 step 2  at (0,1): D0 = the six cells with x>=1; argmax E0 = 3 at
                      both (1,0) and (1,1), an equipotential pair
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(OUT / "src"))
sys.path.insert(0, str(HERE))

import bootstrap  # noqa: E402,F401
from problem import PlanRequest, Termination  # noqa: E402
from audit_independent import audit_route  # noqa: E402
from epsilon_core.maps import MAPS  # noqa: E402
from epsilon_core.etm import ETM  # noqa: E402

TRACE = OUT / "artifacts" / "epsilon_trace"


def toy_request():
    free = frozenset((x, y) for x in range(4) for y in range(2))
    return PlanRequest(case_id="toy_4x2", free=free, published_targets=free,
                       covered=frozenset(), current=(0, 0), base=(0, 0),
                       old_route=(), remaining_resource=200, seed=7,
                       termination=Termination(time_limit_seconds=10))


class HierarchyHandCheck(unittest.TestCase):
    def test_exogenous_field_and_levels(self):
        maps = MAPS(toy_request().free, toy_request().published_targets, frozenset())
        self.assertEqual((maps.x0, maps.x1, maps.y0, maps.y1), (0, 3, 0, 1))
        self.assertEqual(maps.bmax, 4)
        self.assertEqual([maps.B[x] for x in range(4)], [4, 3, 2, 1])
        self.assertEqual(maps.max_depth, 1)
        self.assertEqual(len(maps.nodes_by_level[1]), 1)   # the root
        self.assertEqual(len(maps.nodes_by_level[0]), 2)   # two 2x2 blocks

    def test_level0_potential_is_the_exogenous_field(self):
        request = toy_request()
        maps = MAPS(request.free, request.published_targets, frozenset())
        for x in range(4):
            for y in range(2):
                self.assertEqual(maps.E0[(x, y)], 4 - x)
                self.assertEqual(maps.state[(x, y)], "U")

    def test_coarse_potential_uses_probability_times_mean(self):
        request = toy_request()
        maps = MAPS(request.free, request.published_targets, frozenset())
        (root,) = maps.nodes_by_level[1]
        self.assertAlmostEqual(maps.E[1][root.key()], 2.5, places=9)
        # after crediting the whole left column both pU and the mean B drop
        maps.mark_covered((0, 0))
        maps.mark_covered((0, 1))
        maps.recompute_coarse()
        self.assertLess(maps.E[1][root.key()], 2.5)

    def test_directly_reachable_stops_at_an_obstacle(self):
        free = frozenset((x, y) for x in range(5) for y in range(3)) - {(3, 1)}
        targets = free
        maps = MAPS(free, targets, frozenset())
        candidates = {(1, 1), (2, 1), (3, 1), (4, 1), (0, 2)}
        reachable = maps.directly_reachable((0, 1), candidates)
        self.assertNotIn((3, 1), reachable)   # blocked cell itself
        self.assertNotIn((4, 1), reachable)   # behind the blocked cell
        self.assertIn((2, 1), reachable)


class StateMachineHandCheck(unittest.TestCase):
    def test_first_two_decisions_match_the_hand_calculation(self):
        request = toy_request()
        maps = MAPS(request.free, request.published_targets, frozenset())
        etm = ETM(maps, request.current, seed=7)
        self.assertEqual(etm.state, "CP0")
        # transit crediting already cleared the start cell
        self.assertEqual(maps.E0[(0, 0)], 0)
        wp, level, rule, _ = etm.choose_waypoint((0, 0))
        self.assertEqual(level, 0)
        self.assertEqual(rule, "line8_argmax_potential")
        self.assertEqual(wp, {(0, 1)})
        self.assertEqual(maps.E0[(0, 1)], 4)

        etm.move((0, 1))
        self.assertEqual(maps.E0[(0, 1)], 0)
        wp, level, rule, note = etm.choose_waypoint((0, 1))
        self.assertEqual(level, 0)
        self.assertEqual(rule, "line8_argmax_potential")
        self.assertEqual(wp, {(1, 0), (1, 1)})
        self.assertAlmostEqual(maps.E0[(1, 0)], 3)
        self.assertAlmostEqual(maps.E0[(1, 1)], 3)
        self.assertEqual(note["equipotential_size"], 2)

    def test_up_down_branch_and_task_branch_are_reachable(self):
        """Algorithm 1 lines 5 and 6, on a hand-built state."""
        free = frozenset({(0, 0), (0, 1), (0, 2), (0, 3), (1, 1)})
        targets = free
        request = PlanRequest(case_id="branch", free=free, published_targets=targets,
                              covered=frozenset(), current=(0, 1), base=(0, 0),
                              remaining_resource=100, seed=1,
                              termination=Termination(time_limit_seconds=5))
        maps = MAPS(free, targets, frozenset())
        etm = ETM(maps, (0, 1), seed=1, credit="waypoint")
        wp, level, rule, _ = etm.choose_waypoint((0, 1))
        self.assertEqual(rule, "line5_up_down_unexplored")
        self.assertEqual(wp, {(0, 2), (0, 0)})
        # with waypoint crediting the start cell is still unexplored, and if only
        # one vertical neighbour is unexplored line 6 asks the vehicle to task here
        maps2 = MAPS(free, targets, frozenset({(0, 2)}))
        etm2 = ETM(maps2, (0, 1), seed=1, credit="waypoint")
        wp, level, rule, _ = etm2.choose_waypoint((0, 1))
        self.assertEqual(rule, "line6_task_here")
        self.assertEqual(wp, {(0, 1)})

    def test_local_extremum_climbs_a_level_and_picks_a_random_fine_cell(self):
        """The escape uses a coarse level, and I(.) picks an unexplored fine cell."""
        free = frozenset((x, y) for x in range(9) for y in range(3))
        targets = free
        # every cell within the level-0 neighbourhood of (0,1) is explored, and the
        # only outstanding cells are far to the right, outside N^0(0,1)
        outstanding = {(8, 1), (8, 2)}
        covered = frozenset(free - outstanding)
        request = PlanRequest(case_id="escape", free=free, published_targets=targets,
                              covered=covered, current=(0, 1), base=(0, 0),
                              remaining_resource=100, seed=3,
                              termination=Termination(time_limit_seconds=5))
        maps = MAPS(free, targets, covered)
        # sanity: level 0 finds nothing, so the machine really is in an extremum
        etm = ETM(maps, (0, 1), seed=3, credit="waypoint")
        self.assertEqual(etm.computing_set(0, (0, 1)), [],
                         "level 0 must be empty for this to be a local extremum")
        wp, level, rule, note = etm.choose_waypoint((0, 1))
        self.assertGreaterEqual(level, 1, "should have climbed out of level 0")
        self.assertEqual(rule, "line16_random_unexplored_in_block")
        self.assertTrue(wp <= outstanding, f"escape waypoint must be a real pending cell: {wp}")

    def test_random_fine_cell_selection_is_not_nearest_first(self):
        """I(.) is a random choice inside the coarse cell, not a nearest-cell rule."""
        free = frozenset((x, y) for x in range(9) for y in range(3))
        targets = free
        outstanding = {(8, 1), (8, 2)}
        covered = frozenset(free - outstanding)
        chosen = set()
        for seed in range(40):
            maps = MAPS(free, targets, covered)
            etm = ETM(maps, (0, 1), seed=seed, credit="waypoint")
            wp, level, rule, _ = etm.choose_waypoint((0, 1))
            self.assertGreaterEqual(level, 1)
            chosen |= wp
        self.assertEqual(chosen, outstanding,
                         "both unexplored cells must be selectable; a nearest-first "
                         "rule would always return the same one")

    def test_trace_is_saved_for_review(self):
        TRACE.mkdir(parents=True, exist_ok=True)
        request = toy_request()
        maps = MAPS(request.free, request.published_targets, frozenset())
        etm = ETM(maps, request.current, seed=7)
        etm.run(max_steps=1000)
        etm.return_to_base(request.base)
        audit = audit_route(request, tuple(etm.route))
        payload = {
            "case_id": request.case_id,
            "hand_calculation": __doc__,
            "maps": maps.describe(),
            "initial_B": {f"{x}": maps.B[x] for x in range(maps.x0, maps.x1 + 1)},
            "decisions": [
                {"step": d.step, "lambda": list(d.lam), "level": d.level, "rule": d.rule,
                 "waypoint": list(d.waypoint), "potential": d.potential, "note": d.note}
                for d in etm.trace.decisions],
            "route": [list(p) for p in etm.route],
            "summary": etm.summary(),
            "audit": audit,
        }
        (TRACE / "toy_4x2_decisions.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertGreaterEqual(len(etm.trace.decisions), 4)


class CreditTimingEffect(unittest.TestCase):
    """The adaptation that matters most: move/task timing changes decisions."""

    def test_transit_crediting_suppresses_the_task_branch(self):
        request = toy_request()
        transit = ETM(MAPS(request.free, request.published_targets, frozenset()),
                      request.current, seed=7, credit="transit")
        transit.run(max_steps=1000)
        terminal_transit = transit.trace.terminal
        self.assertEqual(transit.trace.tasks, 0,
                         "with transit crediting the WT task branch cannot fire")
        waypoint = ETM(MAPS(request.free, request.published_targets, frozenset()),
                       request.current, seed=7, credit="waypoint")
        waypoint.run(max_steps=1000)
        self.assertGreater(waypoint.trace.tasks, 0,
                           "the diagnostic mode should still task at waypoints")
        self.assertNotEqual(terminal_transit, "", "transit run must record a terminal state")


if __name__ == "__main__":
    unittest.main(verbosity=2)
