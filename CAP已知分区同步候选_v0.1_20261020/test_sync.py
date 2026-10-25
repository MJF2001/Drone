import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'runtime'))
from known_sync import KnownMapCapGraph
from primitives import Metric,Deadline
from checks import audit

class Tests(unittest.TestCase):
    def graph(self,points):
        return KnownMapCapGraph(set(points),Metric({(x,y) for x in range(8) for y in range(5)}),(0,0))
    def apply(self,g,p,current=(0,0)):
        before=g.snapshot(); g.sync(set(p),current); audit(before,g.snapshot(),p)
    def test_split(self):
        g=self.graph([(0,0),(1,0),(2,0)]); self.apply(g,[(0,0),(2,0)])
        self.assertEqual(len(g.order),2);self.assertEqual(len(g.events[-2]['replacements']),1)
    def test_empty(self):
        g=self.graph([(0,0)]);self.apply(g,[]);self.assertEqual(g.order,[])
    def test_nochange(self):
        g=self.graph([(0,0),(1,0)]);n=len(g.events);self.apply(g,[(0,0),(1,0)])
        self.assertEqual(len(g.events),n)
    def test_connected_shrink(self):
        g=self.graph([(0,0),(1,0),(2,0)]);ids=list(g.order);self.apply(g,[(1,0),(2,0)])
        self.assertEqual(g.order,ids)
    def test_two_splits_one_replan(self):
        p={(x,y) for x in range(3) for y in (0,3)};g=self.graph(p);n=len(g.events)
        self.apply(g,p-{(1,0),(1,3)})
        self.assertEqual(len(g.order),4)
        self.assertEqual(sum(e['type']=='global_replan' for e in g.events[n:]),1)
    def test_idempotence(self):
        g=self.graph([(0,0),(1,0),(2,0)]);self.apply(g,[(0,0),(2,0)])
        a=copy.deepcopy(g.__dict__); self.apply(g,[(0,0),(2,0)])
        self.assertEqual(g.snapshot(),dict(order=a['order'],nodes=[dict(id=i,A=sorted(n['A']),R=sorted(n['R']),center=n['center'],state=n['state']) for i,n in a['nodes'].items()]))
        self.assertEqual(g.events,a['events'])
    def test_resurrection_reject(self):
        g=self.graph([(0,0),(1,0)]);self.apply(g,[(0,0)]);old=g.snapshot()
        with self.assertRaises(ValueError):g.sync({(0,0),(1,0)},(0,0))
        self.assertEqual(g.snapshot(),old)
    def test_unknown_reject(self):
        g=self.graph([(0,0)]);g.unknown={(1,0)}
        with self.assertRaises(ValueError):g.sync({(0,0)},(0,0))
    def test_bad_current_reject(self):
        g=self.graph([(0,0)])
        with self.assertRaises(ValueError):g.sync({(0,0)},(99,0))
    def test_deadline_atomic(self):
        for stage in ('known_sync_node','components','matrix','known_sync_commit'):
            g=self.graph([(0,0),(1,0),(2,0)]);old=g.snapshot();events=copy.deepcopy(g.events);nid=g.next_id
            def check(s):
                if s==stage:raise Deadline(s)
            g.metric.check=check
            with self.assertRaises(Deadline):g.sync({(0,0),(2,0)},(1,0))
            self.assertEqual(g.snapshot(),old);self.assertEqual(g.events,events);self.assertEqual(g.next_id,nid);self.assertEqual(g.current,(0,0))
    def test_three_way_cut(self):
        g=self.graph([(0,1),(1,1),(2,1),(1,2)]);self.apply(g,[(0,1),(2,1),(1,2)])
        self.assertEqual(len(g.order),3)
    def test_empty_initial(self):
        g=self.graph([]);self.apply(g,[])
if __name__=='__main__':unittest.main(verbosity=2)
