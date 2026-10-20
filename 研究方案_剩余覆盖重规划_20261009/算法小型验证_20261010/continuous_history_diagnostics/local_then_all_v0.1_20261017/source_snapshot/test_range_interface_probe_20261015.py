import copy,unittest
import range_interface_probe_20261015 as p

class InterfaceTests(unittest.TestCase):
    def setUp(self):self.cases={c['name']:c for c in p.fixtures()}
    def test_all_old_routes_valid_initially(self):
        for c in self.cases.values():
            p.contract(c)
            self.assertLessEqual(set(map(tuple,c['old_route'])),p.pointset(c['metadata'],'initial_free'))
    def test_AB_is_not_map_crop(self):
        c=self.cases['loop_AB_sufficient'];r=p.solve_scope(c,'AB')
        self.assertIn((1,1),r['patch'])
        self.assertNotIn((1,1),[q for b in c['blocks'][:2] for q in b['service']])
    def test_AB_matches_full_in_loop(self):
        c=self.cases['loop_AB_sufficient'];self.assertEqual(p.solve_scope(c,'AB')['steps'],p.solve_scope(c,'ALL')['steps'])
    def test_widening_improves(self):
        c=self.cases['open_boundary_tradeoff'];self.assertLess(p.solve_scope(c,'ABC')['steps'],p.solve_scope(c,'AB')['steps'])
    def test_literal_tail_preserved(self):
        c=self.cases['open_boundary_tradeoff'];r=p.solve_scope(c,'AB');tail=tuple(c['old_route'][r['scope_info']['right']:])
        self.assertEqual(r['route'][-len(tail):],tail)
    def test_return_tail_collision_is_detected(self):
        c=self.cases['return_tail_broken'];r=p.solve_scope(c,'AB')
        self.assertEqual(r['status'],'scope_rejected_preserved_collision')
        self.assertIsNotNone(p.solve_scope(c,'ALL')['route'])
    def test_deferred_not_completed(self):
        c=self.cases['obscured_target'];self.assertIn((4,1),c['metadata']['deferred_targets'])
        self.assertNotIn((4,1),c['covered']);self.assertNotIn((4,1),c['targets'])
        self.assertNotIn((4,1),p.solve_scope(c,'ALL')['route'])
    def test_added_targets_assigned(self):
        c=self.cases['new_targets_fixed_domain'];r=p.solve_scope(c,'AB')
        self.assertTrue({(3,2),(4,2)}<=set(r['scope_info']['required']))
        self.assertTrue({(3,2),(4,2)}<=set(r['patch']))
    def test_input_unchanged(self):
        c=self.cases['loop_AB_sufficient'];before=copy.deepcopy(c);p.solve_scope(c,'AB');self.assertEqual(c,before)
    def test_resource_not_ignored(self):
        c=self.cases['loop_AB_sufficient'];c['distance_budget']=1;self.assertFalse(p.solve_scope(c,'ALL')['resource_satisfied'])
    def test_endpoint_collision_rejected(self):
        c=self.cases['loop_AB_sufficient'];c['free'].remove(c['base'])
        with self.assertRaisesRegex(ValueError,'endpoint_not_free'):p.solve_scope(c,'AB')
    def test_illegal_targets_rejected(self):
        c=self.cases['loop_AB_sufficient'];c['targets'].append((1,0))
        with self.assertRaisesRegex(ValueError,'targets_not_free'):p.solve_scope(c,'AB')
    def test_radius_rejected(self):
        c=self.cases['loop_AB_sufficient'];c['radius']=1
        with self.assertRaisesRegex(ValueError,'radius_not_zero'):p.solve_scope(c,'AB')
    def test_tiny_cap_enforced(self):
        c=self.cases['loop_AB_sufficient'];c['free']+= [(x,10) for x in range(300)]
        with self.assertRaisesRegex(ValueError,'tiny_probe_cap'):p.solve_scope(c,'AB')
    def test_unknown_scope_rejected(self):
        with self.assertRaises(ValueError):p.solve_scope(self.cases['loop_AB_sufficient'],'BAD')
    def test_no_tasks_still_connects(self):
        route,stats=p.exact_patch({(0,0),(1,0),(2,0)},set(),(0,0),(2,0));self.assertEqual(len(route)-1,2)
    def test_unreachable_is_not_fake_route(self):
        route,stats=p.exact_patch({(0,0),(2,0)},{(2,0)},(0,0),(2,0));self.assertIsNone(route)

if __name__=='__main__':unittest.main()
