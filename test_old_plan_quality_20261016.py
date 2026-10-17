import copy,unittest
from old_plan_quality_diagnostic_20261016 import route_check,reference_case,precheck
class Tests(unittest.TestCase):
    def setUp(self):
        self.c=dict(name='tiny',free=[[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]],targets=[[0,0],[1,0],[2,0]],covered=[[0,0]],
            current=[1,0],base=[0,0],old_route=[[1,0],[2,0],[1,0],[0,0]],radius=0,distance_budget=10,
            metadata=dict(initial_targets=[[0,0],[1,0],[2,0]],split='development',event='no_change',range_diagnostic=dict(role='control')))
    def test_route(self):self.assertTrue(route_check(self.c,self.c['old_route'])['valid'])
    def test_collision(self):
        c=copy.deepcopy(self.c);c['free'].remove([2,0]);self.assertFalse(route_check(c,c['old_route'])['valid'])
    def test_no_diagonal(self):self.assertFalse(route_check(self.c,[[1,0],[2,1],[2,0],[1,0],[0,0]])['valid'])
    def test_return(self):self.assertFalse(route_check(self.c,[[1,0],[2,0]])['valid'])
    def test_coverage(self):self.assertFalse(route_check(self.c,[[1,0],[0,0]])['valid'])
    def test_resource(self):
        c=copy.deepcopy(self.c);c['distance_budget']=2;self.assertFalse(route_check(c,c['old_route'])['valid'])
    def test_only_tail_changes(self):
        old=copy.deepcopy(self.c);r=[[1,0],[2,0],[2,1],[1,1],[0,1],[0,0]];new=reference_case(self.c,r)
        self.assertEqual(self.c,old);self.assertEqual(new['old_route'],r)
        self.assertTrue(all(new[k]==old[k] for k in old if k!='old_route'))
    def test_reject_invalid_reference(self):
        with self.assertRaises(ValueError):reference_case(self.c,[[1,0],[0,0]])
    def test_control_only(self):
        precheck(self.c);c=copy.deepcopy(self.c);c['metadata']['event']='obstacle'
        with self.assertRaises(AssertionError):precheck(c)
    def test_empty_window_independently(self):
        from verify_road_range_diagnostic_20261015 import independent_plan
        cfg=independent_plan(self.c)['plans']['R_SEED']
        self.assertEqual((cfg['left'],cfg['right'],cfg['required']),(0,0,[]))
if __name__=='__main__':unittest.main()
