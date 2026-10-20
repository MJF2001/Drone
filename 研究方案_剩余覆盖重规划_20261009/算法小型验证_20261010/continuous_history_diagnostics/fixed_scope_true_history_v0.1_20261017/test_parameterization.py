from pathlib import Path
import sys,json,time
D=Path(__file__).resolve().parent;R=D.parents[3];A=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';S=D/'source_snapshot'
sys.path.insert(0,str(A/'.deps'));sys.path.insert(0,str(S))
import portable_frozen
from model import Snapshot
import outer_connector_candidate_20261016 as historical
import fixed_scope_candidate as candidate
from audit import audit
calls=[]
def run(s,initial,method,seed,scope=None,budget=3):
 if method=='P2_MULTI':x=portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE)
 elif method=='ORIGINAL':x=historical.solve(s,initial,'LITERAL',budget,seed)
 else:x=candidate.solve(s,initial,'LITERAL',budget,seed,scope_name=scope)
 calls.append(dict(shape=s.name,method=method,scope=scope,seed=seed,budget=budget,steps=len(x.get('route',[]))-1,status=x.get('status')))
 return x
try:
 shapes=[('rectangle',[(x,y) for x in range(3) for y in range(2)],[(0,0),(0,1),(1,1),(1,0),(2,0),(2,1),(2,0),(1,0),(0,0)]),('elbow',[(0,0),(1,0),(2,0),(0,1),(0,2)],[(0,0),(1,0),(2,0),(1,0),(0,0),(0,1),(0,2),(0,1),(0,0)])]
 for name,free,old in shapes:
  initial=set(free)-{(0,0)};s=Snapshot(name,frozenset(free),frozenset(initial),frozenset(),(0,0),(0,0),tuple(old),0,100)
  for seed in (0,1):
   baseline=run(s,initial,'P2_MULTI',seed);original=run(s,initial,'ORIGINAL',seed)
   rs={scope:run(s,initial,'PARAMETERIZED',seed,scope) for scope in ['R_SEED','R_PLUS1','R_PLUS2','R_ALL']}
   plus=rs['R_PLUS1'];assert plus['route']==original['route'] and plus['core_route']==original['core_route'] and plus['source']==original['source']
   assert len(rs['R_ALL']['route'])==len(baseline['route']),(name,seed,len(rs['R_ALL']['route']),len(baseline['route']))
   for scope,x in rs.items():
    assert audit(s,x['route'])['valid']
    if x['core_route']:
     cfg=x['detail']['range_plan']['plans'][scope];l,r=cfg['left'],cfg['right'];patch=x['core_patch']
     assert tuple(x['core_route'])==s.old_route[:l]+tuple(patch)+s.old_route[r+1:]
  empty=Snapshot(name+'_empty',s.free,frozenset(),s.targets,s.current,s.base,s.old_route,0,100)
  for scope in ['R_SEED','R_PLUS1','R_PLUS2','R_ALL']:
   x=run(empty,initial,'EMPTY',0,scope);assert audit(empty,x['route'])['valid']
  x=run(s,initial,'DEADLINE',0,'R_ALL',1e-9);assert not x['route'] and x['status']=='deadline'
 print(json.dumps({'status':'PASS','fixture_calls':len(calls)},indent=2))
finally:
 (D/'fixture_calls.json').write_text(json.dumps(calls,indent=2),encoding='utf-8')
