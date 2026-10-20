"""Pure structural tests: no solver, no ledger.

Covers the normalisation rules from A2 and the serialisation round trip, plus the
four known structure counterexamples from the earlier review (single-cell V, partial
V, connector passing over a future target, blocked connector).
"""
import json
import sys
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import native  # noqa: E402
from common_geometry import GridMetric  # noqa: E402


def line_metric(cells):
    return GridMetric(frozenset(map(tuple, cells)))


def plan_of(strips, start=(0, 0), end=(0, 0), free=None):
    free = free or [[x, y] for x in range(6) for y in range(4)]
    return native.build_plan("p", "M", 1, start, end, strips, line_metric(free))


class Structure(unittest.TestCase):
    def test_service_spans_match_the_strips(self):
        plan = plan_of([("r0", "H", [(0, 0), (1, 0), (2, 0)], False),
                        ("r1", "H", [(0, 2), (1, 2)], True)])
        for strip in plan.strips:
            span = plan.route[strip.service_start:strip.service_end + 1]
            ordered = (tuple(reversed(strip.cells)) if strip.reversed_direction
                       else tuple(strip.cells))
            self.assertEqual(span, ordered)
        self.assertEqual(plan.route[0], (0, 0))
        self.assertEqual(plan.route[-1], (0, 0))

    def test_single_cell_strip_keeps_its_axis(self):
        plan = plan_of([("v", "V", [(0, 1)], False)])
        strip = plan.strips[0]
        self.assertEqual(strip.axis, "V")
        self.assertEqual(plan.route[strip.service_start], (0, 1))

    def test_roundtrip_is_stable(self):
        plan = plan_of([("r0", "H", [(0, 0), (1, 0)], False)])
        again = native.NativePlan.from_dict(json.loads(native.dumps(plan)))
        self.assertEqual(native.dumps(plan), native.dumps(again))


class Normalisation(unittest.TestCase):
    def setUp(self):
        self.plan = plan_of([("h0", "H", [(0, 0), (1, 0), (2, 0)], False),
                             ("v0", "V", [(4, 0), (4, 1), (4, 2)], False)])
        self.execution = native.execute_prefix(self.plan, 2)

    def test_completed_strip_is_dropped(self):
        covered = set(self.execution.covered_physical) | {(4, 0), (4, 1), (4, 2)}
        remnants = native.normalize(self.plan, self.execution, covered,
                                    set(map(tuple, [(x, y) for x in range(6)
                                                    for y in range(4)])))
        reasons = {r.rank_id: r.reason for r in remnants}
        self.assertEqual(reasons["h0"], "completed")
        self.assertEqual(reasons["v0"], "completed")

    def test_partial_strip_keeps_ids_indices_and_axis(self):
        covered = {(0, 0)}
        free = {(x, y) for x in range(6) for y in range(4)}
        remnants = native.normalize(self.plan, self.execution, covered, free)
        h0 = next(r for r in remnants if r.rank_id == "h0")
        self.assertEqual(h0.axis, "H")
        self.assertEqual(h0.cells, ((1, 0), (2, 0)))
        self.assertEqual(h0.original_indices, (self.plan.strips[0].service_start + 1,
                                               self.plan.strips[0].service_start + 2))

    def test_vertical_remnant_stays_vertical_with_one_cell(self):
        covered = {(4, 0), (4, 1)}
        free = {(x, y) for x in range(6) for y in range(4)}
        remnants = native.normalize(self.plan, self.execution, covered, free)
        v0 = next(r for r in remnants if r.rank_id == "v0")
        self.assertEqual(v0.axis, "V")
        self.assertEqual(v0.cells, ((4, 2),))

    def test_middle_coverage_splits_the_strip(self):
        plan = plan_of([("h", "H", [(0, 0), (1, 0), (2, 0), (3, 0)], False)])
        free = {(x, y) for x in range(6) for y in range(4)}
        remnants = native.normalize(plan, native.execute_prefix(plan, 0), {(1, 0)}, free)
        ids = sorted(r.rank_id for r in remnants)
        self.assertEqual(ids, ["h", "h#1"])
        self.assertTrue(all(r.axis == "H" for r in remnants))
        self.assertTrue(all(r.reason == "split_by_coverage" for r in remnants))

    def test_connector_passing_a_future_target_updates_the_physical_ledger(self):
        # strip 0 ends at (2,0); the connector to strip 1 passes (3,0)
        plan = plan_of([("a", "H", [(0, 0), (1, 0), (2, 0)], False),
                        ("b", "H", [(4, 0), (5, 0)], False)])
        execution = native.execute_prefix(plan, len(plan.route) - 1 - 4)
        covered = set(execution.covered_physical)
        self.assertIn((3, 0), covered)          # passed, therefore covered
        free = {(x, y) for x in range(6) for y in range(4)}
        remnants = native.normalize(plan, execution, covered, free,
                                    targets_after={(4, 0), (5, 0)} | covered)
        self.assertTrue(all((3, 0) not in r.cells for r in remnants))

    def test_blocked_connector_cell_disappears_from_the_fragment(self):
        plan = plan_of([("a", "H", [(0, 0), (1, 0), (2, 0), (3, 0)], False)])
        free = {(x, y) for x in range(6) for y in range(4)} - {(2, 0)}
        remnants = native.normalize(plan, native.execute_prefix(plan, 0), set(), free)
        cells = [c for r in remnants for c in r.cells]
        self.assertNotIn((2, 0), cells)


class Events(unittest.TestCase):
    def test_obstacle_moves_a_target_to_deferred(self):
        state = native.event_state("e", [(0, 0), (1, 0)], [(0, 0), (1, 0)], set(),
                                   new_obstacles=[(1, 0)])
        self.assertEqual(state.pending, ((0, 0),))
        self.assertEqual(state.deferred, ((1, 0),))

    def test_new_target_is_not_retroactively_covered(self):
        state = native.event_state("e", [(0, 0)], [(0, 0), (1, 0)], {(0, 0)},
                                   new_targets=[(1, 0)])
        self.assertEqual(state.pending, ((1, 0),))
        self.assertEqual(state.deferred, ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
