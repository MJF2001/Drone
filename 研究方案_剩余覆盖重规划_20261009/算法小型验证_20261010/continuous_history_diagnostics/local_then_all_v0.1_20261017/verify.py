from pathlib import Path
import sys,json,hashlib
from audit_helpers import route_errors,compatibility,check_unique,check_acceptances,check_selected
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';S=D/'source_snapshot'
sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(S));import portable_frozen
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
from road_range_candidate_20261015 import digest
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_raw(c,r,method,budget):
 assert not r['route'] or not route_errors(c,r['route'])
 combo=method=='LOCAL_THEN_ALL';events=r['candidate_events'] if combo else r['detail']['candidate_events'];check_acceptances(events,budget);plan=independent_plan(c)
 if combo:
  check_selected(r,events);assert abs(r['first_deadline_public_elapsed']-budget/2)<1e-8;assert r['absolute_deadline']==r['public_t0']+budget
  assert len(r['stages'])==2 and r['stages'][0]['scope']=='R_PLUS1' and r['stages'][1]['scope']=='R_ALL'
  assert r['switch_public_elapsed']>=r['stages'][0]['end_public_elapsed'];assert r['stages'][1]['entry_public_elapsed']>=r['switch_public_elapsed']
  assert abs(r['first_stage_overrun']-max(0,r['switch_public_elapsed']-budget/2))<1e-8
  for st in r['stages']:
   end=budget/2 if st['stage']=='local' else budget
   assert abs(st['available_seconds']-max(0,end-st['entry_public_elapsed']))<1e-8
   if st['status']=='skipped':assert st['entry_public_elapsed']>=end
   if st['raw']:
    d=st['raw']['detail'];assert d['public_t0']==r['public_t0'];assert d['absolute_deadline']<=r['public_t0']+end+1e-8
    if d['range_plan'] is not None:assert d['range_plan']==plan
 else:
  if r['detail']['range_plan'] is not None:assert r['detail']['range_plan']==plan
 for e in events:
  assert e['route_sha256']==digest(tuple(map(tuple,e['route']))) and e['steps']==len(e['route'])-1
  assert e['valid']==(not route_errors(c,e['route']))
  if combo:
   assert e['source']==e['stage']+':'+e['label']
   assert (e['stage'],e['stage_scope']) in [('local','R_PLUS1'),('all','R_ALL')]
   limit=budget/2 if e['stage']=='local' else budget
   if e['accepted']:assert e['accepted_public_elapsed']<=limit and e['accepted_public_elapsed']>=e['validation_complete_public_elapsed'] and e['accepted_public_elapsed']==e['decision_public_elapsed']
  if e.get('patch') is not None:
   scope=e['source_scope'];assert scope==(e['stage_scope'] if combo else method.replace('FIX_','R_'));cfg=plan['plans'][scope];assert e['cfg']==cfg
   assert e['route']==c['old_route'][:cfg['left']]+e['patch']+c['old_route'][cfg['right']+1:]
   if e['valid']:assert compatibility(c,e['route'],cfg)['valid']
 if r['route']:
  d=r if combo else r['detail'];assert d['acceptances'][-1]['route_sha256']==digest(tuple(map(tuple,r['route'])))
 return len(events)
def check_result(j,x,protected):
 assert j==x['job'] and x['worker_status']=='returned';assert sha(j['case'])==j['case_sha256'];assert x['raw']['budget']==j['budget'] and x['raw']['seed']==j['seed']
 for e in x['loaded_modules'].values():assert e['path'] in protected and e['sha256']==protected[e['path']]==sha(e['path'])
 return check_raw(read(j['case']),x['raw'],j['method'],j['budget'])
def main(mode):
 pr=read(D/('preflight_protocol.json' if mode=='preflight' else 'protocol.json'))
 for p,h in pr['protected_hashes'].items():assert sha(p)==h,('protected mismatch',p)
 folder=D/mode;ledger=[json.loads(l) for l in (folder/'attempts.jsonl').read_text().splitlines()];check_unique(ledger);assert [r['run_id'] for r in ledger]==[j['run_id'] for j in pr['jobs']];n=valid=0
 for j,l in zip(pr['jobs'],ledger):
  assert l['returncode']==0 and not l['watchdog'];x=read(l['result_path']);n+=check_result(j,x,pr['protected_hashes']);valid+=bool(x['raw']['route'])
 print(json.dumps(dict(status='PASS',mode=mode,tasks=len(ledger),valid_routes=valid,candidate_events=n,solver_calls=0,read_only=True)))
if __name__=='__main__':main(sys.argv[1])
