"""Read-only hashes, provenance, windows/responsibility, dual metrics and totals."""
import csv
from support import *
from environment import verify as verify_environment
from analyze import compute,A
def strip_external(x):
 if isinstance(x,dict):return {k:strip_external(v) for k,v in x.items() if k not in ('external_audit_seconds','external_audit')}
 if isinstance(x,list):return [strip_external(v) for v in x]
 return x
def main():
 manifest=read(H/'manifest.json')
 for p,h in manifest.items():assert sha(H/p)==h,p
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts};assert actual==set(manifest)
 n=verify_environment();protocol=read(H/'protocol.json');assert len(protocol['inputs'])==36
 for p,h in protocol['sources'].items():assert sha(p)==h
 for item in protocol['inputs']:
  assert sha(item['input'])==item['input_sha256'] and sha(item['payload'])==item['sha256'];c=read(item['input']);env=read(item['payload']);assert env['state']==c and pts(env['marker'])==pts(item['marker'])
  original=read(item['source']);w=read(item['witness']);prep=read(item['history_source']);before=read(Path(item['history_source']).parent.parent/'inputs'/(item['base_id']+'.json'));prefix=prep['raw']['route'][:w['cut']+1]
  assert prefix==w['history'] and pts(prefix)&pts(before['targets'])==pts(c['covered']) and c['current']==prefix[-1] and c['previous']==prefix[-2] and c['old_route']==prep['raw']['route'][w['cut']:]
  assert pts(w['blocked'])==pts(before['free'])-pts(original['free'])==pts(item['marker'])
  for field in ('current','previous','base','predator','covered','old_route','initial_targets','distance_budget'):assert c[field]==original[field]
  if item['kind']=='event':assert sha(item['input'])==sha(item['source'])
  else:assert c['free']==before['free'] and c['targets']==before['targets'] and c['published_targets']==before['published_targets'] and pts(c['deferred_targets'])==pts(c['published_targets'])-pts(c['free'])-pts(c['covered'])
 gi=read(H/'gate_index.json');assert gi['passed'] and len(gi['records'])==24
 for p in gi['records']:
  x=read(H/p);assert A.check(x['input'],x['result'],x['method'])==x['audit']
 stub=read(H/'stub_gates.json');assert len(stub)==16
 for x in stub:
  if x['test'] in ('p0_before','p0_after','window_before','window_scan','local_before','local_offer','local_after','splice_check','final_check','encode_before','encode_after'):assert x['result']['raw']['status']=='deadline' and not x['result']['raw']['route']
  elif x['test']=='tie':assert x['result']['raw']['selected']=='P0'
  elif x['test']=='strict_shorter':assert x['result']['raw']['selected']=='LOCAL_P2'
  elif x['test'] in ('invalid','exception'):assert not x['result']['raw']['route']
 order=read(H/'formal_order.json');actual_order=[json.loads(s) for s in (H/'actual_order.jsonl').read_text(encoding='utf-8').splitlines()];assert len(actual_order)==len(order)==324
 for x,y in zip(order,actual_order):assert all(x[k]==y[k] for k in x)
 assert len(list((H/'execution').glob('*.json')))==len(list((H/'execution').glob('*.log')))==len(list((H/'jobs').glob('*.json')))==324
 print('ENVIRONMENT/36PROVENANCE/24GATES/16STUBS/324ORDER VERIFIED',n,flush=True)
 d=compute();saved=read(H/'analysis.json');assert strip_external(d)==strip_external(saved)
 ledger=read(H/'call_ledger.json');assert ledger['formal_entries']==324 and ledger['formal_native']==saved['internal_calls'] and ledger['formal_core_total']==426 and ledger['gate_native']=={'PPCPP':24,'local_P2':10,'global_P2':0} and ledger['stub_real_solver_calls']==0
 for ev in ledger['local_search_evidence']:
  c=next(c for c in saved['calls'] if c['sequence']==ev['sequence']);er=read(H/c['output'])['raw']['local'];assert er['status']=='finished' and er['core_finished'] and {'H_generate','V_generate','core_finished','deep_finished','shuffle_1_expand'}<={x['stage'] for x in er['events']}
 with (H/'324调用完整指标.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==324
 for x,y in zip(rows,saved['calls']):
  for k in ('status','valid','timely','late','source','entry_seconds','original_patch_steps','local_steps'):assert x[k]==('' if y[k] is None else str(y[k]))
  for k,v in (y['metrics'] or {}).items():assert x['metric_'+k]==('' if v is None else str(v))
 with (H/'36状态三种子与窗口.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==36
 for x,y in zip(rows,saved['states']):assert json.loads(x['methods'])==y['methods'] and json.loads(x['window'])==y['window']
 assert saved['P0_pairs']==108 and not saved['continue_signal']['passed']
 print(json.dumps(dict(verified=True,new_solver_calls=0,environment_files=n,formal_entries=324,formal_core_calls=ledger['formal_native'],gate_entries=24,gate_core_calls=ledger['gate_native'],stub_tests=16,P0_pairs=108,summary={kind:{key:val for key,val in s.items() if key=='counts'} for kind,s in saved['summary'].items()},continue_signal=saved['continue_signal'],status='已封存，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
