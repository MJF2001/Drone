import unittest,copy
from types import SimpleNamespace
import ppcpp
from model import Snapshot
from audit_ppcpp import audit,bfs
class Gates(unittest.TestCase):
    def setUp(self):
        self.s=Snapshot('gate',frozenset((x,y) for x in range(4) for y in range(3)),frozenset({(1,0),(3,0),(3,2)}),frozenset({(0,0)}),(0,0),(0,0),(),0,100)
        self.c={k:[list(p) for p in getattr(self.s,k)] for k in ('free','targets','covered')};self.c.update(current=[0,0],base=[0,0],distance_budget=100)
    def test_decision_audit_and_heading(self):
        r=ppcpp.solve(self.s,self.s.targets|self.s.covered,1,0,(-1,0),(0,1));self.assertTrue(audit(self.c,r)['valid'])
    def test_corrupt_score_detected(self):
        r=ppcpp.solve(self.s,self.s.targets|self.s.covered,1,0,(-1,0),None);r['trace'][0]['options'][0]['score']+=.1
        with self.assertRaises(AssertionError):audit(self.c,r)
    def test_old_route_and_seed_do_not_change_core(self):
        s=Snapshot(self.s.name,self.s.free,self.s.targets,self.s.covered,self.s.current,self.s.base,((999,999),),0,100)
        a=ppcpp.solve(self.s,self.s.targets|self.s.covered,1,0,(-1,0),None);b=ppcpp.solve(s,s.targets|s.covered,1,9,(-1,0),None);self.assertEqual(a['route'],b['route'])
    def test_audit_cross_deadline_rejected(self):
        for end in (1.,1.01):
            clock=SimpleNamespace(now=0.)
            class FakeGeometry:
                def __init__(self,s,d):self.s=s
                def precheck(self):return None
                def path(self,a,b):return (a,)
            s=Snapshot('empty',frozenset({(0,0)}),frozenset(),frozenset(),(0,0),(0,0),(),0,0)
            def delayed(s,r):clock.now=end;return dict(valid=True)
            r=ppcpp.solve(s,set(),1,0,(-1,0),None,_clock=lambda:clock.now,_geometry=FakeGeometry,_audit=delayed)
            self.assertFalse(r['route']);self.assertEqual(r['status'],'deadline')
    def test_empty_return(self):
        s=Snapshot('return',self.s.free,frozenset(),frozenset(),(3,0),(0,0),(),0,100)
        r=ppcpp.solve(s,set(),1,0,(-1,0),None);self.assertEqual(len(r['route'])-1,3)
    def test_resource_rejects_complete_geometry(self):
        s=Snapshot('resource',self.s.free,self.s.targets,self.s.covered,self.s.current,self.s.base,(),0,1)
        self.assertFalse(ppcpp.solve(s,s.targets|s.covered,1,0,(-1,0),None)['route'])
    def test_predator_not_recomputed_from_targets(self):
        r=ppcpp.solve(self.s,self.s.targets|self.s.covered,1,0,(-3,7),None);self.assertEqual(r['predator'],(-3,7))
    def test_invalid_history_rejected(self):
        with self.assertRaises(ValueError):ppcpp.solve(self.s,self.s.targets|self.s.covered,1,0,(-1,0),(99,99))
if __name__=='__main__':unittest.main()
