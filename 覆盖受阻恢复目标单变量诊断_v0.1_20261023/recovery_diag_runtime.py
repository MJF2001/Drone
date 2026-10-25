"""Production imports: frozen PPCPP and contract only; no experiment references."""
import sys,time,json,math,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'基线复现准备_20261019'))
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import recovery_diag_native as native
from recovery_diag_hook import Diagnostic
validate=module('last_validation',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py').validate
from model import Snapshot,DeadlineExceeded,NoPath
def snapshot(c):return Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
def run_payload(payload,mode,budget=20,seed=0,*,hook=None,clock=time.perf_counter,geometry=native.UnifiedGeometry,diagnostic_spec=None,target_intervention_enabled=False):
 from recovery_diag_candidate import solve
 begin=clock();deadline=begin+budget;raw=None;phases={};events=[]
 def mark(stage):
  if hook:hook(stage)
  events.append(dict(stage=stage,seconds=clock()-begin)) if hook else None
  if clock()>=deadline:raise DeadlineExceeded()
 try:
  c=json.loads(payload);validate(c);s=snapshot(c);mark('entry');diagnostic=Diagnostic(diagnostic_spec,target_intervention_enabled,clock)
  raw=solve(s,set(map(tuple,c['initial_targets'])),mode,seed,tuple(c['predator']),tuple(c['previous']) if c['previous'] else None,begin,deadline,phases,mark,clock,geometry,diagnostic)
  if raw['status']=='core_complete':diagnostic.finish(raw)
  mark('encode_before');encode_begin=clock();wire=json.dumps({'raw':raw,'diagnostic':diagnostic.export()},ensure_ascii=False,allow_nan=False,separators=(',',':'));phases['encoding']=clock()-encode_begin;mark('encode_after')
 except DeadlineExceeded:
  raw=raw if raw is not None else dict(branches={},trace=[])
  raw.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 elapsed=clock()-begin
 if elapsed>=budget:raw.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 return dict(raw=raw,entry_seconds=elapsed,phase_seconds=phases,eligible=raw['status']=='core_complete' and elapsed<budget,budget=budget,method=mode,seed=seed,injection_events=events,diagnostic=diagnostic.export())
