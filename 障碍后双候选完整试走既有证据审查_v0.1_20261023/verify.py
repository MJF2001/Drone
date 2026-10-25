"""Independent saved evidence audit: stdlib only, no path/geometry searches.
Physical lengths: integer square-factor enumeration, Fraction radical sums;
turns: integer direction products; timing: original JSON and Decimal arithmetic.
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
from decimal import Decimal
from math import isqrt,atan2,ceil
import json,hashlib,time
H=Path(__file__).resolve().parent;ROOT=H.parent;BASE=ROOT/'障碍后接续假设有限扩样_v0.1_20261023';C=Counter()
def read(p):
 b=Path(p).read_bytes();C['json_reads']+=1;C['json_bytes']+=len(b);return json.loads(b.decode('utf-8-sig'))
def sha(p):
 b=Path(p).read_bytes();C['hash_reads']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def pset(x):return set(tuple(v) for v in x)
def coefficients(c):
 out=Counter()
 for t in c['exact']['terms']:out[t['r']]+=Q(t['c']['n'],t['c']['d']);C['certificate_terms']+=1
 return {r:q for r,q in out.items() if q}
def add(*signed):
 out=Counter()
 for s,e in signed:
  for r,q in e.items():out[r]+=s*q;C['independent_additions']+=1
 return {r:q for r,q in out.items() if q}
def physical_length(path):
 out=Counter()
 for a,b in zip(path,path[1:]):
  n=(b[0]-a[0])**2+(b[1]-a[1])**2;C['length_edges']+=1
  if not n:continue
  factor=1
  for k in range(1,isqrt(n)+1):
   C['square_factor_trials']+=1
   if n%(k*k)==0:factor=k
  out[n//(factor*factor)]+=Q(factor)
 return dict(out)
def interval(e):
 S=1<<192;lo=hi=Q(0)
 for r,q in e.items():
  k=isqrt(r*S*S);a=Q(k,S);b=a if k*k==r*S*S else Q(k+1,S);lo+=q*(a if q>=0 else b);hi+=q*(b if q>=0 else a);C['integer_root_bounds']+=1
 return lo,hi
def sign(e):
 if not e:return 0
 lo,hi=interval(e);assert lo>0 or hi<0;return 1 if lo>0 else -1
def value(e):return float(sum(interval(e))/2)
def close(a,b,tol=1e-9):assert abs(a-b)<tol,(a,b)
def turns(path):
 directions=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:]) if a!=b];counts=dict(total=0,**{'90':0,'180':0,'other':0});angle=0.
 for (x,y),(a,b) in zip(directions,directions[1:]):
  cross=x*b-y*a;dot=x*a+y*b;C['turn_direction_pairs']+=1
  if cross or dot<0:
   counts['total']+=1;counts['90' if not dot else '180' if not cross and dot<0 else 'other']+=1;angle+=atan2(abs(cross),dot)
 return counts,angle
def independently_timed(o):
 t=o['timing'];r=o['native']['raw'];x=dict(solver_seconds=r['seconds'],solver_accepted_seconds=r['accepted_seconds'],solver_budget_seconds=r['budget'],native_entry_seconds=o['native_entry_seconds'],raw_common_end_to_end=t['raw_common_end_to_end'],post_increment=t['post_increment'],post_engine_seconds=o['post_envelope']['entry_seconds'],combined_main_seconds=t['combined_end_to_end'],hook_seconds=o['diagnostic']['diagnostic_hook_seconds'] if o['diagnostic'] else None,independent_total_seconds=o['independent_seconds'],independent_full_views_post_seconds=o['independent']['seconds'],independent_decisions_seconds=o['decision_audit']['seconds'],worker_wall_seconds=o['worker_wall_seconds'],parent_wall_seconds=o['parent_wall_seconds'])
 for name,a,b in [('raw_credit_metrics_mixed_seconds','raw_common_end_to_end','native_entry_seconds'),('entry_outside_solver_mixed_seconds','native_entry_seconds','solver_seconds'),('post_wrapper_outside_engine_mixed_seconds','post_increment','post_engine_seconds'),('parent_outside_worker_mixed_seconds','parent_wall_seconds','worker_wall_seconds')]:x[name]=float(Decimal(str(x[a]))-Decimal(str(x[b])));C['timer_subtractions']+=1
 x['worker_outside_main_and_independent_mixed_seconds']=float(Decimal(str(x['worker_wall_seconds']))-Decimal(str(x['combined_main_seconds']))-Decimal(str(x['independent_total_seconds'])));C['timer_subtractions']+=2
 close(x['raw_common_end_to_end']+x['post_increment'],x['combined_main_seconds'],1e-12);close(t['post_engine_seconds'],x['post_engine_seconds'],1e-12);assert x['solver_accepted_seconds']<=x['solver_seconds'] and x['independent_full_views_post_seconds']+x['independent_decisions_seconds']<=x['independent_total_seconds']+1e-9
 return x
def check_stats(actual,values):
 values=sorted(values);n=len(values);assert actual['n']==n
 if not n:return
 total=float(sum((Decimal(str(v)) for v in values),Decimal(0)));median=values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2
 for name,v in [('sum',total),('mean',total/n),('median',median),('min',values[0]),('max',values[-1]),('P95_nearest_rank',values[ceil(.95*n)-1])]:close(actual[name],v,1e-10);C['statistic_values']+=1
def verify():
 begin=time.perf_counter();checks=Counter()
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,p
 manifest=read(H/'manifest.json');registry=read(BASE/'state_registry.json');assert manifest['states']==[r['id'] for r in registry] and len(registry)==12
 outputs={r['id']:r for r in read(H/'twelve_candidate_reference.json')};timerows={(r['id'],r['arm']):r for r in read(H/'response_timing_observations.json')};sumrows={r['id']:r for r in read(H/'two_independent_call_cost_sums.json')};export={r['id']:r for r in read(BASE/'42处理完整计时.json')};assert len(export)==42 and len(outputs)==12 and len(timerows)==36
 totals={};oldsum={};selturns={v:Counter() for v in ('A','B')};angular={v:0. for v in ('A','B')};default_raw=selected_raw=0;raw_pi_half_delta=0;selected_sum={};classification=Counter();geos={};allcost=[];byarm={a:[] for a in ('REF','OFF','ALT1')};source_views={};sources={}
 for reg in registry:
  ident=reg['id'];row=outputs[ident];oo={a:read(BASE/'outputs'/(ident+'__'+a+'.json')) for a in ('REF','OFF','ALT1')};sources[ident]=oo;assert all(o['passed'] and o['eligible'] and o['independent']['passed'] and o['decision_audit']['passed'] for o in oo.values());assert all(oo['OFF']['off_equivalence'].values());assert oo['OFF']['post']['vertices']==oo['REF']['post']['vertices']
  c=oo['OFF']['input'];assert all(o['input']==c for o in oo.values());trigger=oo['OFF']['diagnostic']['trigger'];idx=trigger['route_index'];cur=oo['OFF']['native']['raw']['route'];pending=pset(c['targets'])-pset(c['covered'])-pset(cur[:idx+1]);assert pending==pset(row['trigger']['pending'])==pset(trigger['pending']);assert row['trigger']['common_prefix']==cur[:idx+1] and row['trigger']['current']==cur[idx] and row['trigger']['previous']==cur[idx-1] if idx else row['trigger']['previous']==c['previous']
  q0=tuple(trigger['default_goal']);q1=next(tuple(p) for p in reg['old_order'] if tuple(p) in pending and tuple(p)!=q0);assert row['default']==list(q0) and row['alternative']==list(q1);first=next(i for i,t in enumerate(oo['OFF']['native']['raw']['trace']) if t['kind']=='recovery');assert row['trigger']['first_native_recovery_record']==first and row['trigger']['equals_first_recovery']==(first==trigger['trace_record']);checks['trigger_and_candidate_from_saved_prefix']+=1
  d={};armtimes={};turns_by={};angles_by={}
  for arm,o in oo.items():
   ar=row['arms'][arm];assert ar['source_sha256']==sha(ar['source']);raw=o['native']['raw']['route'];F=pset(c['free']);U=pset(c['targets'])-pset(c['covered']);assert raw[0]==c['current'] and raw[-1]==c['base'] and pset(raw)<=F and U<=pset(raw);assert len(raw)-1<=c['distance_budget'];assert all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(raw,raw[1:]));assert len(raw)-1==ar['raw_length'];turns_by[arm]={};angles_by[arm]={}
   for view,path in [('A',raw),('B',o['post']['vertices'])]:
    length=physical_length(path);metric=o['views'][view]['metrics'];assert length==coefficients(metric['length_certificate']);close(value(length),metric['length']);tc,angle=turns(path);assert tc==ar['turns'][view]['counts']=={k:metric['turns'].get(k,0) for k in ('total','90','180','other')};close(angle,ar['turns'][view]['total_turn_radians']);coverage=ar['coverage'][view]
    for k,v in coverage.items():assert v==metric[k]
    assert coverage['missing']==0 and coverage['return_success'] and coverage['deferred']==0 and coverage['active_coverage']==coverage['published_coverage']==1;assert coverage['remaining_before']==len(U) and coverage['new_credit']==len(U);turns_by[arm][view]=tc;angles_by[arm][view]=angle;checks['physical_length_turns_saved_coverage']+=1
    source_views[ident,arm,view]=metric
   assert ar['engine_turns']==dict(original=o['post']['turns_original'],shortcut=o['post']['turns_new'])
   for name,view in [('original','A'),('shortcut','B')]:
    assert ar['engine_turns'][name]['nonzero_direction_changes']==turns_by[arm][view]['total'];close(ar['engine_turns'][name]['total_turn_radians'],angles_by[arm][view])
   d[arm]=physical_length(o['post']['vertices']);assert d[arm]==coefficients(ar['post_certificate']);close(ar['post_length'],value(d[arm]));tt=independently_timed(o);recorded=timerows[ident,arm]['timing']
   for k,v in tt.items():
    if v is None:assert recorded[k] is None
    else:close(recorded[k],v,1e-12)
   assert recorded['post_partial_timings']==o['post']['timing'] and 'encoding' not in o['post']['timing'];assert recorded['native_detail_profile'] is None
   ex=export[ident+'__'+arm]
   for k in ('native_entry_seconds','combined_main_seconds','independent_seconds','worker_wall_seconds','parent_wall_seconds'):
    source_value=o['independent_seconds'] if k=='independent_seconds' else tt[k];close(ex[k],source_value,1e-12)
   armtimes[arm]=tt;byarm[arm].append(recorded);checks['original_timer_identity_and_export']+=1
  delta=add((1,d['ALT1']),(-1,d['OFF']));sg=sign(delta);winner='ALT1' if sg<0 else 'OFF';assert row['choice']==winner and row['delta_post_sign']==sg and coefficients(row['delta_post_certificate'])==delta;selected_delta=delta if winner=='ALT1' else {};assert coefficients(row['selected_change_post_certificate'])==selected_delta;close(row['selected_change_post'],value(selected_delta));default_raw+=row['arms']['OFF']['raw_length'];selected_raw+=row['arms'][winner]['raw_length'];assert row['selected_change_raw']==row['arms'][winner]['raw_length']-row['arms']['OFF']['raw_length'];assert row['raw_same']==(oo['OFF']['native']['raw']['route']==oo['ALT1']['native']['raw']['route']) and row['post_same']==(oo['OFF']['post']['vertices']==oo['ALT1']['post']['vertices']);selected_sum=add((1,selected_sum),(1,selected_delta));oldsum=add((1,oldsum),(1,d['OFF']));totals=add((1,totals),(1,d[winner]));geos.setdefault(reg['base_geometry'],[]).append((selected_delta,d['OFF'],row['classification']));classification[row['classification']]+=1
  for view in ('A','B'):
   for k in ('total','90','180','other'):
    dd=turns_by[winner][view][k]-turns_by['OFF'][view][k];assert row['selected_turn_delta'][view]['counts'][k]==dd;selturns[view][k]+=dd;assert row['ALT_turn_delta'][view]['counts'][k]==turns_by['ALT1'][view][k]-turns_by['OFF'][view][k]
   angle=angles_by[winner][view]-angles_by['OFF'][view];close(row['selected_turn_delta'][view]['total_turn_radians'],angle);angular[view]+=angle
  raw_pi_half_delta+=row['selected_turn_delta']['A']['counts']['90']+2*row['selected_turn_delta']['A']['counts']['180']
  sr=sumrows[ident];pair={k:float(Decimal(str(armtimes['OFF'][k]))+Decimal(str(armtimes['ALT1'][k]))) for k in sr['sum']}
  for k,v in pair.items():close(sr['sum'][k],v,1e-12)
  allcost.append(pair);checks['two_saved_candidate_choice_turn_cost_sum']+=1
 summary=read(H/'reference_summary.json');assert summary['counts']==dict(classification);assert coefficients(summary['post_selected_change_certificate'])==selected_sum;close(summary['post_default_sum'],value(oldsum));close(summary['post_selected_sum'],value(totals));close(summary['post_selected_change'],value(selected_sum));assert summary['raw_default_sum']==default_raw and summary['raw_selected_sum']==selected_raw and summary['raw_selected_change']==selected_raw-default_raw
 for view in selturns:assert summary['selected_turn_deltas'][view]['counts']==dict(selturns[view]);close(summary['selected_turn_deltas'][view]['total_turn_radians'],angular[view])
 permean=[];perpercent=[]
 for geo,items in geos.items():
  z={}
  for change,default,cl in items:z=add((1,z),(1,change))
  ss=summary['by_base'][geo];assert coefficients(ss['selected_change_certificate'])==z and ss['states']==2;close(ss['state_mean_change'],value(z)/2);percent=sum(100*value(change)/value(default) for change,default,cl in items)/2;close(ss['mean_state_percent'],percent);permean.append(value(z)/2);perpercent.append(percent)
 close(summary['geometry_equal_weight_mean_distance_change'],sum(permean)/6);close(summary['geometry_equal_weight_mean_state_percent'],sum(perpercent)/6);close(summary['total_length_percent'],100*value(selected_sum)/value(oldsum))
 ts=read(H/'timing_summary.json')
 for arm,stats in ts['arm_statistics'].items():
  for k,s in stats.items():
   values=[x[k] for x in byarm[arm] if x[k] is not None]
   if not values:assert s is None
   else:check_stats(s,values)
 for k,s in ts['two_independent_call_sum_statistics'].items():check_stats(s,[x[k] for x in allcost])
 assert ts['clean_online_entry_seconds'] is None and ts['shared_prefix_online_seconds'] is None and ts['pure_core_without_diagnostic'] is None
 complete=read(H/'72保存响应视图完整指标.json');assert len(complete)==72
 for r in complete:assert r['metrics']==source_views[r['id'],r['arm'],r['view']]
 hist=read(H/'history_costs_excluded.json')['rows'];assert len(hist)==6 and all(x['arm']=='history' for x in hist)
 for snippet in read(H/'static_source_evidence.json'):
  assert sha(snippet['file'])==snippet['sha256'];lines=Path(snippet['file']).read_text(encoding='utf-8-sig').splitlines();assert snippet['lines']==[dict(line=i,text=lines[i-1]) for i in range(snippet['start'],snippet['end']+1)];checks['static_snippet_line_and_hash']+=1
 assert all(x['classification'] in ('代码已有能力','当前模型已验证能力','仍需适配') for x in read(H/'FIRST_capability_matrix.json'))
 before=(H/'root_before.md').read_bytes();shadow=ROOT/'障碍后接续估计器影子诊断_v0.1_20261023';assert read(shadow/'final_receipt.json')['root_sha256']==sha(H/'root_before.md');assert before==(shadow/'root_after.md').read_bytes();current=(ROOT/'当前进度与下一步.md').read_bytes();assert current.endswith(before)
 if (H/'root_after.md').exists():assert current==(H/'root_after.md').read_bytes()
 else:assert current==before
 sealed=0
 if (H/'final_receipt.json').exists():
  final=read(H/'final_receipt.json')
  for p,v in final['files'].items():assert sha(H/p)==v,p;sealed+=1
  assert sha(ROOT/'当前进度与下一步.md')==final['root_sha256']
 r=dict(passed=True,states=12,saved_response_observations=36,saved_response_views=72,checks=dict(checks),counts=dict(C),raw_selected_angle_delta_exact_pi_over_2_units=raw_pi_half_delta,raw_selected_angle_is_exactly_zero=raw_pi_half_delta==0,post_selected_angle_difference_radians=angular['B'],root_chain=True,sealed_files_checked=sealed,new_core=0,new_history=0,new_post=0,new_path_distance_search=0,new_geometry_visibility=0,new_candidate_route=0,new_counterfactual=0,new_training=0,FIRST_imported=False,seconds=time.perf_counter()-begin)
 print(json.dumps(r,ensure_ascii=False,indent=2));return r
if __name__=='__main__':verify()
