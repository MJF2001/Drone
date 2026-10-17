import unittest
from dataclasses import replace
from scenarios_v3 import initial, case_from_checkpoint
from scenarios_v2 import checkpoint
from model import footprint
from audit import audit


class SingleCellTests(unittest.TestCase):
    def test_neighbour_is_not_captured(self):
        self.assertEqual(footprint((0, 0), {(0, 0), (1, 0), (0, 1)}, radius=0), {(0, 0)})

    def test_history_and_deferred_ledger(self):
        seed, route, straight, corner = initial(18, 6, 'corridor')
        self.assertEqual(seed.radius, 0)
        self.assertTrue(audit(seed, route)['valid'])
        old, prefix = checkpoint(seed, route, .25)
        self.assertEqual(old.covered, set(prefix) & seed.targets)
        for family in ('no_change', 'near_obstacle', 'straight_channel', 'corner_channel'):
            s, meta = case_from_checkpoint(old, prefix, straight, corner, 18, 6, 'corridor', .25, family)
            published = set(map(tuple, meta['published_targets']))
            blocked = set(map(tuple, meta['obstacles']))
            deferred = set(map(tuple, meta['deferred_targets']))
            self.assertEqual(deferred, (published-old.covered) & blocked)
            self.assertEqual(s.targets | deferred, published)
            self.assertFalse(s.targets & deferred)
            self.assertFalse((s.targets-s.covered) & blocked)
            self.assertEqual(s.covered, old.covered)
            self.assertEqual(s.current, prefix[-1])
            # Original all-target task cannot be claimed complete when deferred remain.
            if deferred:
                full = replace(s, targets=frozenset(published))
                self.assertFalse(audit(full, tuple(p for p in route if p in s.free))['valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
