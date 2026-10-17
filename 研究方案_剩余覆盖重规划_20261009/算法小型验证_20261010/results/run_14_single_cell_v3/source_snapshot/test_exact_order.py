import unittest
from itertools import permutations
from exact_order import held_karp
from model import Geometry, DeadlineExceeded
from scenarios import build_case


class ExactOrderingTests(unittest.TestCase):
    def check_against_enumeration(self, start, between, end):
        n = len(start)
        def cost(order):
            return start[order[0]]+sum(between[a][b] for a,b in zip(order, order[1:]))+end[order[-1]]
        order, optimum = held_karp(start, between, end)
        self.assertEqual(sorted(order), list(range(n)))
        self.assertEqual(optimum, min(cost(p) for p in permutations(range(n))))
        self.assertEqual(cost(order), optimum)

    def test_general_small_matrices_match_all_permutations(self):
        for n in range(1, 8):
            start = [3+(i*7)%11 for i in range(n)]
            end = [2+(i*3)%7 for i in range(n)]
            between = [[0 if i == j else 1+(i*5+j*7)%13 for j in range(n)] for i in range(n)]
            self.check_against_enumeration(start, between, end)

    def test_obstacle_distances_match_enumeration(self):
        s, _ = build_case(18, 6, .5, 'channel_obstacle')
        g = Geometry(s)
        points = sorted(g.reachable)[::max(1, len(g.reachable)//6)][:6]
        self.check_against_enumeration([g.distance(s.current, p) for p in points],
            [[g.distance(p,q) for q in points] for p in points],
            [g.distance(p,s.base) for p in points])

    def test_empty_pool_and_repeated_coordinates(self):
        self.assertEqual(held_karp([], [], [], empty_cost=7), ([], 7))
        self.check_against_enumeration([0, 0], [[0, 0], [0, 0]], [4, 4])

    def test_size_limit_and_deadline_do_not_claim_optimal(self):
        with self.assertRaises(ValueError):
            held_karp([0]*15, [[0]*15 for _ in range(15)], [0]*15)
        def expired():
            raise DeadlineExceeded()
        with self.assertRaises(DeadlineExceeded):
            held_karp([1], [[0]], [1], expired)


if __name__ == '__main__':
    unittest.main(verbosity=2)
