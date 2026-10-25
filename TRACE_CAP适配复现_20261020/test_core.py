import sys,unittest,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
from primitives import Metric,components,center,tour
from structures import TraceTree,CapGraph,trace_greedy,cap_greedy,trace_mark_departure,trace_dead_end
from planners import solve
def c(f,t=None,h=(),s=(0,0),b=(0,0),resource=1000):
    t=set(f) if t is None else set(t);h=set(h)
    return dict(free=sorted(f),targets=sorted(t),covered=sorted(h),current=s,base=b,published_targets=sorted(t|h),distance_budget=resource)
class Core(unittest.TestCase):
    def test_four_components(self):self.assertEqual(len(components({(0,0),(1,1)})),2)
    def test_center_in_concave_region(self):self.assertIn(center({(0,0),(0,2),(2,0)}),{(0,0),(0,2),(2,0)})
    def test_metric_no_cornercut(self):
        m=Metric({(0,0),(1,0),(1,1)});self.assertEqual(m.matrix([(0,0),(1,1)])[0][1],2)
    def test_canonical_connector(self):
        m=Metric({(x,y) for x in range(3) for y in range(3)});self.assertEqual(m.path((2,2),(0,0)),m.path((0,0),(2,2))[::-1])
    def test_open_nn_2opt(self):
        f={(x,0) for x in range(4)};m=Metric(f);r,info=tour(sorted(f),(0,0),lambda p:p,m)
        self.assertEqual(r[0],(0,0));self.assertEqual(set(r),f);self.assertLessEqual(info['final_cost'],info['initial_cost'])
    def test_fixed_endpoint(self):
        f={(x,0) for x in range(4)};r,_=tour(sorted(f),(0,0),lambda p:p,Metric(f),(1,0));self.assertEqual(r[-1],(1,0))
    def test_coincident_region_centers_not_deduped(self):
        r,_=tour([1,2],0,lambda p:(0,0),Metric({(0,0)}));self.assertEqual(set(r),{0,1,2})
    def test_trace_real_split_and_leaf_index(self):
        f={(x,0) for x in range(5)};s={p:'Fu' for p in f};tree=TraceTree(f,s,Metric(f),(0,0));tree.states[(2,0)]='Fc';tree.update({(2,0)})
        self.assertEqual(len(tree.order),2);self.assertTrue(tree.nodes[0]['children']);self.assertNotIn((2,0),tree.index)
        self.assertEqual(set().union(*(tree.nodes[i]['R'] for i in tree.order)),f-{(2,0)})
    def test_trace_unaffected_slot_order(self):
        f={(x,0) for x in range(11)};states={p:'Fc' if p in {(3,0),(7,0)} else 'Fu' for p in f};tree=TraceTree(f,states,Metric(f),(0,0));before=list(tree.order)
        middle=before[1];p=sorted(tree.nodes[middle]['R'])[1];tree.states[p]='Fc';tree.update({p})
        unchanged=[i for i in before if i!=middle];self.assertEqual([i for i in tree.order if i in unchanged],unchanged)
        self.assertTrue(any(e['type']=='slot_refine' and e['parent']==middle for e in tree.events))
    def test_trace_unknown_is_separate_symbolic_state(self):
        f={(0,0),(1,0)};tree=TraceTree(f,{(0,0):'Fu',(1,0):'U'},Metric(f),(0,0));self.assertEqual(tree.nodes[0]['state'],'exploring')
    def test_trace_delay_not_physical_completion(self):
        s={(0,0):'Fu',(0,1):'Fu',(0,-1):'Fu'};self.assertTrue(trace_mark_departure((0,0),s));self.assertEqual(s[(0,0)],'Fu')
    def test_trace_left_lap(self):
        f={(x,y) for x in range(-1,2) for y in range(-1,2)};s={p:'Fu' for p in f};self.assertEqual(trace_greedy((0,0),f,s,f),(-1,0))
    def test_trace_diagonal_rejected_through_obstacle(self):
        f={(0,0),(-1,1)};self.assertIsNone(trace_greedy((0,0),{(-1,1)},{(-1,1):'Fu'},f))
    def test_trace_dead_end_boundary(self):
        f={(x,0) for x in range(5)};s={p:'Fc' if p[0]<3 else 'Fu' for p in f};self.assertEqual(trace_dead_end((0,0),{(3,0),(4,0)},s,Metric(f)),(3,0))
    def test_cap_direction_order(self):self.assertEqual(cap_greedy((0,0),{(0,1),(0,-1),(1,0)}),(0,1))
    def test_cap_exploring_farthest_global_end(self):
        f={(x,0) for x in range(7)};g=CapGraph({(1,0),(5,0)},Metric(f),(0,0),unknown={(1,1),(5,1)})
        self.assertEqual(g.nodes[g.order[-1]]['center'],(5,0));self.assertEqual(g.events[-1]['end'],g.order[-1])
    def test_cap_all_known_free_global_end(self):
        g=CapGraph({(1,0),(3,0)},Metric({(x,0) for x in range(4)}),(0,0));self.assertIsNone(g.events[-1]['end'])
    def test_cap_replaces_graph_node_not_tree(self):
        f={(x,0) for x in range(5)};g=CapGraph(f,Metric(f),(0,0));g.replace(0,[{(0,0),(1,0)},{(3,0),(4,0)}])
        self.assertNotIn(0,g.nodes);self.assertEqual(len(g.nodes),2);self.assertEqual(g.events[-1]['type'],'global_replan')
    def test_history_transit_and_return(self):
        f={(x,0) for x in range(5)}
        for method in ('TRACE','CAP'):
            r=solve(c(f,{(4,0)},{(0,0)},(1,0)),method,2);self.assertEqual(r['status'],'complete');self.assertEqual(r['route'][-1],(0,0));self.assertIn((4,0),r['route'])
    def test_empty_task_returns(self):
        for method in ('TRACE','CAP'):
            r=solve(c({(x,0) for x in range(3)},set(),s=(2,0)),method,2);self.assertEqual(r['status'],'complete');self.assertEqual(len(r['route'])-1,2)
    def test_current_auto_capture(self):
        for method in ('TRACE','CAP'):self.assertEqual(solve(c({(0,0)}),method,2)['route'],[(0,0)])
    def test_virtual_terminal_not_claimed_by_plan(self):
        f={(x,0) for x in range(5)};r=solve(c(f,{(0,0),(2,0),(4,0)},{(2,0)},(2,0)), 'TRACE',2)
        self.assertEqual(r['status'],'complete');p=r['plans'][0];self.assertEqual(p['end_source'],'next_region_virtual_center');self.assertEqual(p['executed_order'],p['order'][:-1])
    def test_budget_failure_no_fallback(self):
        for method in ('TRACE','CAP'):
            r=solve(c({(0,0),(1,0)},resource=1),method,2);self.assertEqual(r['status'],'resource_exceeded');self.assertFalse(r['route']);self.assertFalse(r['global_completion'])
    def test_deferred_not_completed(self):
        case=c({(0,0),(1,0)});case['published_targets'].append((2,0))
        for method in ('TRACE','CAP'):self.assertEqual(solve(case,method,2)['deferred'],[(2,0)])
    def test_covered_newly_blocked_preserved(self):
        case=c({(0,0),(1,0)},h={(2,0)})
        for method in ('TRACE','CAP'):self.assertEqual(solve(case,method,2)['deferred'],[])
    def test_unreachable_refused(self):
        for method in ('TRACE','CAP'):
            r=solve(c({(0,0),(2,0)}),method,2);self.assertEqual(r['status'],'unreachable');self.assertFalse(r['route'])
    def test_deadline_exact(self):
        for method in ('TRACE','CAP'):
            v=[0]
            def hook(stage):v[0]=2
            r=solve(c({(0,0)}),method,2,clock=lambda:v[0],checkpoint_hook=hook);self.assertEqual(r['status'],'deadline');self.assertFalse(r['route'])
if __name__=='__main__':unittest.main()
