"""Outcome release ONLY after immutable prediction seal."""
from common import *
from collections import Counter
from fractions import Fraction
from frozen_shadow_center_20261023.exact import Expr,certificate
import math
def display(e):return float(sum(e.interval())/2)
def num(n):return Expr.number(n)
def stats(v):
 v=sorted(v);n=len(v)
 return dict(n=n,sum=sum(v),mean=sum(v)/n if n else None,median=(v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2) if n else None,min=v[0] if n else None,max=v[-1] if n else None,P95_nearest_rank=v[math.ceil(.95*n)-1] if n else None)
def main():
 start=time.perf_counter();guard();seal=read(H/'predictions_seal.json');assert seal['predictions_sha256']==sha(H/'predictions.json');assert seal['controller_sha256']==read(H/'controller_registration.json')['source_sha256']
 for p,v in seal['files'].items():assert sha(H/p)==v
 assert time.time()>=seal['sealed_utc'];release=time.time();rows=[];ixs={x['key']:x for x in read(STRUCT/'pair_index.json')};outcomes=[]
 for pred in read(H/'predictions.json'):
  ix=ixs[pred['key']];record=read(STRUCT/ix['file']);old={a:read(record['source'][a]) for a in ('OFF','ALT1')};est={a:read(H/'outputs'/(pred['key']+'__'+a+'.json')) for a in ('OFF','ALT1')};true={a:Expr.load(o['views']['B']['metrics']['length_certificate']['exact']) for a,o in old.items()};dt=true['ALT1']-true['OFF'];sg=dt.sign();chosen=pred['prediction']['choice'];selected=dt if chosen=='ALT1' else num(0);regret=selected-(dt if sg<0 else num(0));row=dict(key=pred['key'],dataset=ix['dataset'],base_geometry=ix['base_geometry'],origin=ix['origin'],identity=record['identity'],true_sign=sg,truth_class='improvement' if sg<0 else 'deterioration' if sg>0 else 'equal',prediction=pred['prediction'],available=pred['available'],actual_selected_delta=display(selected),actual_selected_certificate=certificate(selected),two_candidate_regret=display(regret),regret_certificate=certificate(regret),delta_true=display(dt),delta_true_certificate=certificate(dt),arms={})
  if not pred['available']:label='unavailable'
  elif sg<0:label='caught_improvement' if chosen=='ALT1' else 'missed_improvement'
  elif sg>0:label='wrongly_accepted_deterioration' if chosen=='ALT1' else 'correctly_rejected_deterioration'
  else:label='equal_true_biased_q1' if chosen=='ALT1' else 'equal_true_retained_q0'
  row['classification']=label
  for a,o in est.items():
   t=true[a];ee=Expr.load(o['Jhat_certificate']['exact'])-t if o.get('Jhat_certificate') else None;p=read(H/'crops'/(pred['key']+'__'+a+'.json'));psu=o.get('prefix_summary');row['arms'][a]=dict(J_true=display(t),J_true_certificate=certificate(t),Jhat_raw=o.get('Jhat_raw'),Jhat_post=o.get('Jhat_post'),Jhat_certificate=o.get('Jhat_certificate'),error=display(ee) if ee is not None else None,error_certificate=certificate(ee) if ee is not None else None,prefix_summary=psu,tail_new_edges=o.get('counts',{}).get('tail_new_edges'),tail_task_queries=o.get('counts',{}).get('task_path_queries'),tail_incidental=o.get('counts',{}).get('incidental_tasks'),tail_start_pending=p['stop_state']['pending'],tail_end=next((v['goal'] for v in reversed(o.get('tail',{}).get('visits',[])) if v['kind']=='task'),None),source=str(record['source'][a]),source_sha256=record['source'][a+'_sha256'])
  if pred['available']:
   dh=Expr.load(pred['delta_hat_certificate']['exact']);e0=Expr.load(row['arms']['OFF']['error_certificate']['exact']);e1=Expr.load(row['arms']['ALT1']['error_certificate']['exact']);de=dh-dt;assert not (de-(e1-e0)).terms;row.update(delta_hat=display(dh),delta_hat_certificate=certificate(dh),error_difference=display(de),error_difference_certificate=certificate(de),error_difference_identity_exact=True)
  rows.append(row)
 dump(H/'joined_results.json',rows)
 summaries={}
 for dataset in ('base','variants'):
  rr=[r for r in rows if r['dataset']==dataset];counts=Counter(r['classification'] for r in rr);selected=sum((Expr.load(r['actual_selected_certificate']['exact']) for r in rr),num(0));regret=sum((Expr.load(r['regret_certificate']['exact']) for r in rr),num(0));bybase={}
  for geo in sorted({r['base_geometry'] for r in rr}):
   vv=[r for r in rr if r['base_geometry']==geo];s=sum((Expr.load(r['actual_selected_certificate']['exact']) for r in vv),num(0));bybase[geo]=dict(pairs=len(vv),selected_sum=display(s),selected_mean=display(s)/len(vv),selected_sum_certificate=certificate(s))
  summaries[dataset]=dict(pairs=len(rr),classification=dict(counts),available=sum(r['available'] for r in rr),suggest_ALT1=sum(r['prediction']['choice']=='ALT1' for r in rr),selected_delta_sum=display(selected),selected_delta_sum_certificate=certificate(selected),selected_sum_sign=selected.sign(),two_candidate_regret_sum=display(regret),regret_sum_certificate=certificate(regret),worst_actual_selected=max(r['actual_selected_delta'] for r in rr),worst_two_candidate_regret=max(r['two_candidate_regret'] for r in rr),by_base=bybase,base_equal_weight_selected_mean=sum(x['selected_mean'] for x in bybase.values())/len(bybase))
 lookup={r['key']:r for r in rows};i=lookup['base__I_gap_B__p60'];tkeys=['base__T_gap_B__p25','variants__T_gap_B__p25__A1','variants__T_gap_B__p25__A2'];gate=dict(original_I_suggest_q1=i['prediction']['choice']=='ALT1',original_T_and_two_A_avoid_q1=all(lookup[k]['prediction']['choice']=='OFF' for k in tkeys),base_selected_sum_strictly_negative=summaries['base']['selected_sum_sign']<0);gate['passed']=all(gate.values());gate['decision']='close fixed configuration continuation signal; no parameter repair or real finite-rollout timing authorized'
 dump(H/'summary.json',dict(datasets=summaries,gate=gate,truth_released_utc=release,prediction_seal_utc=seal['sealed_utc'],prediction_seal_sha256=sha(H/'predictions_seal.json'),stopped=True))
 maincounts=Counter();auditcounts=Counter();timing={};work=[]
 for slot in read(H/'manifest.json')['slots']:
  o=read(H/'outputs'/(slot['id']+'.json'));a=read(H/'audits'/(slot['id']+'.json'));w=dict(id=slot['id'],dataset=slot['dataset'],prefix=o.get('prefix_summary'),tail_counts=o['counts'],timing=o['timing'],worker_wall_seconds=o['wall_seconds'],independent_seconds=a.get('seconds'),independent_counts=a.get('counts'),raw_total=o.get('Jhat_raw'),post_total=o.get('Jhat_post'));work.append(w)
  for k,v in o['counts'].items():
   if type(v) is int:maincounts[k]+=v
   elif isinstance(v,dict):maincounts.update({k+'.'+z:n for z,n in v.items() if type(n) is int})
  auditcounts.update(a.get('counts',{}))
  for k,v in o['timing'].items():timing.setdefault(k,[]).append(v)
  timing.setdefault('worker_wall_seconds',[]).append(o['wall_seconds']);timing.setdefault('independent_seconds',[]).append(a.get('seconds',0))
 timing={k:stats(v) for k,v in timing.items()};dump(H/'workload.json',dict(arms=work,main_counts=dict(maincounts),independent_counts=dict(auditcounts),timing_statistics=timing,profile=False,unobserved=['Astar node pops/expansion','production context BFS dequeue/neighbor counters','process memory/online interrupt cost','true finite rollout cost','winner actual resume/recompute cost'],zero_core=True,calls=dict(fixed_prefix_extractions=38,new_tails=38,new_public_post=38,new_views=76,new_complete_core=0,new_true_finite_core=0,new_history_core=0),source_processing='old complete candidates38 reused only after prediction seal; source verification is read-only',overall_main_work='each arm reconstructs the full native substitute and runs whole-route post and two credit views; saved-prefix cost is not online finite-rollout cost'))
 dump(H/'comparison_receipt.json',dict(passed=True,pairs=len(rows),seconds=time.perf_counter()-start,gate=gate,source_truth_only_after_prediction_seal=True,new_core=0,new_post=0,new_geometry=0))
 print(json.dumps(dict(gate=gate,datasets=summaries,main_counts=dict(maincounts),timing=timing),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
