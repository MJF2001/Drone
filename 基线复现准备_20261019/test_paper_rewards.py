"""Independent scalar formula checks against manuscript Eqs 2--6; not ranking."""
import unittest,math
from ppcpp_independent import core
class PaperRewards(unittest.TestCase):
    def test_distance_eq2(self):
        pending={(1,0),(0,1),(-1,0),(0,-1)}
        rows=core.reward_options((0,0),None,pending,pending|{(0,0)},(-2,0),(2,.5))
        for row in rows:
            q=row['cell'];expected=(math.dist(q,(-2,0))-1)/2
            self.assertAlmostEqual(row['distance_reward'],expected)
    def test_angle_eq3_all_cardinal_pairs(self):
        dirs=((1,0),(0,1),(-1,0),(0,-1))
        for incoming in dirs:
            for outgoing in dirs:
                previous=(-incoming[0],-incoming[1]);q=outgoing
                rows=core.reward_options((0,0),previous,{q},{(0,0),q},(-3,-3),(2,.5))
                # Geometric interior angle: previous-current against next-current.
                cosine=(previous[0]*q[0]+previous[1]*q[1])
                expected=math.acos(cosine)/math.pi
                self.assertAlmostEqual(rows[0]['straight_reward'],expected)
    def test_boundary_eq4_with_historical_frontier(self):
        q=(1,0);pending={q,(2,0),(1,1)};free=pending|{(0,0),(1,-1)}
        row=core.reward_options((0,0),None,pending,free,(-2,0),(2,.5))[0]
        self.assertEqual(row['boundary_reward'],.5)
    def test_boundary_not_obstacles_only(self):
        q=(1,0);free={q,(0,0),(2,0),(1,1),(1,-1)}
        row=core.reward_options((0,0),None,{q},free,(-2,0),(2,.5))[0]
        self.assertEqual(row['boundary_reward'],1.)
    def test_sum_eq5(self):
        rows=core.reward_options((0,0),(-1,0),{(1,0),(0,1)},{(0,0),(1,0),(0,1)},(-2,0),(2,.5))
        for r in rows:self.assertAlmostEqual(r['score'],r['distance_reward']+2*r['straight_reward']+.5*r['boundary_reward'])
    def test_argmax_eq6_and_tie_convention(self):
        self.assertEqual(core.choose_neighbor([dict(cell=(0,1),score=2),dict(cell=(1,0),score=1)]),(0,1))
        self.assertEqual(core.choose_neighbor([dict(cell=(1,0),score=2),dict(cell=(0,1),score=2)]),(0,1))
    def test_equal_distance_is_explicit_extra_convention(self):
        rows=core.reward_options((0,0),None,{(0,1),(0,-1)},{(0,0),(0,1),(0,-1)},(-2,0),(2,.5))
        self.assertTrue(all(r['distance_reward']==0 for r in rows))
    def test_predator_exterior_not_a_unique_original_rule(self):
        for base in ((-5,0),(5,0)):
            targets={(0,0),(1,0),(1,1)};p=core.predator_for(targets,base);self.assertTrue(p[0]<0 or p[0]>1)
    def test_dot_formula_not_general_angle_formula(self):
        self.assertNotAlmostEqual((math.cos(math.pi/4)+1)/2,.75)
if __name__=='__main__':unittest.main()
