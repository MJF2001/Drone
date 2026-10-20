"""Read-only verification of the sealed P2_WARM_GLOBAL run outputs."""
from pathlib import Path
import sys,json,hashlib,argparse
ROOT=Path(__file__).resolve().parent;ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009'/'算法小型验证_20261010';RUN=ALGO/'continuous_history_diagnostics'/'old_plan_warm_global_v0.1_20261017';REC=RUN/'recovery2'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ALGO/'frozen_baselines'/'v2_20261012'/'source'))
from prepare_road_range_diagnostic_20261015 import snapshot
from verify_continuous_preparation_20261016 import read,route_check
from audit import audit
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=read(RUN/'protocol.json');jobs=p['jobs'];orig=[json.loads(x) for x in (RUN/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()];rec2=[json.loads(x) for x in (REC/'recovery_ledger.jsonl').read_text(encoding='utf-8').splitlines()];assert len(jobs)==120
 index={}
 for base in (RUN/'runs',REC/'runs'):
  for j in jobs:
   f=base/(j['run_id']+'.json')
   if f.exists():
    q=read(f)
    if q.get('worker_status')=='returned' and q.get('independent_route_check',{}).get('valid'):index.setdefault(j['run_id'],(j,q))
 assert len(index)==120,(len(index),'valid unique outputs')
 for rid,(j,q) in index.items():
  c=read(Path(j['case']));assert q['case_sha256']==sha(j['case']);assert q['method']==j['method'] and q['budget']==j['budget'] and q['seed']==j['seed']
  s=snapshot(c);raw=q['raw'];route=tuple(map(tuple,raw['route']));a=audit(s,route);assert a['valid'],(rid,a)
  assert route_check(c,route)['valid'],rid
  if j['method']=='P2_WARM_GLOBAL':
   ev=next(e for e in raw['events'] if e.get('stage')=='warm_sequence_audit');assert not ev['duplicate_count'] and not ev['missing_targets'] and not ev['extra_targets'];assert set(map(tuple,ev['sequence']))==set(map(tuple,ev['covered_targets']))
 # Preserve and count every attempted execution across initial and recovery ledgers.
 attempts={'initial':len(orig),'recovery1':sum(1 for _ in (RUN/'recovery'/'recovery_ledger.jsonl').open(encoding='utf-8')),'recovery2':len(rec2)}
 print(json.dumps({'status':'PASS','unique_calls':len(index),'independent_route_audits':len(index),'warm_sequence_audits':sum(j['method']=='P2_WARM_GLOBAL' for j,_ in index.values()),'attempts':attempts,'method':'read-only; no planner invoked; no files written'},ensure_ascii=True))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.parse_args();main()
