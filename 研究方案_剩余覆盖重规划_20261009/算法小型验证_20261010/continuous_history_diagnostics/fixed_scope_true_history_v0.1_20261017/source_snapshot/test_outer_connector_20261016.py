import unittest,time,copy
import portable_frozen
from model import Snapshot,DeadlineExceeded
from unified_geometry import UnifiedGeometry
from outer_connector_candidate_20261016 import responsibilities,connect,outside_segments,solve
from old_plan_quality_diagnostic_20261016 import route_check
class Tests(unittest.TestCase):
    def setUp(self):
        self.old=((0,0),(0,1),(1,1),(1,0),(2,0),(1,0),(0,0))
        self.s=Snapshot('fixture',frozenset((x,y) for x in range(3) for y in range(2)),frozenset({(2,0)}),frozenset(),(0,0),(0,0),self.old,0,100)
        self.cfg=dict(left=3,right=4,required=((2,0),));self.g=UnifiedGeometry(self.s,float('inf'))
    def test_partition(self):
        a=responsibilities(self.s,self.cfg);self.assertEqual(a['local_required'],((2,0),));self.assertEqual(a['prefix_required'],())
    def test_shorter_and_ports(self):
        a=responsibilities(self.s,self.cfg);p,q=outside_segments(self.s,self.cfg,a,self.g,'RECONNECT');self.assertEqual(p,((0,0),(1,0)));self.assertEqual(q,((2,0),(1,0),(0,0)))
        self.assertEqual(len(self.old)-1-(len(p)+len(q)-2+1),2)
    def test_literal(self):
        p,q=outside_segments(self.s,self.cfg,responsibilities(self.s,self.cfg),self.g,'LITERAL');self.assertEqual(p,self.old[:4]);self.assertEqual(q,self.old[4:])
    def test_zero_steps(self):self.assertEqual(connect(self.g,(0,0),[(0,0)],(0,0)),((0,0),))
    def test_no_incidental_skip(self):
        r=connect(self.g,(0,0),[(2,0),(1,0)],(0,0));self.assertEqual(r,((0,0),(1,0),(2,0),(1,0),(0,0)))
    def test_deadline(self):
        with self.assertRaises(DeadlineExceeded):connect(self.g,(0,0),[],(0,0),time.perf_counter()-1)
    def test_unknown(self):
        with self.assertRaises(ValueError):outside_segments(self.s,self.cfg,{},self.g,'bad')
    def test_no_mutation(self):
        cfg=copy.deepcopy(self.cfg);responsibilities(self.s,cfg);self.assertEqual(cfg,self.cfg);self.assertEqual(self.s.old_route,self.old)
    def test_full_solve(self):
        for mode in ('LITERAL','RECONNECT'):
            r=solve(self.s,{(2,0)},mode,1,1);self.assertTrue(r['independent_audit']['valid']);self.assertTrue(r['core_independent_audit']['valid'])
    def test_resource(self):
        s=Snapshot('cap',self.s.free,self.s.targets,self.s.covered,self.s.current,self.s.base,self.old,0,2)
        r=solve(s,{(2,0)},'RECONNECT',1,1);self.assertFalse(r['route'])
    def test_changed_map(self):
        s=Snapshot('new',self.s.free,frozenset({(2,0),(2,1)}),frozenset(),self.s.current,self.s.base,self.old,0,100)
        for mode in ('LITERAL','RECONNECT'):
            r=solve(s,{(2,0)},mode,1,1);self.assertTrue(r['independent_audit']['valid']);self.assertTrue(r['core_independent_audit']['valid'])
    def test_new_obstacle(self):
        s=Snapshot('obstacle',self.s.free-{(1,1)},self.s.targets,frozenset(),self.s.current,self.s.base,self.old,0,100)
        for mode in ('LITERAL','RECONNECT'):
            r=solve(s,{(2,0)},mode,1,1);self.assertTrue(r['independent_audit']['valid']);self.assertNotIn((1,1),r['route'])
            self.assertTrue(r['core_independent_audit']['valid'])
    def test_prefix_suffix_assignment(self):
        s=Snapshot('tasks',self.s.free,frozenset({(0,1),(2,0),(0,0)}),frozenset(),(0,0),(0,0),self.old,0,100)
        a=responsibilities(s,self.cfg);self.assertEqual(a['prefix_visits'],((0,1),));self.assertEqual(a['suffix_visits'],())
        self.assertNotIn((0,0),a['prefix_required'])
    def test_independent_bfs_checker(self):
        from verify_outer_connector_diagnostic_20261016 import segment_check
        c=dict(free=list(self.s.free));self.assertEqual(segment_check(c,[(0,0),(1,0),(2,0),(1,0),(0,0)],(0,0),[(2,0),(1,0)],(0,0),True),4)
        with self.assertRaises(AssertionError):segment_check(c,[(0,0),(0,1),(1,1),(1,0)],(0,0),[],(1,0),True)
    def test_deadline_solve(self):
        r=solve(self.s,{(2,0)},'RECONNECT',.000000001,1);self.assertEqual(r['status'],'deadline')
if __name__=='__main__':unittest.main()
