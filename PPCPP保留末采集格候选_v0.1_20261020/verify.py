from common import *
from analyze import compute,summarize,timing
import csv,ast
audit_module=load('last_verify_policy_audit',H/'audit.py')
def main():
 protect();analysis=read(H/'analysis.json');rows,calls,refs=compute();assert analysis['states']==rows and analysis['calls']==calls
 assert refs==read(H/'reference_seal.json')['files']
 for p,h in refs.items():
  path=R/p;assert sha(path)==h
  folder=R/Path(p).parts[0];upstream=read(folder/'manifest.json');assert upstream[str(path.relative_to(folder))]==h
 gate=read(H/'gate_index.json');assert gate['passed'] and gate['calls']==218 and gate['development_calls']==180 and gate['fixture_calls']==27 and gate['deadline_calls']==9
 for item in gate['index']:
  g=read(H/item['path']);audit_module.check(g['input'],g['result'])
  if item['kind']=='deadline_injection':assert not g['result']['eligible'] and not g['result']['raw']['route'] and g['result']['raw']['status']=='deadline' and g['result']['raw']['branches']['P0']['status']=='core_complete'
  if item['kind']=='original_failure':assert 'P1' not in g['result']['raw']['branches'] and not g['result']['eligible']
 for bound in read(H/'gate_exact_bounds.json'):
  if bound['p1_status']=='core_complete':assert bound['result']['status']=='optimal'
 assert gate['exact_fixture_calls']==len(read(H/'gate_exact_bounds.json'))==8
 for batch,summary in analysis['batches'].items():assert summary==summarize([r for r in rows if r['batch']==batch])
 for batch,methods in analysis['timing'].items():
  for method,t in methods.items():assert t==timing([x['entry_seconds'] for x in calls if x['batch']==batch and x['method']==method])
 for batch,methods in analysis['metric_totals'].items():
  for method,total in methods.items():
   metrics=[r[method+'_metrics'] for r in rows if r['batch']==batch and method+'_metrics' in r];assert total['N']==len(metrics)
   for k,v in total.items():
    if k not in ('N','active_coverage','published_coverage','overlap'):assert v==sum(m[k] for m in metrics)
 report=(H/'保留末采集格候选开发结果.md').read_text(encoding='utf-8');n=0
 for batch in ('main36','supp24'):
  subset=[r for r in rows if r['batch']==batch]
  with (H/f'{batch}_状态表.csv').open(encoding='utf-8-sig',newline='') as f:tab=list(csv.reader(f))
  assert len(tab)==len(subset)+1
  for cells,r in zip(tab[1:],subset):
   expected=[r['name'],r['PPCPP_metrics']['length'],r.get('P1_metrics',{}).get('length','不适用'),r['selected'],r['LAST_metrics']['length'],r['reference']['Lstar'],r['saved'],r['final_gap'],r['e'],r.get('P1_minus_Lnear','无参考'),r['audit']['extra_work_connection_steps']]
   assert '|'+ '|'.join(map(str,expected))+'|' in report
   assert cells[:8]==[str(x) for x in expected[:8]];n+=1
 with (H/'全部调用时间与分段.csv').open(encoding='utf-8-sig',newline='') as f:timerows=list(csv.reader(f))
 assert len(timerows)==361
 for c,x in zip(timerows[1:],calls):assert c[0]==x['id'] and float(c[6])==x['entry_seconds']
 choices={'best_improvement':sorted([r for r in rows if r.get('saved',0)>0],key=lambda r:(-r['saved'],r['id'])),'unrecovered_space':sorted([r for r in rows if r['reference']['original_gap']>0 and r.get('final_gap',0)>0],key=lambda r:r['id']),'P1_longer':sorted([r for r in rows if 'P1_metrics' in r and r['P1_metrics']['length']>r['PPCPP_metrics']['length']],key=lambda r:r['id']),'reservation_infeasible':sorted([r for r in rows if r['P1_status']=='reservation_infeasible'],key=lambda r:r['id'])}
 assert analysis['selected']=={k:v[0]['id'] if v else None for k,v in choices.items()}
 for name in set(x for x in analysis['selected'].values() if x):assert (H/'figures'/f'{name}.png').exists() and (H/'figures'/f'{name}.svg').exists()
 # Production modules may not import offline or exact tools.
 for file in ('runtime.py','candidate.py','worker.py'):
  tree=ast.parse((H/file).read_text(encoding='utf-8'))
  for node in ast.walk(tree):
   if isinstance(node,ast.ImportFrom):assert node.module not in ('exact','independent','analyze','common')
   if isinstance(node,ast.Import):assert not any(n.name in ('exact','independent','analyze','common') for n in node.names)
 ledger=read(H/'formal_call_ledger.json');assert ledger['calls']==len(calls)==360 and ledger['eligible']==sum(x['eligible'] for x in calls)==360
 assert len(list((H/'execution').glob('*.json')))==len(list((H/'jobs').glob('*.json')))==360
 assert ledger['statuses']=={'core_complete':360}
 if (H/'manifest.json').exists():
  for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
 print(json.dumps(dict(verified=True,formal_calls=360,gate_calls=218,gate_exact_calls=8,source_sealed=True,manifest_sealed=(H/'manifest.json').exists(),P0_formal_pairs=180,stable_method_state_groups=120,report_rows=n,read_scope_verified=True,main36=analysis['batches']['main36'],supp24=analysis['batches']['supp24'],review_status='执行完成，待负责人审核'),ensure_ascii=False))
if __name__=='__main__':main()
