import random,unittest
from model import Snapshot,Geometry
from bfs_metric_geometry import BFSMetricGeometry
from structure_candidates import solve_candidate


class BatchedDistanceTests(unittest.TestCase):
    def scene(self):
        free=frozenset((x,y) for x in range(7) for y in range(5))-{(3,1),(3,2),(3,3)}
        return Snapshot('ties',free,free,frozenset(),(0,0),(0,0),(),0,300)

    def test_interleaved_queries_preserve_distances_and_exact_paths(self):
        s=self.scene();old=Geometry(s);new=BFSMetricGeometry(s)
        points=sorted(s.free);rng=random.Random(1011)
        for _ in range(1200):
            a,b=rng.choice(points),rng.choice(points)
            if rng.random()<.7:
                self.assertEqual(old.distance(a,b),new.distance(a,b))
            else:
                self.assertEqual(old.path(a,b),new.path(a,b))
        for a in points:
            for b in points:
                self.assertEqual(old.path(a,b),new.path(a,b))

    def test_complete_search_returns_same_route(self):
        s=self.scene()
        old=solve_candidate(s,'P2_SHARED',20,77)
        new=solve_candidate(s,'P2_SHARED',20,77,geometry_class=BFSMetricGeometry)
        self.assertEqual(old['route'],new['route'])
        self.assertTrue(new['audit']['valid'])


if __name__=='__main__':unittest.main()
