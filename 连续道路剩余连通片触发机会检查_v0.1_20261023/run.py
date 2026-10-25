from pathlib import Path
from collections import Counter
import json,hashlib,time,ast,traceback
import primary as P,independent as I
H=Path(__file__).resolve().parent;R=H.parent;S=R/'中心区OFF全量质量时间开发比较_v0.1_20261022';OLD=R/'连续道路与剩余任务地图语义盘点_v0.1_20261023'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def norm(x):return json.loads(json.dumps(x))
def write(n,x):
 p=H/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def register():
 assert not (H/'plan.json').exists();meta=read(OLD/'inventory.json');jobs=[j for j in read(S/'plan.json')['formal'] if j['rep']==0 and j['seed']==20261020 and j['method']=='PPCPP' and j['case'] in {r['id'] for r in meta if r['event']=='obstacle'}];assert len(jobs)==18
 guards={};of=read(OLD/'final_receipt.json')
 for n,v in of['files'].items():assert sha(OLD/n)==v;guards[str(OLD/n)]=v
 guards[str(OLD/'final_receipt.json')]=sha(OLD/'final_receipt.json');guards[str(OLD/'verify_receipt.json')]=sha(OLD/'verify_receipt.json')
 index=[];manifest=read(S/'manifest.json')['files']
 for j in jobs:
  ident=j['case'];m=next(r for r in meta if r['id']==ident)
  paths=[S/j['input'],S/'outputs'/(j['id']+'.json'),Path(m['source_witness']),Path(m['source_preparation']),Path(m['source_initial'])]
  for p in paths:guards[str(p.resolve())]=sha(p)
  for p in paths[:2]:assert sha(p)==manifest[str(p.relative_to(S)).replace('/','\\')]
  index.append(dict(job=j,meta=m,paths=[str(p.resolve()) for p in paths]))
 for n in ('plan.json','manifest.json','history_evidence.json'):guards[str(S/n)]=sha(S/n)
 for pkg in ('障碍后片区次序与收尾规则设计_v0.1_20261023','障碍后片区两阶段规则有限验证_v0.1_20261023','障碍后片区两阶段规则有限验证_v0.2_20261023'):
  for name in ('final_receipt.json','region_rule.py','region_audit.py'):
   if (R/pkg/name).exists():guards[str(R/pkg/name)]=sha(R/pkg/name)
 write('source_hashes.json',guards)
 selected=[min(j['case'] for j in jobs if next(m for m in meta if m['id']==j['case'])['family']==f) for f in ('I','L','Z')]+['small_I_obstacle_p30']
 write('plan.json',dict(policy='RESIDUAL_CC_TRIGGER_V1',index=index,budget=dict(event_components=18,decision_components=18,primary_distance_rows=54,independent_distance_rows=54,pure_cases=6,core=0,post=0,new_history=0,new_paths=0,visibility=0),definition='first original recovery Q four-neighbor components, IDs lex-min; unique minimum, q0 in S, fixed original exact representative conditions for every other component',figures=selected,figure_selection='lex-min obstacle ID for each family I/L/Z plus fixed small_I_obstacle_p30; before trigger computation',first_rejection_nulls=True,code_hashes={p.name:sha(p) for p in H.glob('*.py')}))
 write('registration_receipt.json',dict(passed=True,states=18,new_decision_computations=0,component_computations=0,distance_rows=0,utc=time.time()))
def execute():
 plan=read(H/'plan.json')
 for p,v in read(H/'source_hashes.json').items():assert sha(p)==v,p
 for p,v in plan['code_hashes'].items():assert sha(H/p)==v,p
 from tests import run
 write('pure_receipt.json',run());layers=read(OLD/'layers_and_components.json');M=Counter();A=Counter();results=[];beg=time.perf_counter()
 try:
  for entry in plan['index']:
   j=entry['job'];sid=j['case'];meta=entry['meta'];c=read(entry['paths'][0]);saved=read(entry['paths'][1]);raw=saved['native']['raw'];initial=saved['initial_collect_here'];w=read(entry['paths'][2]);prep=read(entry['paths'][3]);before=read(entry['paths'][4]);pack=layers[sid]
   assert saved['passed'] and saved['main_passed'] and saved['input']==c and saved['job']['seed']==20261020
   assert raw['mode']=='PPCPP' and raw['selected']=='P0' and raw['status']=='core_complete' and set(raw['branches'])=={'P0'}
   assert w['history']==prep['raw']['route'][:w['cut']+1] and c['old_route']==prep['raw']['route'][w['cut']:]
   assert P.points(c['covered'])==P.points(w['history'])&P.points(before['targets']);assert w['history'][-1]==c['current'] and w['history'][-2]==c['previous']
   e=P.extract(c,raw,initial);ie=I.extract(c,raw,initial);assert norm(e)==norm(ie),'independent prefix mismatch'
   U=P.points(e['U']);uc=P.components(U,M);iuc=I.components(U,A);assert uc==iuc
   F=P.points(c['free']);blocked=P.points(before['free'])-F;assert blocked==P.points(w['blocked'])
   r=dict(id=sid,base_id=meta['base_id'],family=meta['family'],size=meta['size'],progress=meta['progress'],event='obstacle',U_components=uc,U_sizes=[len(p) for p in uc],extraction=e,Q_components=None,decision=None,blockage=dict(new_cells=sorted(blocked),old_native_suffix_hits=sorted(P.points(c['old_route'])&blocked),old_native_suffix_blocked=bool(P.points(c['old_route'])&blocked),old_actual_post_blocked=None,old_post_evidence='pre-event preparation contains native raw only; no saved actual post/blockage certificate identified in bound provenance; unknown',event_post_not_used=True),input=c,actual_pre_event_history=w['history'],initial_collect_here=initial)
   rows={};auditrows={}
   if e['has_recovery']:
    k=e['raw_index'];assert norm(raw['route'][:k+1])==norm(raw['branches']['P0']['route'][:k+1]) and norm(e['trace_prefix'])==norm(raw['branches']['P0']['trace'][:e['trace_index']+1])
    Q=P.points(e['Q']);qc=P.components(Q,M);iqc=I.components(P.points(ie['Q']),A);assert qc==iqc
    def get(p):
     if p not in rows:assert len(rows)<3;rows[p]=P.row(F,p,M)
     return rows[p]
    def iget(p):
     if p not in auditrows:assert len(auditrows)<3;auditrows[p]=I.row(F,p,A)
     return auditrows[p]
    decision=P.judge(Q,F,tuple(c['base']),tuple(e['X']),tuple(e['q0']),qc,get);other=I.judge(P.points(ie['Q']),F,tuple(c['base']),tuple(ie['X']),tuple(ie['q0']),iqc,iget)
    assert norm(decision)==norm(other) and rows==auditrows,'independent trigger/distance mismatch';r.update(Q_components=qc,decision=decision)
   else:r['decision']=dict(trigger=False,reason='no_recovery',S=None,representatives=None,conditions=None,q0_verified=None)
   serialize=lambda ds:[dict(source=p,distances=[dict(cell=q,distance=d[q]) for q in sorted(d)]) for p,d in ds.items()]
   write('distance_rows/'+sid+'.json',dict(primary=serialize(rows),independent=serialize(auditrows),contains_parents=False,contains_paths=False))
   r['audit']=dict(passed=True,prefix=True,U_components=True,Q_components=True if e['has_recovery'] else None,distance_rows=len(rows),independent_distance_rows=len(auditrows));write('states/'+sid+'.json',r);results.append(r)
   print(sid,r['U_sizes'],[len(p) for p in r['Q_components']] if r['Q_components'] is not None else None,r['decision']['reason'],flush=True)
  assert len(results)==18 and M['component_calls']<=36 and A['component_calls']<=36 and M['distance_rows']<=54 and A['distance_rows']<=54
  write('results.json',results);write('workload.json',dict(primary=dict(M),independent=dict(A),seconds=time.perf_counter()-beg,actual_core=0,actual_post=0,new_history=0,candidate_routes=0,coverage_searches=0,visibility_queries=0,geometry_post_queries=0,description='component traversals and single-source distance rows are NEW graph computation; old preparation route read only for actual-history provenance and old-native-blockage facts'))
  write('run_status.json',dict(passed=True,status='fixed_18_complete_stopped'))
 except BaseException as ex:
  write('failure.json',dict(error=repr(ex),traceback=traceback.format_exc(),completed=len(results)));raise
if __name__=='__main__':
 if __import__('sys').argv[-1]=='register':register()
 else:execute()
