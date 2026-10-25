import sys,json,unittest,hashlib,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'runtime'))
from target_contract import Session,TargetContractError
from audit_contract import audit
EVIDENCE=[]
def case():return dict(free=[(x,0) for x in range(6)],targets=[(x,0) for x in range(6)],covered=[(0,0)],current=(1,0),base=(0,0),distance_budget=100)
class Tests(unittest.TestCase):
    def record(self,c,r):
        # Save the actual API result, never manufacture a global success.
        c=json.loads(json.dumps(c));r=json.loads(json.dumps(r));check=audit(c,r);EVIDENCE.append(dict(test=self.id(),input=c,result=r,check=check));return r
    def session(self):c=case();return c,Session(c)
    def bind(self,s,p=(0,0)):s.bind_target(p,source='provided_resume_state',reference='synthetic explicit caller fixture; NOT author state')
    def test_missing_target_no_guess(self):
        c,s=self.session();r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['status'],'missing_resume_target');self.assertEqual(len(r['path']),1)
    def test_outside_target_preserved(self):
        c,s=self.session();self.bind(s,(5,0));r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['current'],[5,0]);self.assertEqual(r['status'],'region_complete_transition_required')
    def test_covered_target_is_interface(self):
        c,s=self.session();self.bind(s,(0,0));r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['current'],[0,0]);self.assertIn([0,0],r['covered'])
    def test_bound_target_cannot_be_overwritten(self):
        c,s=self.session();self.bind(s)
        with self.assertRaises(TargetContractError):self.bind(s,(3,0))
    def test_entry_preserves_target_even_when_crossed(self):
        c=case();c.update(current=(0,0),covered=[]);s=Session(c);self.bind(s,(1,0));token=dict(s.state)
        self.record(c,s.enter_region([(0,0),(1,0),(2,0)]));self.assertEqual(s.state,token)
        r=self.record(c,s.cover_region({(2,0),(3,0)}));self.assertEqual(r['current'],[1,0]);self.assertEqual(r['target_state']['generation'],1)
    def test_no_automatic_next_target(self):
        c,s=self.session();self.bind(s);self.record(c,s.cover_region({(1,0),(2,0)}));r=self.record(c,s.cover_region({(3,0),(4,0)}));self.assertEqual(r['status'],'next_target_transition_required')
    def test_explicit_next_transition(self):
        c,s=self.session();self.bind(s);self.record(c,s.cover_region({(1,0),(2,0)}));s.bind_target((5,0),source='explicit_next_transition',reference='caller next-state decision')
        r=self.record(c,s.enter_region([(0,0),(1,0),(2,0),(3,0)]));self.assertEqual(r['target_state']['generation'],2)
    def test_blocked_or_unknown_target_rejected(self):
        c,s=self.session()
        with self.assertRaises(TargetContractError):self.bind(s,(9,0))
    def test_provenance_required(self):
        c,s=self.session()
        with self.assertRaises(TargetContractError):s.bind_target((0,0),source='provided_resume_state',reference='')
    def test_entry_policy_not_invented(self):
        c,s=self.session();self.bind(s);r=self.record(c,s.cover_region({(3,0),(4,0)}));self.assertEqual(r['status'],'entry_contract_required')
    def test_disconnected_residual_requires_update(self):
        c,s=self.session();self.bind(s);r=self.record(c,s.cover_region({(0,0),(1,0),(2,0)}));self.assertEqual(r['status'],'partition_update_required');self.assertEqual(len(r['parts']),2)
    def test_no_virtual_collection_outside_path(self):
        c,s=self.session();self.bind(s,(0,0));r=self.record(c,s.cover_region({(1,0),(2,0)}));self.assertIn([5,0],r['pending'])
    def test_deadline_keeps_actual_prefix_and_state(self):
        c=case();clock={'t':0}
        def hook(stage):
            if stage=='move_after':clock['t']=2
        s=Session(c,2,clock=lambda:clock['t'],hook=hook);self.bind(s);r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['status'],'deadline');self.assertEqual(len(r['path']),2);self.assertEqual(r['target_state']['phase'],'bound')
    def test_resource_budget_limits_prefix(self):
        c=case();c['distance_budget']=1;s=Session(c);self.bind(s);r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['status'],'resource_exceeded');self.assertEqual(len(r['path']),2)
    def test_local_completion_not_global_success(self):
        c=case();c['targets']=[(1,0),(2,0)];c['covered']=[];s=Session(c);self.bind(s,(2,0));r=self.record(c,s.cover_region({(1,0),(2,0)}));self.assertFalse(r['global_complete']);self.assertNotEqual(r['current'],list(c['base']))
    def test_pinned_tsp_primitives_unchanged(self):
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(sha(HERE/'runtime/primitives.py'),sha(HERE.parent/'CAP单源查询修正_v0.2_20261020/runtime/primitives.py'))
    def test_free_but_unreachable_interface(self):
        c=case();c['free'].append((10,0));s=Session(c);self.bind(s,(10,0));r=self.record(c,s.cover_region({(1,0),(2,0)}));self.assertEqual(r['status'],'unreachable_interface')
    def test_inside_endpoint_still_allowed(self):
        c,s=self.session();self.bind(s,(3,0));r=self.record(c,s.cover_region({(1,0),(2,0),(3,0)}));self.assertEqual(r['current'],[3,0])
    def test_invalid_time_budget(self):
        for b in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):Session(case(),b)
    def test_blocked_history_retained_and_unfinished_deferred(self):
        c=case();c['covered'].append((8,0));c['published_targets']=c['targets']+[(8,0),(9,0)];s=Session(c);self.bind(s);r=self.record(c,s.cover_region({(1,0),(2,0)}));self.assertIn([8,0],r['covered']);self.assertEqual(r['deferred'],[[9,0]])
if __name__=='__main__':
    outcome=unittest.main(exit=False,verbosity=2)
    (HERE/'mechanism_cases.json').write_text(json.dumps(EVIDENCE,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(0 if outcome.result.wasSuccessful() else 1)
