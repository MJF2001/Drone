import unittest
from scenarios_v2 import layout, initial, checkpoint, case_from_checkpoint, FAMILIES
from model import capture_route
from audit import audit


class FixedDomainTests(unittest.TestCase):
    def test_published_geometry_and_history_do_not_depend_on_event(self):
        for kind in ('open', 'corridor'):
            seed, route, straight, corner = initial(18, 6, kind)
            self.assertTrue(audit(seed, route)['valid'])
            old, prefix = checkpoint(seed, route, .75)
            for family in FAMILIES:
                s, meta = case_from_checkpoint(old, prefix, straight, corner, 18, 6, kind, .75, family)
                self.assertEqual(s.free | frozenset(map(tuple, meta['obstacles'])), seed.free)
                self.assertEqual(s.current, old.current)
                self.assertEqual(s.covered, capture_route(prefix, old.targets))
                self.assertEqual(s.old_route, old.old_route)
                self.assertEqual(s.distance_budget, seed.distance_budget)
                self.assertTrue(s.targets <= seed.free)
                self.assertFalse((s.targets-old.targets) & s.covered)
                self.assertIn(s.current, s.free)
                self.assertIn(s.base, s.free)

    def test_events_do_not_delete_inspection_targets(self):
        seed, route, straight, corner = initial(24, 9, 'corridor')
        old, prefix = checkpoint(seed, route, .25)
        for family in ('near_obstacle', 'far_obstacle', 'channel_obstacle'):
            s, meta = case_from_checkpoint(old, prefix, straight, corner, 24, 9, 'corridor', .25, family)
            self.assertEqual(s.targets, old.targets)
            self.assertTrue(meta['obstacles'])
            self.assertTrue(meta['old_route_collision'])

    def test_expansion_is_real_and_domain_known_before_event(self):
        old, straight, corner, domain = layout(18, 6, 'corridor')
        self.assertFalse(old & straight)
        self.assertFalse(old & corner)
        self.assertTrue((old | straight | corner) <= domain)
        self.assertEqual(len(straight), 54)
        self.assertEqual(len(corner), 90)


if __name__ == '__main__':
    unittest.main(verbosity=2)
