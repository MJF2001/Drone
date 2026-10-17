import itertools
import random
import time
import unittest
from dataclasses import replace
import oarp_replan
from oarp_replan.ranks import Rank, partition, metrics, rank_replan, enumerate_oracle
from oarp_replan.tour import OldService, path_sets, old_services, tour_replan, exact_gtsp
from model import Snapshot, Geometry
from audit import audit
from oarp_replan.adapter import solve_core
from oarp_replan.budget import cap_for_time


class RankTests(unittest.TestCase):
    def test_all_small_shapes_both_models_and_budgets(self):
        base = [(x,y) for x in range(3) for y in range(2)]
        old = partition(base,{p:'H' for p in base})
        checked = 0
        for mask in range(1,1<<len(base)):
            cells = {p for k,p in enumerate(base) if mask>>k & 1}
            for variant in (1,2):
                for cap in (0,1,2,6):
                    expected = enumerate_oracle(cells,old,cap,variant)
                    actual = rank_replan(cells,old,cap,variant)
                    if expected is None:
                        self.assertIsNone(actual['ranks'], (cells,variant,cap,actual))
                        self.assertEqual(actual['status'],'infeasible')
                    else:
                        self.assertIsNotNone(actual['ranks'], (cells,variant,cap,actual))
                        self.assertEqual(actual['status'],'optimal')
                        self.assertAlmostEqual(actual['objective'],expected['objective'])
                    checked += 1
        self.assertEqual(checked,504)

    def test_initial_rank_partition_known_optima(self):
        for cells, count in [({(x,0) for x in range(4)},1),
            ({(x,y) for x in range(2) for y in range(2)},2),
            ({(0,1),(1,0),(1,1),(1,2),(2,1)},3)]:
            r = rank_replan(cells,variant=0)
            self.assertEqual(r['metrics']['rank_count'],count)

    def test_no_silent_fractional_rounding_and_zero_budget(self):
        old = (Rank('H',((0,0),(1,0),(2,0))),)
        self.assertEqual(rank_replan({(0,0),(2,0)},old,cap=0)['status'],'infeasible')
        r = rank_replan({(0,0),(2,0)},old,cap=2)
        self.assertEqual(r['metrics']['new_rank_count'],2)

    def test_expansion_and_empty_targets(self):
        old = (Rank('H',((0,0),(1,0))),)
        for variant in (1,2):
            r = rank_replan({(0,0),(1,0),(2,0)},old,cap=2,variant=variant)
            self.assertEqual(r['metrics']['new_rank_count'],1)
        self.assertEqual(rank_replan(set())['ranks'],())

    def test_mixed_old_orientations_and_expansions_match_oracle(self):
        rng = random.Random(231117837)
        base = {(x,y) for x in range(3) for y in range(3)}
        for trial in range(12):
            old = partition(base,{p:rng.choice(('H','V')) for p in sorted(base)})
            cells = {p for p in sorted(base) if rng.random() > .3} | {(3,1)}
            for variant in (1,2):
                for cap in (2,12):
                    oracle = enumerate_oracle(cells,old,cap,variant)
                    actual = rank_replan(cells,old,cap,variant)
                    if oracle is None:
                        self.assertIsNone(actual['ranks'])
                    else:
                        self.assertAlmostEqual(actual['objective'],oracle['objective'])

    def test_invalid_unstrengthened_solution_is_rejected_and_repair_labeled(self):
        import json
        from pathlib import Path
        fixture = json.loads((Path(__file__).parent/'oarp_replan/decoder_counterexample.json').read_text())
        cells = set(map(tuple,fixture['cells']))
        old = tuple(Rank(r['axis'],tuple(map(tuple,r['cells']))) for r in fixture['old'])
        strict = rank_replan(cells,old,2,1,allow_certification_repair=False)
        self.assertEqual(strict['status'],'invalid_original_model_solution')
        fixed = rank_replan(cells,old,2,1)
        oracle = enumerate_oracle(cells,old,2,1)
        self.assertTrue(fixed['certification_repair'])
        self.assertAlmostEqual(fixed['objective'],oracle['objective'])


class TourTests(unittest.TestCase):
    def test_packet_keeps_internal_path_and_breaks_blocked_connector(self):
        route = ((0,0),(1,0),(2,0),(2,1),(2,2),(1,2),(0,2))
        a,b = Rank('H',((0,0),(1,0))),Rank('H',((0,2),(1,2)))
        services = (OldService(a,0,1),OldService(b,5,6))
        blocks = path_sets((a,b),services,route,set(route))
        self.assertEqual(len(blocks),1)
        self.assertEqual(blocks[0]['path'],route)
        split = path_sets((a,b),services,route,set(route)-{(2,1)})
        self.assertEqual(len(split),2)
        self.assertTrue(all((2,1) not in b['path'] for b in split))

    def test_exact_gtsp_against_all_permutations_and_orientations(self):
        rng = random.Random(410)
        for groups in range(1,5):
            n = 2*groups+2
            matrix = [[rng.randrange(1,30) for j in range(n)] for i in range(n)]
            sets = [[2*i,2*i+1] for i in range(groups)]+[[n-2],[n-1]]
            cost,tour = exact_gtsp(matrix,sets,n-2,n-1)
            brute = min(sum(matrix[a][b] for a,b in zip(order,order[1:]))
                for permutation in itertools.permutations(range(groups))
                for choices in itertools.product((0,1),repeat=groups)
                for order in [(n-2,)+tuple(2*k+choices[k] for k in permutation)+(n-1,)])
            self.assertEqual(cost,brute)

    def test_real_glns_terminal_constraints_cost_and_coverage(self):
        cells = {(x,y) for x in range(4) for y in range(3)}
        s = Snapshot('native',frozenset(cells),frozenset(cells),frozenset(),(0,0),(0,0),(),radius=0)
        ranks = rank_replan(cells,variant=0)['ranks']
        blocks = path_sets(ranks,(),(),s.free)
        actual = tour_replan(Geometry(s),blocks,seconds=.3,seed=71)
        oracle = tour_replan(Geometry(s),blocks,exact=True)
        self.assertTrue(audit(s,actual['route'])['valid'])
        self.assertGreaterEqual(actual['length'],oracle['length'])
        self.assertEqual(actual['length'],sum(actual['matrix'][a][b] for a,b in
            zip(actual['order'],actual['order'][1:]+actual['order'][:1])))

    def test_history_adapter_covers_once_without_false_future_targets(self):
        route = ((0,0),(1,0),(2,0),(2,1),(1,1),(0,1),(0,0))
        records = old_services(route,{(1,0),(2,0),(1,1),(0,1)})
        flat = [p for s in records for p in s.rank.cells]
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(set(flat),{(1,0),(2,0),(1,1),(0,1)})


class AdapterTests(unittest.TestCase):
    def fixture(self):
        free = frozenset((x,y) for x in range(6) for y in range(4))
        old = frozenset((x,y) for x in range(4) for y in range(3))
        route = tuple((x,y) for y in range(3) for x in (range(4) if y%2 == 0 else range(3,-1,-1)))
        # Append a legal return connector.
        route += ((2,2),(1,2),(0,2),(0,1),(0,0))
        s = Snapshot('adapter',free,old,frozenset({(0,0)}),(0,0),(0,0),route,radius=0)
        return s,old

    def test_expansion_and_obstacle_both_models(self):
        s,old = self.fixture()
        targets = s.targets | {(4,0),(4,1),(4,2)}
        s = replace(s,free=s.free-{(2,1)},targets=targets-{(2,1)})
        for v in (1,2):
            r = solve_core(s,old,v,seconds=2,cap_override=30)
            self.assertEqual(r['status'],'planned')
            self.assertTrue(audit(s,r['route'])['valid'])
            self.assertIn('tour',r['detail'])
            self.assertFalse(r['detail']['original_encounter_framework'])

    def test_budget_infeasible_core_returns_real_fallback(self):
        s,old = self.fixture()
        s = replace(s,free=s.free-{(2,1)},targets=s.targets-{(2,1)})
        r = solve_core(s,old,seconds=2,cap_override=0)
        self.assertEqual(r['status'],'planned')
        self.assertTrue(audit(s,r['route'])['valid'])
        self.assertEqual(r['detail']['core_no_solution'],'infeasible')
        self.assertEqual(r['source'],'GD_adapter_fallback')

    def test_zero_time_does_not_claim_success(self):
        s,old = self.fixture()
        r = solve_core(s,old,seconds=0)
        self.assertEqual(r['status'],'planning_failure')
        self.assertFalse(r['route'])

    def test_cap_inverse(self):
        p = {'monotone_seconds':[.01,.02,.04,.08]}
        self.assertIsNone(cap_for_time(p,.001))
        self.assertEqual(cap_for_time(p,.039),1)
        self.assertEqual(cap_for_time(p,10),3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
