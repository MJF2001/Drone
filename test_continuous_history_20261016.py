import unittest,copy
from continuous_history_inputs_20261016 import checkpoint,publish
class Tests(unittest.TestCase):
    def setUp(self):
        self.c=dict(name='tiny',free=[[0,0],[1,0],[2,0],[3,0]],targets=[[1,0],[2,0]],covered=[],current=[0,0],base=[0,0],old_route=[[0,0],[1,0],[2,0],[1,0],[0,0]],radius=0,distance_budget=32,metadata=dict(map_id='tiny'))
        self.e=dict(free=self.c['free'],metadata=dict(published_targets=[[1,0],[2,0],[3,0]],event='straight'))
    def test_first_threshold(self):
        h=checkpoint(self.c,self.c['old_route']);self.assertEqual(h['index'],1);self.assertEqual(h['covered'],[[1,0]]);self.assertEqual(h['remaining_budget'],31)
    def test_no_premature_future(self):self.assertNotIn([3,0],checkpoint(self.c,self.c['old_route'])['covered'])
    def test_suffix_continuity(self):
        h=checkpoint(self.c,self.c['old_route']);self.assertEqual(h['executed_route']+h['old_route'][1:],self.c['old_route'])
    def test_repeated_steps_not_progress(self):
        route=[[0,0],[1,0],[0,0],[1,0],[2,0],[1,0],[0,0]];self.assertEqual(checkpoint(self.c,route,75)['index'],4)
    def test_invalid_route(self):
        with self.assertRaises(ValueError):checkpoint(self.c,[[0,0],[2,0],[0,0]])
    def test_hidden_deferred(self):
        h=checkpoint(self.c,self.c['old_route']);self.e['free']=[[0,0],[1,0],[3,0]];p=publish(self.c,h,self.e)['case'];self.assertEqual(p['metadata']['deferred_targets'],[[2,0]]);self.assertNotIn([2,0],p['covered'])
    def test_current_collision(self):
        self.e['free']=[[0,0],[2,0],[3,0]];self.assertEqual(publish(self.c,checkpoint(self.c,self.c['old_route']),self.e)['status'],'unsupported_current_blocked')
    def test_base_collision(self):
        self.e['free']=[[1,0],[2,0],[3,0]];self.assertEqual(publish(self.c,checkpoint(self.c,self.c['old_route']),self.e)['status'],'unsupported_base_blocked')
    def test_no_mutation(self):
        saved=copy.deepcopy(self.c);h=checkpoint(self.c,self.c['old_route']);publish(self.c,h,self.e);self.assertEqual(saved,self.c)
    def test_bad_percent(self):
        for p in (0,100):
            with self.assertRaises(ValueError):checkpoint(self.c,self.c['old_route'],p)
if __name__=='__main__':unittest.main()
