"""Pure saved-route algebra. No planner imports, route generation, or optimization."""
from pathlib import Path
import json,hashlib,sys,csv,collections,subprocess
D=Path(__file__).resolve().parent;BASE=D.parent;ROOT=D.parents[3];OLD=BASE/'fixed_scope_true_history_v0.1_20261017';NEW=BASE/'initial_repair_retention_v0.1_20261017'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def bound(old,cfg):
 l,r=cfg['left'],cfg['right'];s,t=old[l],old[r];o=l+len(old)-1-r
 return o+max([distance(s,t)]+[distance(s,q)+distance(q,t) for q in cfg['required']])
def legal(c,r):
 errors=[];route=list(map(tuple,r));free=set(map(tuple,c['free']));pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))
 if not route:return ['empty']
 if route[0]!=tuple(c['current']) or route[-1]!=tuple(c['base']):errors.append('endpoints')
 if not set(route)<=free:errors.append('collision')
 if any(distance(a,b)!=1 for a,b in zip(route,route[1:])):errors.append('movement')
 if not pending<=set(route):errors.append('coverage')
 if len(route)-1>c['distance_budget']:errors.append('resource')
 return errors

def compatible(c,r,cfg):
 e=legal(c,r);l,h=cfg['left'],cfg['right'];old=c['old_route'];prefix=old[:l+1];suffix=old[h:];patch=r[l:len(r)-(len(old)-1-h)]
 if r[:len(prefix)]!=prefix:e.append('prefix')
 if r[-len(suffix):]!=suffix:e.append('suffix')
 if not patch or patch[0]!=old[l] or patch[-1]!=old[h]:e.append('ports')
 if not set(map(tuple,cfg['required']))<=set(map(tuple,patch)):e.append('responsibility')
 return dict(compatible=not e,errors=e,core_steps=len(patch)-1)
def compute():
 jobs=[j for j in read(OLD/'protocol.json')['jobs'] if j['method']!='P2_MULTI'];assert len(jobs)==160
 structures={};runs=[];hashes={};cases={};plans={}
 for j in jobs:
  p=OLD/'formal'/(j['run_id']+'.json');x=read(p);c=read(j['case']);assert sha(j['case'])==j['case_sha256'];hashes[str(p)]=sha(p);hashes[j['case']]=sha(j['case']);cases[j['map_id']]=c
  plan=x['raw']['detail']['range_plan'];assert plan
  if j['map_id'] in plans:assert plans[j['map_id']]==plan
  plans[j['map_id']]=plan;r=x['raw']['route'];assert not legal(c,r)
  runs.append(dict(run_id=j['run_id'],map_id=j['map_id'],method=j['method'],budget=j['budget'],repeat=j['repeat'],seed=j['seed'],steps=len(r)-1,route=r,path=str(p),sha256=sha(p)))
 for m,c in sorted(cases.items()):
  plan=plans[m];initial=set(map(tuple,c['metadata']['initial_targets']));pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))
  for scope,cfg in plan['plans'].items():
   if scope not in ('R_SEED','R_PLUS1','R_PLUS2','R_ALL'):continue
   l,r=cfg['left'],cfg['right'];structures[m,scope]=dict(map_id=m,scope=scope,event=c['metadata']['event'],left=l,right=r,start=c['old_route'][l],join=c['old_route'][r],prefix_steps=l,suffix_steps=len(c['old_route'])-1-r,outside_steps=l+len(c['old_route'])-1-r,required=cfg['required'],required_count=len(cfg['required']),free=c['free'],distance_budget=c['distance_budget'],core_resource=c['distance_budget']-(l+len(c['old_route'])-1-r),old_collision_indices=plan['old_collision_indices'],new_target_count=len(pending-initial),deferred_count=len(c['metadata']['deferred_targets']),lower_bound=bound(c['old_route'],cfg))
 comps=[]
 for run in runs:
  for scope in ('R_SEED','R_PLUS1','R_PLUS2','R_ALL'):
   cfg=plans[run['map_id']]['plans'][scope];comps.append(dict(map_id=run['map_id'],run_id=run['run_id'],origin_method=run['method'],budget=run['budget'],repeat=run['repeat'],target_scope=scope,steps=run['steps'],**compatible(cases[run['map_id']],run['route'],cfg)))
 assert len(structures)==40 and len(comps)==640
 certificates=[];paired=[]
 for (m,scope),st in structures.items():
  pool=[r for r in runs if r['map_id']==m];best=min(pool,key=lambda r:r['steps']);ok={v['run_id'] for v in comps if v['map_id']==m and v['target_scope']==scope and v['compatible']};compatible_runs=[r for r in pool if r['run_id'] in ok];cb=min(compatible_runs,key=lambda r:r['steps']) if compatible_runs else None
  certificates.append(dict(map_id=m,scope=scope,lower_bound=st['lower_bound'],best_witness_steps=best['steps'],best_witness_run_id=best['run_id'],constraint_cost_certificate=best['steps']<st['lower_bound'],guaranteed_gap=max(0,st['lower_bound']-best['steps']),shortest_compatible_steps=cb['steps'] if cb else None,shortest_compatible_run_id=cb['run_id'] if cb else None))
  for run in pool:
   if run['method']!=scope.replace('R_','RANGE_'):continue
   omissions=[r for r in compatible_runs if r['steps']<run['steps']];matched=[r for r in omissions if r['budget']==run['budget'] and r['repeat']==run['repeat']]
   paired.append(dict(map_id=m,scope=scope,run_id=run['run_id'],budget=run['budget'],repeat=run['repeat'],steps=run['steps'],search_omission_certificate=bool(omissions),shortest_compatible_run_id=cb['run_id'] if cb else None,shortest_compatible_steps=cb['steps'] if cb else None,same_budget_repeat_shorter_witnesses=[r['run_id'] for r in matched],unidentified=not omissions and not best['steps']<st['lower_bound']))
 return dict(structures=list(structures.values()),compatibility=comps,certificates=certificates,run_certificates=paired,runs=runs,source_hashes=hashes,planner_calls=0,performance_experiments=0,holdout_used=False)
def fixtures():
 c=dict(free=[[0,0],[1,0],[2,0],[1,1],[2,1],[0,1]],targets=[[1,0]],covered=[],current=[0,0],base=[0,0],distance_budget=30,old_route=[[0,0],[1,0],[2,0],[1,0],[0,0]])
 cfg=dict(left=1,right=3,required=[[1,0]]);assert compatible(c,c['old_route'],cfg)['compatible'];assert bound(c['old_route'],dict(left=0,right=4,required=[]))==0
 assert compatible(c,[[0,0],[1,0],[0,0]],cfg)['compatible']; assert compatible(c,c['old_route'],cfg)['core_steps']==2 # repeated join, fixed length splitting
 bad=dict(c);bad['targets']=[[2,1]];assert not compatible(bad,c['old_route'],dict(left=1,right=3,required=[[2,1]]))['compatible']
 assert not compatible(c,[[0,0],[1,0],[2,0],[2,1],[1,1],[0,1],[0,0]],cfg)['compatible']
 assert distance([0,0],[2,0])==2 and len([[0,0],[0,1],[1,1],[2,1],[2,0]])-1==4 # obstacle detour hand route, no search
 detour=[[0,0],[0,1],[1,1],[2,1],[2,0]];obstacle=dict(free=detour,targets=[[2,0]],covered=[],current=[0,0],base=[2,0],distance_budget=10,old_route=detour);assert not legal(obstacle,detour);assert bound(detour,dict(left=0,right=4,required=[[2,0]]))==2 < len(detour)-1
 return dict(status='PASS',checks=['empty_Q','endpoint_in_Q','repeated_join_exact_split','suffix_mismatch','missing_responsibility','compatible_positive_negative','Manhattan_relaxed_by_obstacle'],planner_calls=0)
def csvwrite(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows])
def main():
 result=compute();fixtures()
 if len(sys.argv)>1 and sys.argv[1]=='verify':
  assert result==read(D/'evidence.json');assert fixtures()==read(D/'synthetic_checks.json')
  for name in ('fixed_scope_true_history_v0.1_20261017','initial_repair_retention_v0.1_20261017'):
   manifest=read(BASE/name/'delivery_sha256.json')
   for e in manifest['files']:assert sha(e['absolute_path'])==e['sha256']
  for e in read(D/'delivery_sha256.json')['files']:assert sha(e['path'])==e['sha256']
  print(json.dumps(dict(status='PASS',structures=40,compatibility_comparisons=640,saved_routes=160,planner_calls=0,performance_experiments=0,holdout_used=False)))
 else:
  (D/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');(D/'synthetic_checks.json').write_text(json.dumps(fixtures(),indent=2),encoding='utf-8')
  for key in ('structures','compatibility','certificates','run_certificates'):csvwrite(D/(key+'.csv'),result[key])
  (D/'provenance.json').write_text(json.dumps(dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),worktree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),source_hashes={str(p):sha(p) for folder in (OLD,NEW) for p in list((folder/'source_snapshot').rglob('*.py'))+[folder/'protocol.json',folder/'verify_delivery.py']},input_hashes=result['source_hashes']),ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps(dict(constraint=[r for r in result['certificates'] if r['constraint_cost_certificate']],omission_runs=sum(r['search_omission_certificate'] for r in result['run_certificates']),unidentified_runs=sum(r['unidentified'] for r in result['run_certificates'])),ensure_ascii=False))
if __name__=='__main__':main()

