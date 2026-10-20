from pathlib import Path
import json,sys,time
from types import SimpleNamespace
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(D/'source_snapshot'))
import portable_frozen,local_then_all as combo,fixed_scope_candidate as fixed,fixed_scope_original as old
from model import Snapshot
from audit import audit
from road_range_candidate_20261015 import digest
from verify import check_raw
LED=D/'synthetic_calls.jsonl'
def call(name,fn):
 count=len(LED.read_text().splitlines()) if LED.exists() else 0;assert count<40;t=time.perf_counter()
 try:r=fn();(D/f'synthetic_{count:02d}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');return r
 finally:
  with LED.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(index=count,name=name,seconds=time.perf_counter()-t))+'\n')
def main():
 for name,free,route in [('rectangle',[(x,y) for x in range(3) for y in range(3)],[(0,0),(0,1),(1,1),(1,0),(2,0),(2,1),(2,0),(1,0),(0,0)]),('elbow',[(0,0),(1,0),(2,0),(3,0),(0,1),(0,2)],[(0,0),(1,0),(2,0),(3,0),(2,0),(1,0),(0,0)])]:
  initial=set(route)-{(0,0)};s=Snapshot(name,frozenset(free),frozenset(set(free)-{(0,0)}),frozenset(),(0,0),(0,0),tuple(route),0,100)
  for seed in (0,1):
   for scope in ('R_PLUS1','R_ALL'):
    a=call(name+str(seed)+'_old_'+scope,lambda:old.solve(s,initial,'LITERAL',2,seed,scope_name=scope));b=call(name+str(seed)+'_fix_'+scope,lambda:fixed.solve(s,initial,'LITERAL',2,seed,scope_name=scope));assert a['route']==b['route'] and a['source']==b['source'] and a['core_route']==b['core_route']
   r=call(name+str(seed)+'_combo',lambda:combo.solve(s,initial,'LOCAL_THEN_ALL',2,seed));assert audit(s,r['route'])['valid'];assert r['solver_subcalls']==2
 free=frozenset((x,y) for x in range(3) for y in range(2));long=((0,0),(0,1),(1,1),(1,0),(2,0),(1,0),(0,0));short=((0,0),(1,0),(0,0));s=Snapshot('stub',free,frozenset({(1,0)}),frozenset(),(0,0),(0,0),long,0,100)
 scenarios=['early','soft_overrun','late_first','better','worse','both_fail','skip_all','first_fail','second_fail','empty_return'];original_time=combo.time;original_solve=combo.fixed_solve
 for scenario in scenarios:
  clock=[0.];seen=[]
  def stub(s,initial,method,budget,seed,**kw):
   scope=kw['scope_name'];seen.append((scope,budget,seed));first=scope=='R_PLUS1'
   if (first and scenario in ['late_first','skip_all']):clock[0]=.6 if scenario=='late_first' else 1.1
   if scenario!='both_fail' and not (first and scenario=='first_fail') and not (not first and scenario=='second_fail'):
    route=short if (scenario=='better' and not first) or (scenario=='worse' and first) else long
    at=clock[0];kw['on_candidate'](dict(label='stub',source_scope=None,route=route,patch=None,cfg=None,valid=True,validation_complete_public_elapsed=at,public_elapsed=at,before_deadline=at<=kw['absolute_deadline'],steps=len(route)-1,route_sha256=digest(route)))
   if first:clock[0]=max(clock[0],.7 if scenario=='soft_overrun' else .1)
   else:clock[0]+=.05
   return dict(status='finished',detail=dict(public_t0=0,absolute_deadline=kw['absolute_deadline'],range_plan=None))
  combo.time=SimpleNamespace(perf_counter=lambda:clock[0]);combo.fixed_solve=stub
  try:r=call('stub_'+scenario,lambda:combo.solve(s,{(1,0)},'LOCAL_THEN_ALL',1,7))
  finally:combo.time=original_time;combo.fixed_solve=original_solve
  assert seen[0][0]=='R_PLUS1' and all(x[2]==7 for x in seen)
  if scenario=='soft_overrun':assert abs(r['stages'][1]['available_seconds']-.3)<1e-8
  if scenario=='early':assert r['stages'][1]['available_seconds']>.5
  if scenario=='late_first':assert not any(e['accepted'] for e in r['candidate_events'] if e['stage']=='local')
  if scenario=='skip_all':assert r['stages'][1]['status']=='skipped'
  if scenario=='both_fail':assert not r['route']
  if scenario=='better':assert len(r['route'])==3 and r['source'].startswith('all:')
  if scenario=='worse':assert len(r['route'])==3 and r['source'].startswith('local:')
 # Real empty-task route-to-base, one additional call.
 s=Snapshot('empty',frozenset({(0,0),(1,0),(2,0)}),frozenset({(0,0),(1,0),(2,0)}),frozenset({(0,0),(1,0),(2,0)}),(2,0),(0,0),((2,0),(1,0),(0,0)),0,100)
 r=call('real_empty_return',lambda:combo.solve(s,set(s.targets),'LOCAL_THEN_ALL',2,0));assert len(r['route'])==3
 (D/'synthetic_results.json').write_text(json.dumps(dict(status='PASS',top_level_calls=len(LED.read_text().splitlines()),real_calls=21,stub_calls=10,tests=scenarios,fixed_equivalent=True),indent=2),encoding='utf-8');print('PASS 31 synthetic calls')
if __name__=='__main__':main()
