import sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'runtime'))
from history_adapter import solve,TaskPublicMap,HistoryCStar
from audit_v05 import audit
def case(f,t,h=(),s=(0,0),b=(0,0)):
    return dict(free=sorted(f),targets=sorted(t),covered=sorted(h),current=s,base=b,published_targets=sorted(set(t)|set(h)),distance_budget=10000)
class Tests(unittest.TestCase):
    def test_flight_not_replaced_by_service(self):
        m=TaskPublicMap({(0,0)});m.update({(x,0):True for x in range(5)});self.assertEqual(len(m.free),5);self.assertTrue(m.feasible((0,0),(4,0)))
    def test_current_domain_unknown_empty(self):
        m=TaskPublicMap({(0,0)});m.update({(0,0):True});self.assertFalse(m.unknown_adjacent((0,0)));self.assertNotIn((1,0),m.cells)
    def test_inner_service_frontier(self):
        m=TaskPublicMap({(0,0)});m.update({(x,y):True for x in range(-3,4) for y in range(-3,4)});self.assertTrue(m.frontier((0,0)))
    def test_transit_nodes_closed(self):
        f={(x,y) for x in range(-2,4) for y in range(-2,4)};t={(0,0),(1,0)};m=TaskPublicMap(t);m.update({p:True for p in f});p=HistoryCStar((0,0),m,t,())
        self.assertTrue(all(n.state=='Cl' for q,n in p.graph.nodes.items() if q not in p.service));self.assertTrue(all(not p.needed(q) for q in p.graph.nodes if q not in p.service))
    def test_padding_invariance(self):
        for pad in (2,6,10):
            f={(x,y) for x in range(-1,7) for y in range(-pad,pad+2)};t={(x,y) for x in range(6) for y in (0,1)};c=case(f,t,{(x,0) for x in range(6)})
            r=solve(c,5,20261018);audit(c,r,5);self.assertEqual(r['status'],'task_complete');self.assertEqual(len(r['route'])-1,12)
    def test_non_target_bridge(self):
        f={(x,0) for x in range(8)};c=case(f,{(0,0),(7,0)},{(0,0)},s=(1,0));r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'task_complete');self.assertIn((4,0),r['route'])
    def test_empty_return(self):
        c=case({(x,0) for x in range(4)},set(),s=(3,0));r=solve(c,5,7);audit(c,r,5);self.assertEqual(len(r['route'])-1,3)
    def test_deferred_blocked_history(self):
        c=case({(0,0),(1,0)},{(0,0),(1,0)},{(2,0)});c['published_targets'].append((3,0));r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'task_complete')
    def test_resource_refusal(self):
        c=case({(0,0),(1,0)},{(0,0),(1,0)});c['distance_budget']=1;r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'resource_exceeded')
    def test_native_hole_only_services_tasks(self):
        f={(x,y) for x in range(5) for y in range(4)};t={(x,1) for x in range(4)};c=case(f,t);r=solve(c,5,7);audit(c,r,5);self.assertEqual(r['status'],'task_complete');self.assertTrue(any(e['type']=='tsp' for e in r['events']))
if __name__=='__main__':unittest.main()
