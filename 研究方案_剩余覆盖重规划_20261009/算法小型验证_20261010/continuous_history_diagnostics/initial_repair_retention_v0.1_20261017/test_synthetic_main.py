from pathlib import Path
import sys,json,time
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(D/'source_snapshot'))
import portable_frozen
import fixed_scope_original as old
import fixed_scope_candidate as fixed
import repair_retention as pool
import range_p2_engine_20261015 as engine
from model import Snapshot,DeadlineExceeded
from audit import audit
from road_range_candidate_20261015 import digest
LEDGER=D/'synthetic_calls.jsonl'
def call(name,fn):
 rows=LEDGER.read_text(encoding='utf-8').splitlines() if LEDGER.exists() else []
 assert len(rows)<60,'synthetic cap exhausted';idx=len(rows);start=time.perf_counter();row={'call_index':idx,'name':name,'status':'started'}
 try:
  x=fn();row.update(status='returned',seconds=time.perf_counter()-start,route_steps=len(x.get('route',()))-1,continuation_subcalls=x.get('continuation_subcalls',0),local_initial_fallback_subcalls=x.get('local_initial_fallback_subcalls',0))
  (D/f'synthetic_{idx:02d}.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');return x
 except BaseException as exc:row.update(status='exception',exception=repr(exc));raise
 finally:
  with LEDGER.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
def fallback_only(s,initial,scope,seed):
 original=engine.candidates
 def stop(*args):raise DeadlineExceeded()
 engine.candidates=stop
 try:return old.solve(s,initial,'LITERAL',2,seed,scope_name=scope)
 finally:engine.candidates=original

def main():
 shapes=[('rectangle',[(x,y) for x in range(3) for y in range(3)],[(0,0),(0,1),(1,1),(1,0),(2,0),(2,1),(2,0),(1,0),(0,0)]),('elbow',[(0,0),(1,0),(2,0),(3,0),(0,1),(0,2)],[(0,0),(1,0),(2,0),(3,0),(2,0),(1,0),(0,0)])]
 checks=[]
 for name,free,route in shapes:
  initial=set(route)-{(0,0)};s=Snapshot(name,frozenset(free),frozenset(set(free)-{(0,0)}),frozenset(),(0,0),(0,0),tuple(route),0,100)
  for seed in (0,1):
   refs={k:call(f'{name}_{seed}_old_{k}',lambda k=k:old.solve(s,initial,'LITERAL',2,seed,scope_name=k)) for k in ['R_SEED','R_PLUS1','R_ALL']}
   fixes={k:call(f'{name}_{seed}_fix_{k}',lambda k=k:fixed.solve(s,initial,'LITERAL',2,seed,scope_name=k)) for k in ['R_SEED','R_PLUS1','R_ALL']}
   for k in refs:
    assert refs[k]['route']==fixes[k]['route'] and refs[k]['core_route']==fixes[k]['core_route'] and refs[k]['source']==fixes[k]['source'],('FIX mismatch',name,seed,k)
   a=call(f'{name}_{seed}_POOL_INIT',lambda:pool.solve(s,initial,'POOL_INIT',2,seed));b=call(f'{name}_{seed}_POOL_PLUS1',lambda:pool.solve(s,initial,'POOL_PLUS1',2,seed))
   front=lambda x:[(e['source'],e['route_sha256'],e['valid']) for e in x['candidate_events'] if not e['source'].startswith('continue_')]
   assert front(a)==front(b)
   for x in (a,b):
    assert audit(s,tuple(map(tuple,x['route'])))['valid']
    assert all(e['accepted_public_elapsed']<=2 for e in x['candidate_events'] if e['accepted'])
    assert len(x['route'])-1==x['acceptances'][-1]['steps']
   for scope in ['R_PLUS1','R_SEED']:
    ref=call(f'{name}_{seed}_fallback_{scope}',lambda scope=scope:fallback_only(s,initial,scope,seed))
    candidates=[e for e in a['candidate_events'] if e['source_scope']==scope and e['valid'] and e['source'].startswith('construct_')]
    best=min(candidates,key=lambda e:len(e['route']))
    assert tuple(map(tuple,ref['core_route']))==tuple(map(tuple,best['route'])),('fallback extraction mismatch',name,seed,scope)
   checks.append({'shape':name,'seed':seed,'FIX_equivalent':True,'fallback_exact':True,'pool_front_equal':True})
 (D/'synthetic_main_results.json').write_text(json.dumps({'status':'PASS','top_level_calls':40,'checks':checks},indent=2),encoding='utf-8')
 print('PASS 40 bounded synthetic top-level calls')
if __name__=='__main__':main()
