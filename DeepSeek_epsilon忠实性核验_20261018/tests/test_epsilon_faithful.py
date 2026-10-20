"""Unit tests for the revised epsilon-star core.  No planner run is started.

"planner call" here means a full ``ETM.run`` over a map (what the ledger counts).
The tests below call construction helpers and single decision steps directly, so
they add nothing to the call ledger.

Run:  python -B -X utf8 -m unittest discover -s tests -p "test_*.py"
"""
import sys
import unittest
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from etm_faithful import ETM  # noqa: E402
from maps_faithful import (MAPS, build_tilings, check_partition,  # noqa: E402
                           segment_cells, split_sizes, splittable)


def rect(x0, y0, w, h):
    return {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}


class SplitRules(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(split_sizes(8), (4, 4))
        self.assertEqual(split_sizes(4), (2, 2))

    def test_odd_split_uses_n_prime_and_n_prime_minus_one(self):
        for n in (5, 7, 9, 13, 25):
            parts = split_sizes(n)
            self.assertEqual(sum(parts), n)
            self.assertEqual(2 * parts[0] - 1, n)

    def test_stopping_rule(self):
        self.assertFalse(splittable(2))
        self.assertTrue(splittable(4))
        self.assertFalse(splittable(3))
        self.assertTrue(splittable(5))
        self.assertFalse(splittable(1))


class Tiling(unittest.TestCase):
    CASES = {
        "4x4": ((0, 3, 0, 3), 1, {1: 4}),
        "8x8": ((0, 7, 0, 7), 2, {1: 16, 2: 4}),
        "6x4": ((0, 5, 0, 3), 1, {1: 4}),
        "9x3": ((0, 8, 0, 2), 2, {1: 4, 2: 2}),
        "5x5": ((0, 4, 0, 4), 1, {1: 4}),
        "7x5": ((0, 6, 0, 4), 2, {1: 6, 2: 4}),
    }

    def test_levels_and_counts_match_the_paper(self):
        for name, (box, expected_l, expected_counts) in self.CASES.items():
            with self.subTest(case=name):
                tilings, L = build_tilings(*box)
                self.assertEqual(L, expected_l)
                self.assertEqual({level: len(blocks) for level, blocks in tilings.items()},
                                 expected_counts)

    def test_every_tiling_is_a_partition(self):
        for name, (box, _, _) in self.CASES.items():
            with self.subTest(case=name):
                tilings, _ = build_tilings(*box)
                self.assertEqual(check_partition(tilings, *box), [])

    def test_the_whole_area_is_not_a_coarse_cell(self):
        for name, (box, _, _) in self.CASES.items():
            with self.subTest(case=name):
                tilings, _ = build_tilings(*box)
                whole = (box[0], box[1], box[2], box[3])
                for level, blocks in tilings.items():
                    self.assertNotIn(whole, [b.key() for b in blocks],
                                     f"level {level} contains the whole area")

    def test_coarsest_tiling_has_at_most_four_cells(self):
        for name, (box, _, counts) in self.CASES.items():
            with self.subTest(case=name):
                self.assertLessEqual(counts[max(counts)], 4)

    def test_two_by_two_level_exists_when_the_map_allows_it(self):
        tilings, _ = build_tilings(0, 7, 0, 7)
        self.assertEqual({(b.width, b.height) for b in tilings[1]}, {(2, 2)})


class Potentials(unittest.TestCase):
    def _maps(self, free, targets=None, covered=()):
        targets = free if targets is None else targets
        return MAPS(frozenset(free), frozenset(targets), frozenset(covered))

    def test_eq2_values(self):
        free = rect(0, 0, 4, 1) - {(2, 0)}            # a hole inside the box
        maps = self._maps(free, targets=free, covered={(0, 0)})
        self.assertEqual(maps.E0[(0, 0)], 0)          # explored
        self.assertEqual(maps.E0[(3, 0)], 1)          # unexplored, rightmost -> B=1
        self.assertEqual(maps.E0[(1, 0)], 3)          # B increases toward the left
        self.assertEqual(maps.E0[(2, 0)], -1)         # not free -> obstacle potential

    def test_eq3_is_mean_probability_times_mean_field(self):
        free = rect(0, 0, 4, 2)
        maps = self._maps(free, targets=free, covered={(0, 0), (1, 0)})
        level1 = maps.tilings[1][0]                   # a 2x2 block of the 4x2 map
        cells = list(level1.cells())
        expected = (2 / len(cells)) * (sum(maps.B[x] for x, _ in cells) / len(cells))
        self.assertAlmostEqual(maps.E[1][level1.key()], expected, places=12)

    def test_incremental_update_matches_a_full_rebuild(self):
        free = rect(0, 0, 6, 4)
        maps = self._maps(free, targets=free)
        target = sorted(maps.state)[5]
        maps.set_explored(target)
        for level in range(1, maps.L + 1):
            self.assertEqual(maps.E[level], maps._coarse_all(level))


class Neighbourhood(unittest.TestCase):
    def test_level0_is_seven_by_seven(self):
        free = rect(0, 0, 9, 9)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        hood = maps.neighbourhood0((4, 4))
        self.assertEqual(len(hood), 49)

    def test_level_neighbourhood_is_three_by_three_cells(self):
        free = rect(0, 0, 8, 8)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        hood = maps.neighbourhood((3, 3), 1)
        self.assertLessEqual(len(hood), 9)
        self.assertEqual({(b.width, b.height) for b in hood}, {(2, 2)})

    def test_strip_window_is_not_padded_by_the_long_side(self):
        free = rect(0, 0, 9, 3)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        block = next(b for b in maps.tilings[1] if b.x0 == 3)
        hood = maps.neighbourhood((block.x0, block.y0), 1)
        self.assertLessEqual(len(hood), 9)
        self.assertLess(len(hood), 4 + 1)      # the padded formula returns 4 here


class Reachability(unittest.TestCase):
    def test_a_cell_behind_a_wall_is_not_directly_reachable(self):
        free = rect(0, 0, 7, 3) - {(3, 1)}
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        self.assertEqual(maps._clear((2, 1), (4, 1)), False)
        self.assertEqual(maps._clear((2, 0), (4, 0)), True)

    def test_segment_touch_counts_every_cell(self):
        self.assertEqual(set(segment_cells((0, 0), (2, 0))), {(0, 0), (1, 0), (2, 0)})
        self.assertTrue({(0, 0), (1, 0), (0, 1), (1, 1)}.issubset(set(segment_cells((0, 0), (1, 1)))))


class Algorithm1Branches(unittest.TestCase):
    """The branch conditions, exercised without running the ETM loop."""

    def setUp(self):
        free = rect(0, 0, 4, 4)
        self.maps = MAPS(frozenset(free), frozenset(free), frozenset())
        self.etm = ETM(self.maps, (0, 0), seed=1, credit="task")

    def test_current_cell_unexplored_fires_line6(self):
        waypoint, level, rule, _ = self.etm.update_waypoint((0, 0))
        self.assertEqual((level, rule), (0, "line6_task_here"))

    def test_explored_cell_with_no_reachable_target_escalates(self):
        # an 8x8 map with a single remaining target at the far corner: it lies
        # outside the 7x7 window of (0,0), so D^0 is empty and the ETM must climb
        free = rect(0, 0, 8, 8)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        etm = ETM(maps, (0, 0), seed=1, credit="task")
        for cell in sorted(maps.state):
            if cell != (7, 7):
                maps.set_explored(cell)
        waypoint, level, rule, _ = etm.update_waypoint((0, 0))
        self.assertEqual(rule, "line16_I_unexplored_in_block")
        self.assertGreaterEqual(level, 1)
        self.assertEqual(next(iter(waypoint)), (7, 7))

    def test_transit_credit_makes_the_current_cell_explored(self):
        free = rect(0, 0, 4, 4)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        etm = ETM(maps, (0, 0), seed=1, credit="transit")
        # the previous adaptation credited the start cell in ST
        self.assertEqual(maps.E0[(0, 0)], 0)
        self.assertNotEqual(etm.update_waypoint((0, 0))[2], "line6_task_here")

    def test_algorithm1_line5_needs_both_vertical_neighbours(self):
        free = rect(0, 0, 4, 4)
        maps = MAPS(frozenset(free), frozenset(free), frozenset())
        etm = ETM(maps, (0, 0), seed=1, credit="task")
        maps.set_explored((0, 3))          # knock out "up" from D0
        maps.set_explored((0, 2))
        maps.set_explored((0, 1))
        waypoint, level, rule, _ = etm.update_waypoint((0, 0))
        self.assertEqual((level, rule), (0, "line6_task_here"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
