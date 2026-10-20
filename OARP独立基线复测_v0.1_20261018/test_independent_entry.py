"""Entry-level regressions. Fake engine only; zero SCIP/GLNS calls."""
import unittest
from unittest.mock import patch
import kernel as k

class Clock:
    def __init__(self):self.now=0.0
    def __call__(self):return self.now

class NoHistory(dict):
    def __getitem__(self,key):
        assert key not in ('old_route','old_suffix'),'independent entry read history'
        return super().__getitem__(key)
    def get(self,key,*args):
        assert key not in ('old_route','old_suffix'),'independent entry read history'
        return super().get(key,*args)

class EntryTests(unittest.TestCase):
    def req(self):return NoHistory(F=[(0,0),(1,0)],P=[(1,0)],C=[],current=(0,0),base=(0,0),resource=20,seed=1)
    def run_case(self,req=None,engine=None,auditor=None,clock=None):
        clock=clock or Clock(); req=self.req() if req is None else req
        calls=[]
        def fake_engine(req,method,cap,fragments,budget,grid,ident):
            calls.append(True)
            self.assertEqual(grid.rows,{})
            if engine:return engine(req,method,cap,fragments,budget,grid,ident)
            return {'route':[(0,0),(1,0),(0,0)]},{'core_natural':True}
        with patch.object(k.Grid,'distance',side_effect=AssertionError('unexpected pre-core greedy distance')):
            result=k.entry(req,'RANK0',None,[],'mock',seconds=1,clock=clock,auditor=auditor,engine=fake_engine)
        return result,calls
    def test_engine_starts_without_greedy_or_history(self):
        r,calls=self.run_case();self.assertEqual(len(calls),1);self.assertEqual(r['source'],'core')
        self.assertTrue(r['flags']['within_budget']);self.assertFalse(r['flags']['fallback_selected'])
        self.assertEqual([c['source'] for c in r['candidates']],['core'])
    def test_shorter_old_route_cannot_replace_core(self):
        req=dict(self.req(),old_suffix=[(0,0),(1,0),(0,0)],old_route=[(0,0),(1,0),(0,0)])
        def engine(*args):return {'route':[(0,0),(1,0),(0,0),(1,0),(0,0)]},{'core_natural':True}
        r,calls=self.run_case(req,engine);self.assertEqual(len(calls),1);self.assertEqual(r['audit']['steps'],4)
        self.assertEqual(r['source'],'core')
    def test_missing_core_produces_no_fallback(self):
        r,calls=self.run_case(engine=lambda *a:(None,{'core_natural':False}))
        self.assertEqual(len(calls),1);self.assertEqual(r['route'],[]);self.assertFalse(r['flags']['route_valid'])
    def test_generation_after_deadline_excluded(self):
        clock=Clock()
        def engine(*args):clock.now=1.01;return {'route':[(0,0),(1,0),(0,0)]},{'core_natural':True}
        r,calls=self.run_case(engine=engine,clock=clock)
        self.assertEqual(len(calls),1);self.assertEqual(r['route'],[])
        self.assertEqual(r['diagnostics'][0]['source'],'core');self.assertFalse(r['flags']['within_budget'])
    def test_audit_crossing_deadline_excluded(self):
        clock=Clock()
        def audit(req,route):
            answer=k.audit(req,route)
            if route:clock.now=1.1
            return answer
        r,calls=self.run_case(auditor=audit,clock=clock)
        self.assertEqual(len(calls),1);self.assertEqual(r['route'],[]);self.assertFalse(r['flags']['within_budget'])
    def test_final_audit_in_total_time(self):
        clock=Clock();counter=[]
        def audit(req,route):
            counter.append(True)
            if len(counter)==2:clock.now=1.2
            return k.audit(req,route)
        r,calls=self.run_case(auditor=audit,clock=clock)
        self.assertEqual(len(calls),1);self.assertTrue(r['flags']['route_valid'])
        self.assertFalse(r['flags']['within_budget']);self.assertEqual(r['public_seconds'],1.2)
    def test_over_resource_core_rejected(self):
        req=self.req();req['resource']=1
        r,calls=self.run_case(req);self.assertEqual(len(calls),1);self.assertEqual(r['route'],[])
        self.assertIn('resource',r['diagnostics'][0]['audit']['errors'])
    def test_expired_engine_does_not_use_old_route(self):
        def engine(*args):raise k.Expired('controlled deadline')
        req=dict(self.req(),old_suffix=[(0,0),(1,0),(0,0)])
        r,calls=self.run_case(req,engine);self.assertEqual(len(calls),1);self.assertEqual(r['route'],[])
        self.assertEqual(r['core_detail']['interruption'],'controlled deadline')

if __name__=='__main__':unittest.main(verbosity=2)
