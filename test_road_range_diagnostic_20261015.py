from pathlib import Path
import copy,unittest
import portable_frozen
from model import Snapshot,DeadlineExceeded
from road_range_candidate_20261015 import service_blocks,range_plan,solve,RANGES
from range_interface_probe_20261015 import fixtures
from prepare_road_range_diagnostic_20261015 import snapshot
ROOT=Path(__file__).resolve().parent

class RoadRangeTests(unittest.TestCase):
    def setUp(self):self.cases={c['name']:c for c in fixtures()}
    def initial(self,c):return set(map(tuple,c['metadata']['initial_targets']))
    def test_engine_only_two_substitutions(self):
        p=portable_frozen.FROZEN/'source/p2_search_audit.py';s=p.read_text(encoding='utf-8')
        expected='# Experimental range adapter: only adds an optional complete-route acceptance callback.\n'+s.replace(
            'def solve(s,budget,variant,seed):','def solve(s,budget,variant,seed,accept=None):').replace(
            "valid=route and single_cell_audit(s,route)['valid']","valid=route and (accept(route,label) if accept is not None else single_cell_audit(s,route)['valid'])")
        self.assertEqual(expected,(ROOT/'range_p2_engine_20261015.py').read_text(encoding='utf-8'))
    def test_default_engine_matches_frozen(self):
        import p2_search_audit,range_p2_engine_20261015
        c=self.cases['open_boundary_tradeoff'];s=snapshot(c)
        a=p2_search_audit.solve(s,30,'multi',7);b=range_p2_engine_20261015.solve(s,30,'multi',7)
        for k in ('route','source','status','core_finished'):self.assertEqual(a[k],b[k])
    def test_blocks_partition_old_first_service(self):
        c=self.cases['open_boundary_tradeoff'];s=snapshot(c);b=service_blocks(s,self.initial(c))
        cells=[p for x in b for p in x['cells']]
        self.assertEqual(len(cells),len(set(cells)));self.assertEqual(set(cells),self.initial(c)-s.covered-{s.current})
    def test_blocks_are_straight(self):
        for c in self.cases.values():
            for b in service_blocks(snapshot(c),self.initial(c)):
                vecs={(q[0]-p[0],q[1]-p[1]) for p,q in zip(b['cells'],b['cells'][1:])}
                self.assertLessEqual(len(vecs),1)
    def test_scopes_nested(self):
        for c in self.cases.values():
            p=range_plan(snapshot(c),self.initial(c))['plans'];last=None
            for m in RANGES:
                x=p[m]
                if last:self.assertLessEqual(x['left'],last['left']);self.assertGreaterEqual(x['right'],last['right'])
                last=x
    def test_all_cut_is_full(self):
        c=self.cases['open_boundary_tradeoff'];p=range_plan(snapshot(c),self.initial(c))['plans']['R_ALL']
        self.assertEqual((p['left'],p['right']),(0,len(c['old_route'])-1))
    def test_all_collisions_enclosed(self):
        c=self.cases['return_tail_broken'];s=snapshot(c);plan=range_plan(s,self.initial(c));x=plan['plans']['R_SEED']
        self.assertTrue(all(x['left']<i<x['right'] for i in plan['old_collision_indices']))
        self.assertTrue(set(s.old_route[:x['left']+1])|set(s.old_route[x['right']:])<=s.free)
    def test_new_targets_in_patch_or_kept_part(self):
        c=self.cases['new_targets_fixed_domain'];s=snapshot(c);p=range_plan(s,self.initial(c))
        for x in p['plans'].values():
            union=set(map(tuple,x['required']))|set(s.old_route[:x['left']+1])|set(s.old_route[x['right']:])|s.covered
            self.assertTrue(s.targets<=union)
    def test_no_change_empty_seed(self):
        c=copy.deepcopy(self.cases['open_boundary_tradeoff']);c['free']=c['metadata']['initial_free'];c['metadata']['obstacles']=[]
        p=range_plan(snapshot(c),self.initial(c));self.assertEqual(p['seed_span'],(0,0))
    def test_plan_deadline(self):
        c=self.cases['loop_AB_sufficient']
        with self.assertRaises(DeadlineExceeded):range_plan(snapshot(c),self.initial(c),0)
    def test_plan_deterministic(self):
        c=self.cases['new_targets_fixed_domain'];self.assertEqual(range_plan(snapshot(c),self.initial(c)),range_plan(snapshot(c),self.initial(c)))
    def test_input_unchanged(self):
        c=self.cases['open_boundary_tradeoff'];before=copy.deepcopy(c);s=snapshot(c);solve(s,self.initial(c),'R_SEED',1,0);self.assertEqual(c,before)
    def test_routes_and_core_audit(self):
        for c in self.cases.values():
            for m in RANGES:
                r=solve(snapshot(c),self.initial(c),m,2,0)
                self.assertTrue(r['independent_audit']['valid'])
                if r['core_route']:self.assertTrue(r['core_independent_audit']['valid'])
    def test_accept_before_deadline(self):
        c=self.cases['open_boundary_tradeoff'];r=solve(snapshot(c),self.initial(c),'R_ALL',.2,0)
        self.assertTrue(all(x['seconds']<=r['budget'] for x in r['detail']['acceptances']+r['detail']['core_acceptances']))
    def test_core_literal_parts(self):
        c=self.cases['new_targets_fixed_domain'];s=snapshot(c);r=solve(s,self.initial(c),'R_SEED',2,0)
        x=r['detail']['range_plan']['plans']['R_SEED'];self.assertTrue(r['core_route'])
        self.assertEqual(r['core_route'],s.old_route[:x['left']]+r['core_patch']+s.old_route[x['right']+1:])
    def test_resource_shortage_no_false_success(self):
        c=copy.deepcopy(self.cases['loop_AB_sufficient']);c['distance_budget']=1;r=solve(snapshot(c),self.initial(c),'R_ALL',1,0)
        self.assertFalse(r['route'])
    def test_all_matches_P2_when_finished_tiny(self):
        c=self.cases['open_boundary_tradeoff'];s=snapshot(c)
        a=portable_frozen.solve(s,self.initial(c),'P2_MULTI',10,0,portable_frozen.PROFILE)
        b=solve(s,self.initial(c),'R_ALL',10,0);self.assertEqual(len(a['route']),len(b['route']))
    def test_negative_budget(self):
        c=self.cases['loop_AB_sufficient'];r=solve(snapshot(c),self.initial(c),'R_SEED',-1,0);self.assertFalse(r['route'])

if __name__=='__main__':unittest.main()
