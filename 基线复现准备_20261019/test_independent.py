import unittest
from unittest.mock import patch
import ppcpp_independent as p
from model import Snapshot,DeadlineExceeded
class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Snapshot('tiny',frozenset((x,y) for x in range(3) for y in range(2)),frozenset({(1,0),(2,0),(2,1)}),frozenset(),(0,0),(0,0),(),0,100)
    def test_core_only_valid(self):
        with patch.object(p.core,'common_fallback',side_effect=AssertionError('forbidden')):
            r=p.solve(self.s,self.s.targets,1);self.assertEqual(r['status'],'core_complete');self.assertTrue(p.single_cell_audit(self.s,r['route'])['valid'])
    def test_old_route_irrelevant(self):
        changed=Snapshot(self.s.name,self.s.free,self.s.targets,self.s.covered,self.s.current,self.s.base,((999,999),),0,100)
        a=p.solve(self.s,self.s.targets,1);b=p.solve(changed,self.s.targets,1);self.assertEqual(a['route'],b['route'])
    def test_intrinsic_recovery_retained(self):
        s=Snapshot('recovery',frozenset((x,0) for x in range(4)),frozenset({(3,0)}),frozenset(),(0,0),(0,0),(),0,100)
        r=p.solve(s,s.targets,1);self.assertEqual(r['status'],'core_complete');self.assertGreater(r['detail']['recovery_count'],0)
    def test_deadline_no_fallback(self):
        with patch.object(p.core,'core_route',side_effect=DeadlineExceeded):
            r=p.solve(self.s,self.s.targets,1);self.assertEqual(r['route'],());self.assertEqual(r['status'],'deadline')
    def test_invalid_core_rejected(self):
        with patch.object(p.core,'core_route',return_value=((0,0),)):
            r=p.solve(self.s,self.s.targets,1);self.assertEqual(r['status'],'core_invalid');self.assertFalse(r['route'])
    def test_resource_rejected(self):
        s=Snapshot(self.s.name,self.s.free,self.s.targets,self.s.covered,self.s.current,self.s.base,(),0,1)
        self.assertFalse(p.solve(s,s.targets,1)['route'])
    def test_no_input_mutation(self):
        before=repr(self.s);p.solve(self.s,self.s.targets,1);self.assertEqual(before,repr(self.s))
    def test_invalid_weight_rejected(self):
        with self.assertRaises(ValueError):p.solve(self.s,self.s.targets,1,weights=(-1,1))
if __name__=='__main__':unittest.main()
