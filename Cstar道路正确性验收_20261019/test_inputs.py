import unittest,copy,ast
import tempfile,sys,types,json
from unittest.mock import patch
from pathlib import Path
from audit_inputs import check_case,check_history
def fixture():return dict(split='development',radius=0,free=[[0,0],[1,0],[2,0]],targets=[[1,0],[2,0]],covered=[],published_targets=[[1,0],[2,0]],deferred_targets=[],current=[0,0],base=[0,0],distance_budget=4)
class Gates(unittest.TestCase):
    def test_good_witness(self):self.assertTrue(check_case(fixture(),[[0,0],[1,0],[2,0],[1,0],[0,0]])['physical_feasible'])
    def test_missing_target(self):
        with self.assertRaisesRegex(AssertionError,'incomplete'):check_case(fixture(),[[0,0]])
    def test_wrong_deferred_ledger(self):
        c=fixture();c['deferred_targets']=[[9,9]]
        with self.assertRaisesRegex(AssertionError,'ledger'):check_case(c,[[0,0]])
    def test_historical_newly_blocked_kept(self):
        c=fixture();c['published_targets'].append([9,9]);c['covered'].append([9,9])
        check_case(c,[[0,0],[1,0],[2,0],[1,0],[0,0]])
    def test_budget_underflow(self):
        c=fixture();c['distance_budget']=3
        with self.assertRaisesRegex(AssertionError,'resource'):check_case(c,[[0,0],[1,0],[2,0],[1,0],[0,0]])
    def test_nonunit_witness(self):
        with self.assertRaisesRegex(AssertionError,'nonunit'):check_case(fixture(),[[0,0],[2,0],[0,0]])
    def test_future_or_holdout_denied(self):
        c=fixture();c['split']='holdout'
        with self.assertRaises(AssertionError):check_case(c,[[0,0]])
    def test_scripts_parse_without_execution(self):
        for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    def test_worker_whitelist_with_stub_only(self):
        import run
        c=fixture();c.update(witnesses=['SECRET'],old_route=['SECRET'],future_events=['SECRET'],map_id='SECRET')
        keys=['free','targets','covered','current','base','published_targets','distance_budget']
        protocol=dict(core_input_whitelist=keys,algorithm_source='Cstar历史适配验收_20261019/专项验收_v0.3/runtime')
        job=dict(input='unused.json',budget_seconds=20,seed=20261018,max_iterations=20000)
        def stub(request,budget,seed,**kw):
            self.assertEqual(set(request),set(keys));self.assertEqual(budget,20);self.assertEqual(kw['max_iterations'],20000)
            return dict(status='stub_only',route=[])
        before=list(sys.path)
        try:
            with tempfile.TemporaryDirectory() as d,patch.object(run,'read',side_effect=[job,protocol,c]),patch.object(run,'sha',return_value='stub'),patch.dict(sys.modules,{'history_adapter':types.SimpleNamespace(solve=stub)}):
                self.assertEqual(run.worker(Path(d)/'job.json',Path(d)/'out.json'),0)
        finally:sys.path[:]=before
if __name__=='__main__':unittest.main()
