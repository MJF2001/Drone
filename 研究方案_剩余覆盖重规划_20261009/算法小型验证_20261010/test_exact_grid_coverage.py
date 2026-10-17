import unittest
from model import Snapshot
from audit import audit
from exact_grid_coverage import exact_coverage,independent_metric_optimum


class ExactCoverageTests(unittest.TestCase):
    def check(self,s,expected):
        result=exact_coverage(s)
        self.assertEqual(result['status'],'optimal')
        self.assertEqual(result['length'],expected)
        self.assertEqual(independent_metric_optimum(s),expected)
        self.assertTrue(audit(s,result['route'])['valid'])

    def test_transit_targets_and_return(self):
        self.check(Snapshot('line',frozenset((x,0) for x in range(4)),frozenset(((1,0),(2,0))),frozenset(),(0,0),(3,0),(),0,20),3)

    def test_covered_current_and_empty_pending(self):
        self.check(Snapshot('empty',frozenset(((0,0),(1,0),(2,0))),frozenset(((1,0),)),frozenset(((1,0),)),(2,0),(0,0),(),0,20),2)

    def test_non_target_detour_is_allowed(self):
        free=frozenset(((0,0),(0,1),(1,1),(2,1),(2,0)))
        self.check(Snapshot('detour',free,frozenset(((2,0),)),frozenset(),(0,0),(0,0),(),0,20),8)

    def test_initial_pose_captures_target(self):
        self.check(Snapshot('start_target',frozenset(((0,0),(1,0))),frozenset(((0,0),)),frozenset(),(0,0),(1,0),(),0,20),1)


if __name__=='__main__':
    unittest.main()
