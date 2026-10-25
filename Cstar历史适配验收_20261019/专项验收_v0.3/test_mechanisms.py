"""Mechanism gates, not route-length ranking."""
import sys,unittest,math,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
from history_adapter import HistoryCStar,TaskGraph,solve
from history_core.public_map import PublicMap
from history_core.planner import optimize_tsp
def case(free,targets,covered=(),current=(0,0),base=(0,0)):
    return dict(free=list(free),targets=list(targets),covered=list(covered),published_targets=list(set(targets)|set(covered)),current=current,base=base,distance_budget=1000)
def plan(c):return solve(c,2,7)
class Mechanisms(unittest.TestCase):
    def test_history_changes_first_core_decision(self):
        f={(0,0),(1,0),(2,0)};a=plan(case(f,{(0,0),(2,0)},current=(1,0),base=(1,0)))
        b=plan(case(f,{(0,0),(2,0)},{(0,0)},current=(1,0),base=(1,0)))
        self.assertEqual(a['task_filters'][0]['eligible'],[(0,0),(2,0)]);self.assertEqual(b['task_filters'][0]['eligible'],[(2,0)])
    def test_covered_is_transit_not_obstacle(self):
        c=case({(0,0),(1,0),(2,0)},{(0,0),(2,0)},{(0,0)},current=(1,0),base=(0,0));r=plan(c)
        self.assertEqual(r['status'],'task_complete');self.assertIn((0,0),r['route'])
    def test_covered_endpoint_does_not_hide_lap_work(self):
        f={(0,y) for y in range(5)};c=case(f,f,f-{(0,2)});r=plan(c)
        self.assertEqual(r['status'],'task_complete');self.assertIn((0,2),r['route'])
    def test_empty_ledger_stops_without_sweeping(self):
        f={(x,0) for x in range(4)};c=case(f,f,f,current=(3,0));r=plan(c)
        self.assertEqual(r['status'],'task_complete');self.assertEqual(len(r['route'])-1,3);self.assertEqual(len(r['task_events']),0)
    def test_history_does_not_close_traversal_state(self):
        m=PublicMap();m.update({(x,0):True for x in range(3)});p=HistoryCStar((1,0),m,{(0,0),(2,0)},{(0,0)})
        self.assertTrue(p.graph.is_open((0,0)));self.assertTrue(p.graph.nodes[(0,0)].tasked)
    def test_long_vertical_edge_split(self):
        m=PublicMap();m.update({(0,y):True for y in range(5)});g=TaskGraph(m)
        for q in ((0,0),(0,4)):g.insert(q)
        g.expand(set(g.nodes));g.insert((0,2),'link');g.expand({(0,2)})
        self.assertNotIn((0,4),g.edges[(0,0)]);self.assertIn((0,2),g.edges[(0,0)])
    def test_algorithm2_link_really_inserted(self):
        f={(x,y) for x in range(2) for y in range(-2,3)};m=PublicMap();m.update({p:True for p in f});g=TaskGraph(m)
        for p in ((1,0),(1,2),(0,0)):g.insert(p)
        g.expand(set(g.nodes));r=g.update_state((1,0),(0,0));self.assertIn([1,1],r['link_inserted'])
    def test_task_anchor_pruning_protects_corridor(self):
        m=PublicMap();m.update({(0,y):True for y in range(5)});g=TaskGraph(m)
        for p in ((0,0),(0,2),(0,4)):g.insert(p)
        g.expand(set(g.nodes));g.task_protected={(0,2)};g.prune((0,0));self.assertIn((0,2),g.nodes);g.validate((0,0))
    def test_real_retreat_selection_on_closed_bridge(self):
        f={(x,0) for x in range(4)};m=PublicMap();m.update({p:True for p in f});p=HistoryCStar((0,0),m,{(3,0)},set())
        p.graph.nodes[(1,0)].state='Cl';p.retreat={(3,0)}
        goal,path,retreat,why=p.select_goal();self.assertTrue(retreat);self.assertEqual(goal,(3,0));self.assertEqual(path,[(0,0),(1,0),(2,0),(3,0)])
    def test_known_hole_detector_and_tsp_really_run(self):
        f={(x,y) for x in range(3) for y in range(3)};m=PublicMap();m.update({p:True for p in f})
        ring={(x,y) for x in range(-1,4) for y in range(-1,4)}-f;m.update({p:False for p in ring})
        p=HistoryCStar((0,0),m,f,set());p.graph.prune(p.current);goal,path,retreat,why=p.select_goal()
        holes=p.detect_holes(goal);self.assertTrue(holes);event=p.cover_holes(holes,goal)
        self.assertEqual(event['type'],'tsp');self.assertGreater(event['moved_steps'],0);self.assertLess(len(p.pending),8)
    def test_algorithm3_endpoint_shapes(self):
        pts={(0,0),(0,1),(1,1)};cost={(a,b):abs(a[0]-b[0])+abs(a[1]-b[1]) for a in pts for b in pts}
        for end in ((1,1),(0,0),None):
            r,_,_=optimize_tsp(pts,(0,0),end,cost);self.assertEqual(r[0],(0,0));self.assertTrue(pts<=set(r))
            if end is not None:self.assertEqual(r[-1],end)
    def test_resource_refusal_no_completion_patch(self):
        c=case({(0,0),(1,0)},{(1,0)});c['distance_budget']=1;r=plan(c);self.assertFalse(r['route']);self.assertFalse(r['completion_tsp'])
    def test_invalid_history_ledger_rejected(self):
        c=case({(0,0),(1,0)},{(1,0)},{(0,0)});c['published_targets']=[(1,0)]
        with self.assertRaisesRegex(ValueError,'history outside'):plan(c)
    def test_conflicting_occupancy_rejected(self):
        c=case({(0,0),(1,0)},{(1,0)});c['known_blocked']=[(1,0)]
        with self.assertRaisesRegex(ValueError,'conflicting occupancy'):plan(c)
    def test_deadline_refuses_route(self):
        tick=[0]
        def clock():tick[0]+=1;return tick[0]
        r=solve(case({(0,0)},{(0,0)}),.1,7,clock=clock)
        self.assertEqual(r['status'],'wall_clock_cap');self.assertFalse(r['route'])
    def test_iteration_cap_is_not_success(self):
        r=solve(case({(0,0),(1,0)},{(1,0)}),2,7,max_iterations=0)
        self.assertEqual(r['status'],'iteration_limit');self.assertFalse(r['route'])
    def test_transit_responsibility_is_not_acquisition(self):
        m=PublicMap();m.update({(x,0):True for x in range(5)})
        p=HistoryCStar((1,0),m,{(4,0)},set())
        self.assertFalse(p.needed((2,0)));self.assertIn((2,0),p.transit_anchors)
        self.assertIn((2,0),p.graph.task_protected);self.assertNotIn((0,0),p.graph.task_protected)
    def test_closed_transit_without_retreat(self):
        m=PublicMap();m.update({(x,0):True for x in range(5)})
        p=HistoryCStar((1,0),m,{(4,0)},set())
        for node in p.graph.nodes.values():node.state='Cl'
        p.retreat=set();goal,path,is_retreat,why=p.select_goal()
        self.assertEqual(why['group'],'task_transit');self.assertEqual(path,[(1,0),(2,0)])
        self.assertFalse(p.needed(goal));self.assertEqual(p.pending,{(4,0)})
    def test_missing_rcg_service_not_grid_completed(self):
        m=PublicMap();m.update({(x,0):True for x in range(5)})
        p=HistoryCStar((1,0),m,{(4,0)},set())
        for a in ((4,0),(3,0)):
            for b in list(p.graph.edges[a]):p.graph.remove_edge(a,b)
            del p.graph.edges[a];del p.graph.nodes[a]
        goal,path,retreat,why=p.select_goal()
        self.assertIsNone(goal);self.assertEqual(why['group'],'no_task_representative');self.assertEqual(p.pending,{(4,0)})
if __name__=='__main__':unittest.main()
