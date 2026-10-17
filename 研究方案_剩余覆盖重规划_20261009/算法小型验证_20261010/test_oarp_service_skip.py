import unittest
from model import Snapshot
from audit import audit
from run_oarp_service_skip import replay


class ServiceSkipTests(unittest.TestCase):
    def scene(self):
        return Snapshot('line',frozenset((x,0) for x in range(4)),
            frozenset(((1,0),(2,0))),frozenset(),(0,0),(3,0),(),0,20)

    def test_transit_coverage_avoids_backtrack_without_dropping_targets(self):
        s = self.scene()
        blocks = [{'path':((2,0),)},{'path':((1,0),)}]
        full = replay(s,blocks,[4,0,2,5],False)
        skip = replay(s,blocks,[4,0,2,5],True)
        self.assertEqual(full['length'],5)
        self.assertEqual(skip['length'],3)
        self.assertEqual(skip['skipped'],[{'index':1,'point':(1,0),'at_current_pose':False}])
        self.assertTrue(audit(s,skip['route'])['valid'])
        self.assertEqual(full['visit_order'],skip['visit_order'])

    def test_uncovered_target_is_not_skipped(self):
        s = self.scene()
        blocks = [{'path':((1,0),)},{'path':((2,0),)}]
        full = replay(s,blocks,[4,0,2,5],False)
        skip = replay(s,blocks,[4,0,2,5],True)
        self.assertEqual(full['route'],skip['route'])
        self.assertEqual(skip['skipped'],[])
        self.assertTrue(audit(s,skip['route'])['valid'])


if __name__=='__main__':
    unittest.main()
