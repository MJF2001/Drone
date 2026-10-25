import sys,unittest,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'runtime'))
from test_v05 import Tests as SemanticTests
from history_core.rcg import RCG
from history_core.public_map import PublicMap
from history_core.planner import optimize_tsp
from equivalent_tsp import CertifiedCosts,optimize_equivalent

def graph(which):
    f={(x,y) for x in range(6) for y in range(5)}
    if which==1:f-={(2,y) for y in (1,2,3)}
    if which==2:f-={(x,2) for x in (1,2,3,4)}
    m=PublicMap();m.update({p:True for p in f});g=RCG(m)
    for p in sorted(f):g.insert(p)
    g.expand(f);return g
def reference(g,points):
    cost={};paths={}
    for a in sorted(points):
        for b in sorted(points):
            if (a,b) in cost:continue
            p,c=g.path(a,b);cost[a,b]=cost[b,a]=c;paths[a,b]=p;paths[b,a]=p[::-1]
    return cost,paths
class EfficiencyTests(unittest.TestCase):
    def check_graph(self,which):
        g=graph(which);points=set(g.nodes);old,paths=reference(g,points);new=CertifiedCosts(g,points,lambda _:None)
        self.assertTrue(new.tight)
        for a in points:
            for b in points:
                self.assertLessEqual(abs(old[a,b]-new.approx(a,b)),new.error(a,b))
                self.assertEqual(new.value(a,b),old[a,b]);self.assertEqual(new.path(a,b),paths[a,b])
    def test_cost_open(self):self.check_graph(0)
    def test_cost_vertical_obstacle(self):self.check_graph(1)
    def test_cost_horizontal_obstacle(self):self.check_graph(2)
    def check_tour(self,endkind):
        for which in range(3):
            g=graph(which);points=set(g.nodes);old,_=reference(g,points);start=min(points)
            end=None if endkind=='free' else start if endkind=='return' else max(points)
            expected=optimize_tsp(points,start,end,old)
            c=CertifiedCosts(g,points,lambda _:None);actual=optimize_equivalent(points,start,end,c,lambda _:None)
            self.assertEqual(actual,expected)
    def test_free_end(self):self.check_tour('free')
    def test_fixed_end(self):self.check_tour('fixed')
    def test_return_end(self):self.check_tour('return')
    def test_checkpoint_propagation(self):
        class Stop(Exception):pass
        seen=[]
        def check(s):
            seen.append(s)
            if s=='tsp_row_search':raise Stop
        g=graph(0)
        with self.assertRaises(Stop):CertifiedCosts(g,set(g.nodes),check)
        self.assertIn('tsp_costs',seen)
    def test_unsupported_weight_rejected(self):
        g=graph(0);a=min(g.edges);b=min(g.edges[a]);g.edges[a][b]=g.edges[b][a]=9.
        with self.assertRaises(ValueError):CertifiedCosts(g,set(g.nodes),lambda _:None)
if __name__=='__main__':unittest.main()
