import unittest
from dataclasses import replace
from model import Snapshot
from mechanisms import admissible, run_diagnostic, strict_expand, pool
from model import Geometry
from audit import audit
from scenarios import build_case, rectangle
from run_mechanisms import sensitivity_snapshot


class MechanismTests(unittest.TestCase):
    def test_constraints_distinguish_group_and_packet(self):
        labels = [(0, 0), (0, 1), (0, 2), (1, 0)]
        self.assertTrue(admissible([2, 1, 0, 3], labels, 'packet'))
        self.assertFalse(admissible([1, 0, 2, 3], labels, 'packet'))
        self.assertTrue(admissible([1, 0, 2, 3], labels, 'group'))
        self.assertFalse(admissible([0, 3, 1, 2], labels, 'group'))
        self.assertTrue(admissible([0, 3, 1, 2], labels, 'free'))

    def test_shared_pool_and_valid_outputs(self):
        for kind in ('G', 'S'):
            s, _ = build_case(18, 6, .5, 'corner')
            a = run_diagnostic(s, kind, False)
            b = run_diagnostic(s, kind, True)
            self.assertEqual(a['points'], b['points'])
            self.assertEqual(a['labels'], b['labels'])
            for r in (a, b):
                self.assertTrue(r['audit']['valid'])
                self.assertTrue(r['skipped_audit']['valid'])
                self.assertTrue(r['ordering_constraint_valid'])

    def test_skip_can_reduce_route_but_never_assume_it_will(self):
        s = Snapshot('skip', frozenset(rectangle(0, 0, 5, 3)), frozenset({(1, 1)}),
                     frozenset(), (0, 1), (0, 1), (), radius=1)
        g = Geometry(s)
        self.assertTrue(audit(s, g.expand([(4, 1)]))['valid'])
        self.assertLess(len(g.expand([(4, 1)])), len(strict_expand(g, [(4, 1)])))

    def test_timeout_has_no_false_incumbent(self):
        s, _ = build_case(18, 6, .5, 'corner')
        r = run_diagnostic(s, 'S', False, 0)
        self.assertEqual(r['status'], 'timeout')
        self.assertFalse(r['route'])

    def test_sensitivity_baseline_preserves_budget_and_history(self):
        for family in ('no_change', 'straight', 'corner', 'local_obstacle', 'channel_obstacle'):
            s, meta = build_case(18, 6, .5, family, initial_policy='optimized')
            baseline = sensitivity_snapshot(s, meta, 1, 2)
            self.assertEqual(replace(baseline, name=s.name), s)
            for radius in (1, 2):
                for margin in (1, 2, 3):
                    changed = sensitivity_snapshot(s, meta, radius, margin)
                    self.assertEqual(changed.distance_budget, s.distance_budget)
                    self.assertEqual(changed.current, s.current)
                    self.assertEqual(changed.old_route, s.old_route)


if __name__ == '__main__':
    unittest.main(verbosity=2)
