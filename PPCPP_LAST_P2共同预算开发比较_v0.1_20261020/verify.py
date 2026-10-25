"""Read-only: hashes, native outputs, full independent audits, dual views."""
import csv
from support import *
from environment import verify as verify_environment
from analyze import compute
def strip_external_timing(x):
 if isinstance(x,dict):return {k:strip_external_timing(v) for k,v in x.items() if k not in ('external_audit_seconds','external_audit')}
 if isinstance(x,list):return [strip_external_timing(v) for v in x]
 return x
def main():
 manifest=read(H/'manifest.json')
 for p,h in manifest.items():assert sha(H/p)==h,p
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts};assert actual==set(manifest)
 n=verify_environment();print('ENVIRONMENT/HASH verified',n,flush=True)
 old=R/'PPCPP_LAST距离查询等价提速_v0.2_20261020';oldseal=read(old/'source_seal.json')['files']
 for new,prior in [('candidate.py','candidate_v2.py'),('runtime.py','runtime.py'),('audit.py','audit.py'),('audit_adapter.py','audit_adapter.py')]:assert sha(H/new)==oldseal[prior]
 gi=read(H/'gate_index.json');assert gi['passed'] and gi['calls']==49
 # Original and thin adapter non-time comparison; no new solver calls.
 from gates import clean
 by={}
 for info in gi['records']:
  x=read(H/info['path']);assert x['kind']==info['kind'];by[info['kind'],info['name'],info['method']]=x['result']
 for c in read(H/'fixtures.json'):
  a=by['p2_equivalence',c['name'],'original'];b=by['p2_equivalence',c['name'],'adapter'];assert clean(a)==clean(b)
 for when in ('before_accept','after_accept'):
  for m in ('original','adapter'):
   x=by['p2_cutoff',when,m];assert x['status']=='deadline' and bool(x['route'])==(when=='after_accept')
 for info in gi['records']:
  if info['kind']=='last_deadline':
   x=read(H/info['path'])['result'];assert not x['raw']['route'] and not x['eligible'] and x['raw']['branches']['P0']['status']=='core_complete'
 order=read(H/'formal_order.json');actual=[json.loads(s) for s in (H/'actual_order.jsonl').read_text(encoding='utf-8').splitlines()];assert len(order)==len(actual)==972
 for a,b in zip(order,actual):assert all(a[k]==b[k] for k in a)
 for folder in ('jobs','execution'):assert len(list((H/folder).glob('*.json')))==972
 assert len(list((H/'execution').glob('*.log')))==972
 d=compute();saved=read(H/'analysis.json');assert strip_external_timing(d)==strip_external_timing(saved)
 with (H/'972调用与完整指标.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==972
 for a,b in zip(rows,saved['calls']):
  for k in ('native_status','has_returned_route','route_valid','timely_valid','late_valid','entry_seconds','route_source','overrun_seconds'):
   assert a[k]==('' if b[k] is None else str(b[k])),(k,a[k],b[k])
  for k,v in (b['metrics'] or {}).items():assert a['metric_'+k]==('' if v is None else str(v))
 with (H/'双视图配对.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==12
 for row in rows:
  x=next(x for x in saved['summary'][row['budget']]['comparisons'] if x['a']==row['a'] and x['b']==row['b'] and x['view']==row['view'])
  for k in ('N','short','equal','long','a_total','b_total','delta'):assert int(row[k])==x[k]
 assert saved['P0_pairs']==324
 assert all(x['stable_route'] and x['stable_trace'] for x in saved['states'] if x['method']!='P2_MULTI')
 print(json.dumps(dict(verified=True,planner_calls=0,environment_files=n,manifest_files=len(manifest),gates=49,formal=972,P0_pairs=saved['P0_pairs'],budgets={b:dict(counts=s['counts'],comparisons=[{k:v for k,v in c.items() if k!='pairs'} for c in s['comparisons']]) for b,s in saved['summary'].items()},status='执行完成，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
