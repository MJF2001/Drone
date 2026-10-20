from pathlib import Path
import sys,json,hashlib
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';S=D/'source_snapshot'
sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(S))
import portable_frozen
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
from road_range_candidate_20261015 import digest
from audit_helpers import *
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_result(j,x,protected):
 assert x['job']==j and x['worker_status']=='returned';assert sha(j['case'])==j['case_sha256']
 c=read(j['case']);raw=x['raw'];route=raw['route'];assert not route or not route_errors(c,route)
 assert raw['budget']==j['budget'] and raw['seed']==j['seed']
 for e in x['loaded_modules'].values():
  assert e['path'] in protected and protected[e['path']]==e['sha256'] and sha(e['path'])==e['sha256'],('unknown module/hash',e)
 plan=independent_plan(c);pool=j['method'].startswith('POOL_');detail=raw if pool else raw['detail'];events=detail['candidate_events']
 if detail['range_plan'] is not None:assert detail['range_plan']==plan
 check_acceptances(events,j['budget'])
 for e in events:
  assert e['route_sha256']==digest(tuple(map(tuple,e['route']))) and e['steps']==len(e['route'])-1
  assert e['valid']==(not route_errors(c,e['route']))
  assert e['before_deadline']==(e['validation_complete_public_elapsed']<=j['budget'])
  if e.get('patch') is not None:
   cfg=plan['plans'][e['source_scope']];assert e['cfg']==cfg
   # Invalid old local segments are retained as evidence, never accepted.
   if e['valid']:
    comp=compatibility(c,e['route'],cfg);assert comp['valid'],comp
    assert list(map(tuple,e['patch']))==comp['patch']
 if pool:
  check_selected(raw,events);assert raw['absolute_deadline']==raw['public_t0']+j['budget']
  assert raw['continuation_subcalls']<=1
  for r in raw['initial_repairs']:
   cfg=plan['plans'][r['scope']];assert r['cfg']==cfg
   if 'responsibilities' in r:assert r['responsibilities']==assignment(c,cfg)
   if 'prefix' in r:assert r['prefix']==c['old_route'][:cfg['left']+1] and r['suffix']==c['old_route'][cfg['right']:]
  k=raw['construction_best_candidate_id']
  if k is not None:assert len(route)<=len(events[k]['route'])
  if raw['continuation']:
   d=raw['continuation']['detail'];assert d['public_t0']==raw['public_t0'] and d['absolute_deadline']<=raw['absolute_deadline']
   assert d['entry_public_elapsed']>=raw['continuation_entry_public_elapsed']
  if route:assert raw['acceptances'][-1]['route_sha256']==digest(tuple(map(tuple,route)))
 else:
  cfg=plan['plans'][j['method'].replace('FIX_','R_')]
  if detail['responsibilities'] is not None:assert detail['responsibilities']==assignment(c,cfg)
  if route:assert detail['acceptances'][-1]['route_sha256']==digest(tuple(map(tuple,route)))
  if raw['core_route']:assert compatibility(c,raw['core_route'],cfg)['valid']
 compat=[]
 if pool:
  for e in events:
   if e['source'].startswith('construct_R_SEED:'):
    compat.append(dict(candidate_id=e['candidate_id'],source=e['source'],route_sha256=e['route_sha256'],**compatibility(c,e['route'],plan['plans']['R_PLUS1'])))
 return dict(run_id=j['run_id'],valid=bool(route),candidate_count=len(events),compatibility=compat)
def main(mode):
 pr=read(D/('preflight_protocol.json' if mode=='preflight' else 'protocol.json'))
 for p,h in pr['protected_hashes'].items():assert sha(p)==h,('protected changed',p)
 folder=D/mode;rows=[json.loads(l) for l in (folder/'attempts.jsonl').read_text().splitlines()];check_unique(rows)
 assert [x['run_id'] for x in rows]==[j['run_id'] for j in pr['jobs']]
 checks=[]
 for j,row in zip(pr['jobs'],rows):
  assert row['job']==j and row['returncode']==0 and not row['watchdog'];checks.append(check_result(j,read(row['result_path']),pr['protected_hashes']))
 result=dict(status='PASS',mode=mode,tasks=len(rows),valid_routes=sum(x['valid'] for x in checks),all_candidate_count=sum(x['candidate_count'] for x in checks),solver_calls=0,checks=checks)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main(sys.argv[1])
