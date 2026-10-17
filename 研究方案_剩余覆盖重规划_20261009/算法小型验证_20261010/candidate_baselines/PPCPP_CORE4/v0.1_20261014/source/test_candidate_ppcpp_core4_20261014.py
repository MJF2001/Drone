import copy
import math
import unittest
from unittest.mock import Mock
from dataclasses import replace
import candidate_ppcpp_core4_20261014 as c
from model import Snapshot,DeadlineExceeded
from unified_geometry import UnifiedGeometry


def scene(free=None,targets=None,covered=(),current=(0,0),base=(0,0),old=(),limit=1000):
    if free is None:free={(x,y) for x in range(4) for y in range(3)}
    if targets is None:targets=free
    return Snapshot('unit',frozenset(free),frozenset(targets),frozenset(covered),
        current,base,tuple(old),0,limit)


def run(s,**kwargs):
    return c.solve(s,set(s.targets)|set(s.covered),1,**kwargs)


class CandidateTests(unittest.TestCase):
    def test_predator_side_and_empty(self):
        targets={(2,0),(5,1)}
        self.assertEqual(c.predator_for(targets,(0,7)),(1,7))
        self.assertEqual(c.predator_for(targets,(8,7)),(6,7))
        self.assertIsNone(c.predator_for(set(),(0,0)))

    def test_empty_targets_returns(self):
        s=scene(targets=set(),current=(3,2))
        r=run(s)
        self.assertTrue(r['independent_audit']['valid'])
        self.assertEqual(len(r['route'])-1,5)
        self.assertTrue(r['detail']['core_valid_before_deadline'])

    def test_empty_at_base_zero_steps(self):
        r=run(scene(targets=set()))
        self.assertEqual(r['route'],((0,0),))
        self.assertTrue(r['independent_audit']['valid'])

    def test_origin_immediately_credited(self):
        r=run(scene(targets={(0,0)}))
        self.assertEqual(r['detail']['initial_pending'],0)
        self.assertEqual(len(r['detail']['core_route']),1)

    def test_single_uncovered_target(self):
        r=run(scene(targets={(1,0)}))
        self.assertEqual(r['detail']['core_steps'],2)
        self.assertEqual(r['detail']['local_moves'],1)

    def test_zero_range_single_neighbor(self):
        options=c.reward_options((0,0),None,{(1,0)},{(0,0),(1,0)},(-1,0),(1,1))
        self.assertEqual(options[0]['distance_reward'],0)
        self.assertEqual(options[0]['straight_reward'],0)
        self.assertTrue(math.isfinite(options[0]['score']))

    def test_zero_range_symmetric_neighbors(self):
        options=c.reward_options((0,0),None,{(-1,0),(1,0)},{(-1,0),(0,0),(1,0)},(0,2),(1,1))
        self.assertEqual([r['distance_reward'] for r in options],[0,0])
        self.assertEqual(c.choose_neighbor(options),(-1,0))

    def test_straight_turn_reverse_rewards(self):
        pending={(1,0),(-1,0),(0,1)}
        rows=c.reward_options((0,0),(-1,0),pending,pending|{(0,0)},(0,3),(1,0))
        values={r['cell']:r['straight_reward'] for r in rows}
        self.assertEqual(values,{(1,0):1.,(-1,0):0.,(0,1):.5})

    def test_distance_normalization(self):
        pending={(1,0),(-1,0)}
        rows=c.reward_options((0,0),None,pending,pending|{(0,0)},(-10,0),(0,0))
        values={r['cell']:r['distance_reward'] for r in rows}
        self.assertEqual(values,{(1,0):1.,(-1,0):0.})

    def test_uncovered_boundary_count(self):
        pending={(1,0),(2,0),(-1,0)}
        rows=c.reward_options((0,0),None,pending,pending|{(0,0)},(0,3),(0,1))
        values={r['cell']:r['boundary_reward'] for r in rows}
        self.assertEqual(values,{(1,0):.75,(-1,0):1.})

    def test_only_cardinal_pending_free_neighbors(self):
        pending={(1,1),(1,0),(-1,0)};free={(0,0),(1,1),(1,0)}
        rows=c.reward_options((0,0),None,pending,free,(3,3),(1,1))
        self.assertEqual([r['cell'] for r in rows],[(1,0)])

    def test_lexicographic_exact_tie(self):
        rows=[dict(cell=(3,4),score=1.),dict(cell=(-1,5),score=1.)]
        self.assertEqual(c.choose_neighbor(rows),(-1,5))

    def test_dead_end_uses_non_target_space(self):
        s=scene(targets={(0,0),(3,0),(3,2)},covered={(0,0)})
        r=run(s)
        self.assertTrue(r['detail']['core_valid_before_deadline'])
        self.assertEqual(r['detail']['recoveries'][0]['goal'],(3,0))
        self.assertGreater(r['detail']['recovery_moves'],0)
        self.assertIn((1,0),r['detail']['core_route'])

    def test_recovery_traverses_historical_targets(self):
        free={(x,0) for x in range(5)};covered={(x,0) for x in range(4)}
        s=scene(free=free,targets=free,covered=covered)
        r=run(s)
        self.assertEqual(r['detail']['recovery_count'],1)
        self.assertEqual(r['detail']['recoveries'][0]['fresh'],1)
        self.assertEqual(s.covered,frozenset(covered))

    def test_segment_credits_every_crossed_target(self):
        s=scene(targets={(1,0),(2,0)});g=UnifiedGeometry(s)
        route=[s.current];pending=set(s.targets)
        self.assertEqual(c.credit_segment(g,route,pending,((0,0),(1,0),(2,0))),2)
        self.assertFalse(pending)
        with self.assertRaises(ValueError):c.credit_segment(g,route,pending,((0,0),))

    def test_historical_blocked_cell_remains_in_ledger(self):
        free={(0,0),(1,0),(1,1),(0,1)};covered={(2,0)}
        s=scene(free=free,targets={(1,1)},covered=covered)
        r=c.solve(s,{(2,0)},1)
        self.assertTrue(r['independent_audit']['valid'])
        self.assertEqual(s.covered,frozenset(covered))
        self.assertNotIn((2,0),r['route'])

    def test_illegal_blocked_target_rejected(self):
        s=scene(free={(0,0)},targets={(1,0)})
        with self.assertRaises(ValueError):run(s)

    def test_wrong_radius_rejected(self):
        with self.assertRaises(ValueError):run(replace(scene(),radius=1))

    def test_unreachable_base(self):
        s=scene(free={(0,0),(2,0)},targets={(0,0)},base=(2,0))
        r=run(s)
        self.assertEqual(r['status'],'environment_infeasible')
        self.assertFalse(r['route'])

    def test_unreachable_target(self):
        s=scene(free={(0,0),(2,0)},targets={(2,0)})
        r=run(s)
        self.assertEqual(r['status'],'environment_infeasible')
        self.assertFalse(r['route'])

    def test_resource_shortage_does_not_claim_completion(self):
        s=scene(targets={(1,0)},limit=1)
        r=run(s)
        self.assertEqual(r['status'],'no_legal_candidate')
        self.assertFalse(r['route'])
        self.assertFalse(r['detail']['core_valid_before_deadline'])

    def test_budget_expires_before_geometry(self):
        s=scene()
        r=c.solve(s,s.targets,1e-12)
        self.assertEqual(r['status'],'deadline')
        self.assertFalse(r['route'])

    def test_offer_checks_after_audit_and_drops_late_route(self):
        s=scene(targets={(0,0)});g=Mock()
        g.check_time.side_effect=[None,DeadlineExceeded()]
        incumbent=c.Incumbent(s,g,0)
        with self.assertRaises(DeadlineExceeded):incumbent.offer(((0,0),),'late')
        self.assertFalse(incumbent.route)

    def test_equal_route_keeps_earlier_incumbent(self):
        s=scene(targets={(0,0)});g=Mock();incumbent=c.Incumbent(s,g,0)
        self.assertTrue(incumbent.offer(((0,0),),'fallback'))
        self.assertTrue(incumbent.offer(((0,0),),'core'))
        self.assertEqual(incumbent.source,'fallback')

    def test_core_success_distinct_from_selection(self):
        s=scene(free={(0,0),(1,0)},targets={(1,0)},old=((0,0),(1,0),(0,0)))
        r=run(s)
        self.assertTrue(r['fallback_selected'])
        self.assertEqual(r['source'],'old_suffix')
        self.assertTrue(r['detail']['core_valid_before_deadline'])

    def test_invalid_weights_and_budget(self):
        s=scene()
        for weights in ((math.nan,1),(1,math.inf),(-1,1),(1,)):
            with self.assertRaises(ValueError):run(s,weights=weights)
        with self.assertRaises(ValueError):c.solve(s,s.targets,math.inf)
        with self.assertRaises(ValueError):c.solve(s,s.targets,0)

    def test_input_unchanged_and_seed_not_a_search_parameter(self):
        s=scene();backup=copy.deepcopy(s)
        a=run(s,seed=11);b=run(s,seed=19)
        self.assertEqual(s,backup)
        self.assertEqual(a['detail']['core_route'],b['detail']['core_route'])
        self.assertEqual(a['route'],b['route'])


if __name__=='__main__':unittest.main()
