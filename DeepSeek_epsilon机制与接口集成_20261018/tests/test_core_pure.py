"""Pure tests: no planner run, no ledger row, no cache file.

An independent, deliberately simple re-implementation of the tiling rule is used
here for the 4x4 and 8x8 cases (hand-written coordinates), so the core is not
validated by calling its own builder and agreeing with itself.
"""
import sys
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from core.maps import MAPS, build_tilings, check_partition  # noqa: E402
from core.etm import ETM  # noqa: E402
import inputs  # noqa: E402


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


class HierarchyCoordinates(unittest.TestCase):
    """Hand-written expectations: (x0, x1, y0, y1) per level."""

    def test_4x4_coarse_cells_exactly(self):
        tilings, L = build_tilings(0, 3, 0, 3)
        self.assertEqual(L, 1)
        got = sorted(b.key() for b in tilings[1])
        self.assertEqual(got, sorted([(0, 1, 0, 1), (0, 1, 2, 3),
                                      (2, 3, 0, 1), (2, 3, 2, 3)]))

    def test_8x8_level2_and_level1_exactly(self):
        tilings, L = build_tilings(0, 7, 0, 7)
        self.assertEqual(L, 2)
        self.assertEqual(sorted(b.key() for b in tilings[2]),
                         sorted([(0, 3, 0, 3), (0, 3, 4, 7),
                                 (4, 7, 0, 3), (4, 7, 4, 7)]))
        self.assertEqual(len(tilings[1]), 16)
        self.assertIn((0, 1, 0, 1), [b.key() for b in tilings[1]])

    def test_the_whole_area_is_never_a_coarse_cell(self):
        for box in ((0, 3, 0, 3), (0, 7, 0, 7), (0, 8, 0, 2), (0, 6, 0, 4)):
            tilings, _ = build_tilings(*box)
            whole = tuple(box)
            for blocks in tilings.values():
                self.assertNotIn(whole, [b.key() for b in blocks])

    def test_finest_coarse_level_exists_and_covers(self):
        for box in ((0, 7, 0, 7), (0, 8, 0, 2), (0, 6, 0, 4)):
            tilings, L = build_tilings(*box)
            self.assertEqual(check_partition(tilings, *box), [])
            self.assertLessEqual(max(b.width for b in tilings[1]), 3)
            self.assertLessEqual(max(b.height for b in tilings[1]), 3)


class Potentials(unittest.TestCase):
    def test_eq2_and_eq3(self):
        free = rect(0, 0, 4, 2)
        maps = MAPS(frozenset(free), frozenset(free), frozenset({(0, 0)}))
        self.assertEqual(maps.E0[(0, 0)], 0)
        self.assertEqual(maps.E0[(3, 0)], 1)
        block = maps.tilings[1][0]
        cells = list(block.cells())
        expected = (sum(1 for c in cells if c != (0, 0)) / len(cells)) * (
            sum(maps.B[x] for x, _ in cells) / len(cells))
        self.assertAlmostEqual(maps.E[1][block.key()], expected, places=12)

    def test_q_only_potential_does_not_change_the_block_mean_field(self):
        """The field B is geometric; only the unexplored fraction changes."""
        free = rect(0, 0, 4, 4)
        all_targets = MAPS(frozenset(free), frozenset(free), frozenset())
        few_targets = MAPS(frozenset(free), frozenset({(0, 0)}), frozenset())
        for level in all_targets.tilings:
            for block in all_targets.tilings[level]:
                mean_all = sum(all_targets.B[x] for x, _ in block.cells()) / len(
                    list(block.cells()))
                mean_few = sum(few_targets.B[x] for x, _ in block.cells()) / len(
                    list(block.cells()))
                self.assertAlmostEqual(mean_all, mean_few, places=12)

    def test_incremental_matches_full_rebuild(self):
        free = rect(0, 0, 6, 4)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        for cell in sorted(maps.state)[:5]:
            maps.set_explored(cell)
        for level in range(1, maps.L + 1):
            self.assertEqual(maps.E[level], maps._coarse_all(level))


class Neighbourhoods(unittest.TestCase):
    def test_level0_is_7x7_and_levels_are_3x3(self):
        free = rect(0, 0, 9, 9)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        self.assertEqual(len(maps.neighbourhood0((4, 4))), 49)
        for level in range(1, maps.L + 1):
            self.assertLessEqual(len(maps.neighbourhood((4, 4), level)), 9)

    def test_long_strip_window_is_not_padded(self):
        free = rect(0, 0, 9, 3)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        block = next(b for b in maps.tilings[1] if b.x0 == 3)
        pad = max(block.width, block.height)
        left, right = block.x0 - pad, block.x1 + pad
        padded = [other for other in maps.tilings[1]
                  if not (other.x1 < left or other.x0 > right)]
        self.assertLess(len(maps.neighbourhood((block.x0, block.y0), 1)), len(padded))


class Reachability(unittest.TestCase):
    def test_corner_grazing_is_blocked_by_the_supercover_rule(self):
        """A diagonal step past a blocked corner touches it; the paper's segment
        criterion and our stricter rule must both refuse it here."""
        free = rect(0, 0, 3, 3) - {(1, 0)}
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        self.assertFalse(maps._clear((0, 0), (1, 1)))
        self.assertTrue(maps._clear((0, 1), (1, 1)))


class Eq5(unittest.TestCase):
    def _engine(self, free, heading=None, turn_cost=1.0, travel_cost=1.0):
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        etm = ETM(maps, (0, 0), pending=frozenset(free), seed=1, credit="task",
                  travel_cost=travel_cost, turn_cost=turn_cost,
                  metric=__import__("common_geometry", fromlist=["GridMetric"]).GridMetric(frozenset(free)))
        etm.heading = heading
        return etm

    def test_equal_distance_prefers_straight_when_a_heading_exists(self):
        free = rect(0, 0, 3, 3)
        etm = self._engine(free, heading=(1, 0))
        chosen = etm.pick_cell({(0, 1), (2, 0)}, (1, 0))
        self.assertEqual(chosen, (2, 0))     # straight on, no turn

    def test_a_turn_costs_the_degrees(self):
        free = rect(0, 0, 3, 3)
        etm = self._engine(free, heading=(1, 0))
        # (2,0) is straight, (1,1) is 45 degrees: with turn_cost=1 the turn costs
        # 45 units, so the straight cell wins even though both are 1 step away
        chosen = etm.pick_cell({(1, 1), (2, 0)}, (1, 0))
        self.assertEqual(chosen, (2, 0))

    def test_without_a_heading_the_choice_is_by_distance_only(self):
        free = rect(0, 0, 4, 4)
        etm = self._engine(free, heading=None)
        chosen = etm.pick_cell({(3, 0), (1, 0)}, (0, 0))
        self.assertEqual(chosen, (1, 0))

    def test_ties_are_reproducible_with_the_same_seed(self):
        free = rect(0, 0, 3, 3)
        picks = []
        for _ in range(2):
            etm = self._engine(free, heading=None)
            picks.append(etm.pick_cell({(2, 0), (0, 2)}, (1, 1)))
        self.assertEqual(picks[0], picks[1])

    def test_zero_turn_cost_is_only_a_unit_counter_example(self):
        """With turn_cost=0 the two vertical candidates cost the same; the rule is
        still defined, it simply cannot express a preference.  This is a unit-level
        statement, not a claim about any particular map."""
        free = rect(0, 0, 3, 5)
        etm = self._engine(free, heading=(0, 1), turn_cost=0.0)
        up = etm.metric.distance((1, 2), (1, 3)) + 0.0
        down = etm.metric.distance((1, 2), (1, 1)) + 0.0
        self.assertEqual(up, down)


class InputWrapper(unittest.TestCase):
    def test_resource_zero_is_re_admitted_only_at_the_base_with_no_task(self):
        request = inputs.load_case("c09_empty_at_base", 20261018)
        verdict = inputs.validate_request(request)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["extension"], "resource_zero_empty_task_at_base")

    def test_resource_zero_with_a_task_is_still_rejected(self):
        request = inputs.load_case("c01_open4x4_interior", 20261018)
        broken = request.replaced(remaining_resource=0)
        verdict = inputs.validate_request(broken)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["code"], "nonpositive_resource")

    def test_bad_position_is_rejected_with_a_named_code(self):
        verdict = inputs.validate_request(inputs.load_case("c12_bad_input", 20261018))
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["code"], "current_not_free")


if __name__ == "__main__":
    unittest.main(verbosity=2)
