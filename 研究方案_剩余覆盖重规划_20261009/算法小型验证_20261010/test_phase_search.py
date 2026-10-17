import unittest
from dataclasses import replace
from phase_search import solve_phases, shifted_candidates, PHASES
from planners import candidates, solve
from model import Geometry
from audit import audit
from scenarios import build_case


class PhaseTests(unittest.TestCase):
    def test_zero_phase_is_original_generator(self):
        for family in ('no_change', 'straight', 'corner', 'local_obstacle', 'channel_obstacle'):
            s, _ = build_case(18, 6, .5, family)
            for direction in ('H', 'V'):
                g = Geometry(s)
                left = s.targets-s.covered-g.views[s.current]
                self.assertEqual(shifted_candidates(g,left,direction,(0,0)), candidates(g,left,direction))

    def test_every_phase_preserves_coverage_and_legal_centres(self):
        s, _ = build_case(18, 6, .5, 'corner')
        for phase in PHASES:
            for direction in ('H', 'V'):
                g = Geometry(s)
                left = s.targets-s.covered-g.views[s.current]
                points = shifted_candidates(g,left,direction,phase)
                covered = set().union(*(g.views[p] for p in points))
                self.assertTrue(left <= covered)
                self.assertTrue(set(points) <= s.free)
                self.assertEqual(len(points),len(set(points)))

    def test_zero_search_matches_p2_and_extended_keeps_incumbent(self):
        s, _ = build_case(18, 6, .5, 'straight')
        baseline = solve(s,'P2')
        zero = solve_phases(s,'ZERO')
        self.assertEqual(zero['route'], baseline.route)
        for mode in ('SHIFT','REPEAT'):
            r = solve_phases(s,mode)
            self.assertTrue(audit(s,r['route'])['valid'])
            self.assertEqual(r['baseline_stage_length'],len(baseline.route)-1)
            self.assertLessEqual(len(r['route']),len(baseline.route))

    def test_failure_states_not_called_complete(self):
        s, _ = build_case(18,6,.5,'corner')
        self.assertEqual(solve_phases(s,'SHIFT',0)['status'],'timeout')
        self.assertEqual(solve_phases(replace(s,distance_budget=1),'SHIFT')['status'],'planning_failure')
        bad, _ = build_case(18,6,.2,'closed_channel')
        self.assertEqual(solve_phases(bad,'SHIFT')['status'],'environment_infeasible')


if __name__ == '__main__':
    unittest.main(verbosity=2)
