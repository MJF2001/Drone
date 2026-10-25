"""Read-only, no solver calls and no exact-search rerun."""
from diag_common import *
from prepare import audit_all
def main():
 manifest=read(D/'manifest.json')
 for p,h in manifest.items():assert sha(D/p)==h,p
 files={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts};assert files==set(manifest)
 for p,h in read(D/'environment_seal.json')['files'].items():assert sha(p)==h,p
 a,rows,selection=audit_all();assert norm(a)==read(D/'source_audit.json');assert norm(rows)==read(D/'selection.json')['candidates'] and norm(selection)==read(D/'selection.json')['selected'];assert len(a)==102
 positive=list((D/'positive').glob('*.json'));assert len(positive)==4
 for path in positive:
  x=read(path);r=x['result'];er=r['raw'] if x['mode'].startswith('direct') else r['raw']['local'];assert len(er['route'])-1==4 and er['route']==[[i,0] for i in range(5)] and r['entry_seconds']<20
  assert x['true_PPCPP_calls']==0 and x['true_local_engine_calls']==1
  if x['fixture']=='redundant':assert er['source']!='old_suffix'
  else:assert er['source']=='old_suffix'
 count=0
 for c in read(D/'exact_index.json')['records']:
  p=read(D/'exact_inputs'/(c['family']+'.json'));F=pts(p['free']);req=pts(p['required'])-pts(p['local_H']);lb=abs(p['entry'][0]-p['exit'][0])+abs(p['entry'][1]-p['exit'][1]);assert len(req)<=12 and len(F)*(2**len(req))<=2000000
  for method,r in c['results'].items():
   assert r['status']=='optimal' and r['seconds']<60;path=r['route'];assert path[0]==p['entry'] and path[-1]==p['exit'] and pts(path)<=F and req<=pts(path)
   assert all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(path,path[1:]));assert len(path)-1==r['length']==len(p['old_patch'])-1==lb;count+=1
  assert c['results']['exact_bfs']['length']==c['results']['exact_dijkstra']['length']
 assert count==6
 accepted=read(D/'exact_acceptance.json');assert accepted['engine_replays']==0 and accepted['real_solver_calls']==0 and len(accepted['probes'])==6
 checker=load('lastcheck_readonly_audit',S/'audit.py')
 for probe in accepted['probes']:
  p=read(D/'exact_inputs'/(probe['family']+'.json'));old=read(p['original_output']);env=read(old['job']['input']);assert checker.check(env,probe['result'],'LOCAL_P2')==probe['audit'] and probe['production_accepted']
 ledger=read(D/'call_ledger.json');assert ledger['positive_entries']==4 and ledger['positive_real_local_engine_calls']==4 and ledger['bfs_calls']==ledger['dijkstra_calls']==3 and ledger['replay_calls']==ledger['original324_reruns']==0
 assert read(D/'acceptance_probe_failure.json')['real_solver_calls']==0
 print(json.dumps(dict(verified=True,new_solver_calls=0,original_local_outputs_checked=102,positive_entries_previously_executed=4,exact_solves_previously_executed=6,engine_replays=0,original324_reruns=0,exact_search_rerun_by_verifier=False,selected_optimal_lengths={c['family']:c['results']['exact_bfs']['length'] for c in read(D/'exact_index.json')['records']},status='已封存，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
