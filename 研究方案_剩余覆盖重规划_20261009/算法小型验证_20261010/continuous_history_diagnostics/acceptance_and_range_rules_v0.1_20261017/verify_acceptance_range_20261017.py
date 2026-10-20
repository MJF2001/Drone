"""Read-only independent audit of hot-start acceptance and range details."""
from pathlib import Path
import sys,json,hashlib,collections,argparse
ROOT=Path(__file__).resolve().parents[4] # repository root from diagnostics/<dir>
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009'/'算法小型验证_20261010';SUP=ALGO/'continuous_history_diagnostics'/'acceptance_and_range_rules_v0.1_20261017';RUN=ALGO/'continuous_history_diagnostics'/'old_plan_warm_global_v0.1_20261017';PREP=ALGO/'continuous_history_diagnostics'/'preparation_verification_v0.1_20261016'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ALGO/'frozen_baselines'/'v2_20261012'/'source'))
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
from prepare_road_range_diagnostic_20261015 import snapshot
from audit import audit
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def warm_sequence(old,targets,covered,current):
 pending=set(map(tuple,targets))-set(map(tuple,covered))-{tuple(current)};seq=[]
 for p in map(tuple,old):
  if p in pending:seq.append(p);pending.remove(p)
 seq.extend(sorted(pending,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
 return seq
def check_core(old,l,r,required,core,patch):
 if core is None or patch is None:return False
 old=list(map(tuple,old));core=list(map(tuple,core));patch=list(map(tuple,patch))
 return bool(patch and patch[0]==old[l] and patch[-1]==old[r] and set(map(tuple,required))<=set(patch) and core==old[:l]+patch+old[r+1:])
def check_unique_success(ids):return len(ids)==len(set(ids))
def check_hash(path,expected):return Path(path).is_file() and sha(path)==expected
def valid_warm_sequence(actual,expected,targets):return list(map(tuple,actual))==list(map(tuple,expected)) and len(actual)==len(set(map(tuple,actual))) and set(map(tuple,actual))==set(map(tuple,targets))
def main():
 protocol=read(RUN/'protocol.json');jobs=protocol['jobs'];assert len(jobs)==120 and len({j['run_id'] for j in jobs})==120
 expected={(m,b,r,rep) for m in {j['map_id'] for j in jobs} for b in (1,20) for r in ('P2_MULTI','LITERAL','P2_WARM_GLOBAL') for rep in (0,1)}
 actual={(j['map_id'],j['budget'],j['method'],j['repeat']) for j in jobs};assert actual==expected and len(actual)==120
 evidence=read(RUN/'completion_final.json');assert evidence['valid_unique_calls']==120
 successes=[];warm_n=core_n=0;state=[];pair_details=[]
 for ln in (RUN/'final_120.jsonl').read_text(encoding='utf-8').splitlines():
  x=json.loads(ln);j=x['job'];q=x['result'];rid=j['run_id'];assert q['worker_status']=='returned' and q['method']==j['method'] and q['budget']==j['budget'] and q['seed']==j['seed'];assert q['case_sha256']==sha(j['case']);successes.append(rid)
  c=read(Path(j['case']));s=snapshot(c);raw=q['raw'];route=tuple(map(tuple,raw['route']));assert audit(s,route)['valid'] and raw['independent_audit']['valid']
  if j['method']=='P2_WARM_GLOBAL':
   seq=warm_sequence(c['old_route'],c['targets'],c['covered'],c['current']);ev=next(e for e in raw['events'] if e.get('stage')=='warm_sequence_audit');assert valid_warm_sequence(ev['sequence'],seq,ev['covered_targets']);warm_n+=1
  if j['method']=='LITERAL':
   plan=independent_plan(c);cfg=plan['plans']['R_PLUS1'];d=raw['detail'];assert d['range_plan']==plan;ass=assignment(c,cfg);assert json.loads(json.dumps(d['responsibilities']))==json.loads(json.dumps(ass));l,r=cfg['left'],cfg['right'];assert d['outside']['prefix']==c['old_route'][:l+1] and d['outside']['suffix']==c['old_route'][r:];assert check_core(c['old_route'],l,r,cfg['required'],raw.get('core_route'),raw.get('core_patch'));assert audit(s,tuple(map(tuple,raw['core_route'])))['valid'];core_n+=1
 assert check_unique_success(successes) and len(successes)==120 and warm_n==40 and core_n==40
 # Check every protected item except the single already disclosed first-runner hash exception.
 mism=[]
 for p,h in protocol['protected_hashes'].items():
  if not check_hash(p,h):mism.append(p)
 runner=str(ROOT/'run_p2_warm_global_20261017.py');assert mism==[runner],mism
 # All saved manifest deliverables still match.
 dm=read(RUN/'deliverables_sha256.json');assert all(check_hash(ROOT/k,v) for k,v in dm.items())
 trials={'initial':38,'initial_valid':25,'initial_exceptions':13,'recovery1':64,'recovery1_valid':0,'recovery2':95,'recovery2_valid':95}
 actual_attempts={'initial':sum(1 for _ in (RUN/'execution_ledger.jsonl').open(encoding='utf-8')),'recovery1':sum(1 for _ in (RUN/'recovery'/'recovery_ledger.jsonl').open(encoding='utf-8')),'recovery2':sum(1 for _ in (RUN/'recovery2'/'recovery_ledger.jsonl').open(encoding='utf-8'))};assert actual_attempts=={'initial':38,'recovery1':64,'recovery2':95}
 print(json.dumps({'status':'PASS','matrix':120,'route_audits':120,'independent_warm_sequences':warm_n,'literal_core_audits':core_n,'unique_successes':len(successes),'protected_hash_exceptions':mism,'attempts':actual_attempts,'read_only':True},ensure_ascii=True))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.parse_args();main()

