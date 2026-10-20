import unittest
from geometry import World, KnownMap, coverage_audit, connected, segment_free
from planner import CStar, optimize_tsp
from rcg import RCG
from run import scenarios

class StrictCStarTests(unittest.TestCase):
    def test_tsp_keeps_fixed_start_and_free_or_fixed_end(self):
        points={(0,0),(0,1),(1,0),(1,1)}
        cost={(a,b):abs(a[0]-b[0])+abs(a[1]-b[1]) for a in points for b in points}
        for end in (None,(1,1),(0,0)):
            order,before,after=optimize_tsp(points,(0,0),end,cost)
            self.assertEqual(order[0],(0,0))
            self.assertEqual(set(order),points)
            if end is not None:
                self.assertEqual(order[-1],end)
            self.assertLessEqual(after,before)

    def test_two_node_tsp_does_not_drop_fixed_end(self):
        a,b=(0,0),(0,1)
        costs={(x,y):float(x!=y) for x in (a,b) for y in (a,b)}
        order,before,after=optimize_tsp({a,b},a,b,costs)
        self.assertEqual(order,[a,b])
        self.assertEqual((before,after),(1.,1.))

    def test_coverage_audit_detects_unswept_area_and_corner_collision(self):
        audit=coverage_audit({(0,0),(1,0),(2,0)},[(0,0)],rc=.75)
        self.assertLess(audit['area_sample_coverage'],1.)
        self.assertLessEqual(audit['certified_area_lower_bound'],audit['area_sample_coverage'])
        self.assertFalse(segment_free((0,0),(1,1),{(0,0),(1,1)}))

    def test_both_open_neighbors_keep_state_and_long_left_departure_adds_link(self):
        known=KnownMap()
        known.update({(x,y):True for x in range(3) for y in range(5)})
        graph=RCG(known)
        for p in ((1,0),(1,2),(1,4),(0,2)):
            graph.insert(p)
        graph.expand(set(graph.nodes))
        graph.update_state((1,2),(0,2))
        self.assertTrue(graph.is_open((1,2)))
        graph.nodes[1,0].state='Cl'
        graph.update_state((1,2),(0,2))
        self.assertFalse(graph.is_open((1,2)))
        self.assertEqual(graph.nodes[1,3].kind,'link')
        self.assertIn((1,3),graph.edges[1,4])

    def test_new_node_splits_old_lap_edge(self):
        world=World({(0,y) for y in range(5)}|{(1,y) for y in range(5)})
        known=type('K',(),{})()
        known.free=set(world.free); known.new_free=set(); known.cells={p:True for p in world.free}
        known.feasible=lambda a,b: segment_free(a,b,known.free)
        graph=RCG(known)
        graph.insert((0,0)); graph.insert((0,4)); graph.connect((0,0),(0,4))
        graph.insert((0,2)); graph.expand({(0,2)})
        self.assertIn((0,2),graph.edges[(0,0)])
        self.assertIn((0,2),graph.edges[(0,4)])
        self.assertNotIn((0,4),graph.edges[(0,0)])

    def test_unknown_side_pocket_is_not_used_before_sensor_reveals_it(self):
        free={(x,y) for x in range(8) for y in range(8)}-{(4,y) for y in range(6)}
        world=World(free,radius=2)
        planner=CStar((1,1),world.observe,seed=0,holes=True).run()
        self.assertEqual(planner.status,'graph_exhausted')
        known={}
        self.assertEqual(len(planner.path),len(planner.observations))
        for i,(pose,observation) in enumerate(zip(planner.path,planner.observations)):
            if i:
                # No access to this pose's or any future observation yet.
                self.assertTrue(segment_free(planner.path[i-1],pose,
                                             {p for p,v in known.items() if v}))
            for x,y,v in observation:
                known[x,y]=bool(v)
        self.assertNotIn((6,1),{(x,y) for x,y,v in planner.observations[0] if v})

    def test_opaque_corner_does_not_reveal_diagonal_free_cell(self):
        # Test all orientations: visibility must not depend on coordinate order.
        for sx in (-1,1):
            for sy in (-1,1):
                world=World({(0,0),(sx,sy)},radius=2)
                observation=world.observe((0,0))
                self.assertNotIn((sx,sy),observation)
                self.assertFalse(observation[sx,0])
                self.assertFalse(observation[0,sy])

    def test_static_occupancy_cannot_change_silently(self):
        known=KnownMap();known.update({(0,0):True})
        with self.assertRaises(ValueError):
            known.update({(0,0):False})

    def test_existing_sample_is_retained_as_link_anchor(self):
        known=KnownMap()
        known.update({(x,y):True for x in range(3) for y in range(5)})
        graph=RCG(known)
        for p in ((1,0),(1,1),(1,4),(0,0)):
            graph.insert(p)
        graph.expand(set(graph.nodes))
        graph.update_state((1,0),(0,0))
        self.assertEqual(graph.nodes[1,1].kind,'link')
        graph.prune((0,0))
        self.assertTrue(graph.is_open((1,1)))
        graph.validate((0,0))

    def test_short_sensor_radius_regressions(self):
        for radius,seed in ((1,0),(2,0),(2,1)):
            _,free,start,_,_=list(scenarios(seed))[-1]
            for holes in (False,True):
                planner=CStar(start,World(free,radius).observe,seed=seed,holes=holes).run()
                self.assertEqual(planner.status,'graph_exhausted',getattr(planner,'error',None))
                audit=coverage_audit(free,planner.path)
                self.assertEqual(audit['collisions'],0)
                self.assertEqual(audit['area_sample_coverage'],1.)
                self.assertEqual(audit['certified_area_lower_bound'],1.)

    def test_regression_maps_have_complete_continuous_coverage(self):
        for seed in range(3):
            for name,free,start,_,_ in scenarios(seed):
                if seed and name!='clutter':
                    continue
                planner=CStar(start,World(free,5).observe,seed=seed,holes=True).run()
                audit=coverage_audit(free,planner.path,rc=.75,subdivisions=4)
                self.assertEqual(planner.status,'graph_exhausted',(seed,name,getattr(planner,'error',None)))
                self.assertEqual(audit['collisions'],0,(seed,name))
                self.assertEqual(audit['area_sample_coverage'],1.0,(seed,name,audit))
                self.assertEqual(audit['certified_area_lower_bound'],1.0,(seed,name,audit))

if __name__=='__main__':
    unittest.main()
