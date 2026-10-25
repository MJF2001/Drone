import sys,unittest,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'runtime'))
from diagonal_geometry import DiagonalMetric,length
from common_geometry import NoPath
from history_adapter import solve
from audit_diagonal import audit,distance
class Tests(unittest.TestCase):
    def c(self,budget=100):return dict(free=[(0,0),(0,1),(1,0),(1,1)],targets=[(0,0),(1,1)],covered=[(0,0)],current=(0,0),base=(0,0),distance_budget=budget)
    def test_diagonal_sqrt2(self):self.assertEqual(length(DiagonalMetric(self.c()['free']).path((0,0),(1,1))),math.sqrt(2))
    def test_one_corner_blocked_no_cut(self):
        m=DiagonalMetric([(0,0),(1,0),(1,1)]);self.assertEqual(length(m.path((0,0),(1,1))),2)
    def test_both_corners_blocked_no_path(self):
        with self.assertRaises(NoPath):DiagonalMetric([(0,0),(1,1)]).path((0,0),(1,1))
    def test_land_only(self):
        c=self.c();r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'task_complete');self.assertEqual(set(r['route']),{(0,0),(1,1)});self.assertAlmostEqual(r['route_distance'],2*math.sqrt(2))
    def test_weighted_resource_not_move_count(self):
        c=self.c(2.8);r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'resource_exceeded')
    def test_side_targets_not_credited_by_diagonal(self):
        c=self.c();c['targets']=c['free'];r=solve(c,5,7);audit(c,r,5);self.assertTrue(set(c['targets'])<=set(r['route']))
    def test_empty_return(self):
        c=self.c();c['targets']=[];c['covered']=[];c['current']=(1,1);r=solve(c,5,7);audit(c,r,5);self.assertAlmostEqual(r['route_distance'],math.sqrt(2))
    def test_paths_against_independent_distance(self):
        f={(x,y) for x in range(5) for y in range(5)}-{(2,1),(2,2),(2,3)};m=DiagonalMetric(f)
        for a in sorted(f):
            for b in sorted(f):
                p=m.path(a,b);self.assertAlmostEqual(length(p),distance(f,a,b));self.assertEqual(m.path(b,a),p[::-1])
    def test_search_deadline(self):
        class Stop(Exception):pass
        def check(s):
            if s=='diagonal_search':raise Stop
        with self.assertRaises(Stop):DiagonalMetric({(x,y) for x in range(4) for y in range(3)},checkpoint=check).path((0,0),(3,2))
    def test_historical_blocked_retained(self):
        c=self.c();c['covered'].append((2,2));c['published_targets']=c['targets']+[(2,2),(3,3)];r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'task_complete')
if __name__=='__main__':unittest.main()
