"""Export saved intervention results only; no new core/post/geometry/BFS."""
from common import *
from collections import Counter,defaultdict
from statistics import mean,median
from math import ceil
import sys,csv
sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
from center_bench_v01_20261022.exact import Expr,certificate,Uncertain
def stats(xs):
 xs=sorted(xs);return {'n':len(xs),'mean':mean(xs) if xs else None,'median':median(xs) if xs else None,'min':min(xs) if xs else None,'max':max(xs) if xs else None,'P95':xs[ceil(.95*len(xs))-1] if xs else None}
def ex(v):return Expr.load(v['metrics']['length_certificate']['exact'])
def ediff(a,b):
 z=a-b
 try:s=z.sign()
 except Uncertain:s='uncertain'
 lo,hi=z.interval();return {'sign':s,'certificate':certificate(z),'interval':[str(lo),str(hi)]}
def diff(a,b):return dict(ediff(ex(a),ex(b)),display=a['metrics']['length']-b['metrics']['length'])
def order(v):return [e['cell'] for e in v['events'] if e['new']]
def seq(a,b):
 n=min(len(a),len(b));p=0
 while p<n and a[p]==b[p]:p+=1
 s=0
 while s<n-p and a[-1-s]==b[-1-s]:s+=1
 same=a==b
 return {'equal':same,'OFF_count':len(a),'ON_count':len(b),'common_prefix':p,'common_suffix':s,'first_difference':None if same else {'index':p,'OFF':a[p] if p<len(a) else None,'ON':b[p] if p<len(b) else None},'OFF_changed_range':None if same else [p,len(a)-s-1],'ON_changed_range':None if same else [p,len(b)-s-1],'range_scope':'index alignment after equal prefix and before maximal disjoint equal suffix, not causal footprint'}
def display_cert(c):
 a,b=Expr.load(c['exact']).interval();return float((a+b)/2)
def csvwrite(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def native_partition(x,spec):
 path=x['views']['A']['path'];U=ps(x['input']['targets'])-ps(x['input']['covered']);pending=set(U);last=None;firsts=[]
 for i,p in enumerate(path):
  if tuple(p) in pending:pending.remove(tuple(p));last=i;firsts.append({'index':i,'cell':p})
 assert not pending and last is not None
 trig=x['native']['diagnostic']['trigger'];a=trig['route_index'];b=a+len(trig['actual_recovery_path'])-1
 assert path[a:b+1]==trig['actual_recovery_path'] and last>=b
 lengths={'common_prefix':a,'specified_recovery':b-a,'subsequent_coverage':last-b,'return_after_last_center_credit':len(path)-1-last}
 assert sum(lengths.values())==len(path)-1
 return {'unit_lengths':lengths,'trigger_route_start':a,'trigger_route_end':b,'last_new_center_index':last,'last_new_center':firsts[-1]['cell'],'new_tasks_during_recovery':[p for p in trig['actual_recovery_path'][1:] if tuple(p) in ps(trig['pending'])],'source':'native unit-grid pending at actual centers, exact trace boundaries; includes incidental collection during recovery','no_center_credit_feedback_to_solver':True}
def main():
 assert not (H/'summary.json').exists()
 plan=read(H/'plan.json');status=read(H/'status.json');selection=read(H/'selection.json');old=Path(selection['old_package']);outputs={};views=[];times=[];query={};ag=defaultdict(Counter)
 for ident in status['completed']:
  x=read(H/'outputs'/(ident+'.json'));j=x['job'];outputs[(j['case'],j['seed'],j['arm'])]=x
  d=x['native']['diagnostic'];times.append(dict(j,**x['timing'],diagnostic_hook_seconds=d['diagnostic_hook_seconds'],cold_import_seconds=x['cold_import_seconds'],independent_wall_seconds=x['independent_wall_seconds'],decision_audit_seconds=x['decision_audit']['seconds'],worker_wall_seconds=x['worker_wall_seconds'],runtime_reported_entry_seconds=x['native']['entry_seconds']))
  for a,v in x['views'].items():views.append(dict(j,alias=a,view='raw' if a=='A' else 'post',metrics=v['metrics'],counts=v['counts'],source_sha256=sha(H/'outputs'/(ident+'.json'))));ag['primary_virtual'].update(v['counts'])
  for key,value in [('post_engine',x['post_envelope']['counts']),('independent_geometry_credit',x['independent']['counts']),('independent_decision',x['decision_audit']['counts']),('diagnostic',d['counts'])]:ag[key].update(value)
  query[ident]={'core_detail_profile':None,'target_intervention_enabled':j['target_intervention_enabled'],'diagnostic_counts':d['counts'],'main_scope_alias':x['query_scope_schema'],'post':x['post_envelope']['counts'],'independent_credit':x['independent']['counts'],'independent_decision':x['decision_audit']['counts']}
 pairs=[];proof=[];refs=[];excluded=[]
 for c in selection['selected']:
  spec=read(H/c['spec'])
  for seed in plan['seeds']:
   if not all((c['id'],seed,arm) in outputs for arm in ('OFF','ON')):excluded.append({'case':c['id'],'seed':seed,'reason':'no full valid OFF/ON pair'});continue
   off,on=[outputs[(c['id'],seed,arm)] for arm in ('OFF','ON')];k=spec['trace_record'];ta,tb=[x['native']['raw']['trace'] for x in (off,on)];a,b=[x['native']['diagnostic']['trigger'] for x in (off,on)]
   assert off['off_equivalence']['passed'] and ta[:k]==tb[:k] and a['pending']==b['pending']==spec['pending']
   assert off['views']['A']['path'][:a['route_index']+1]==on['views']['A']['path'][:b['route_index']+1]==spec['original_route_prefix']
   ee=dict(tb[k],goal=ta[k]['goal']);assert ee==ta[k] and a['chosen_goal']==spec['default_goal'] and b['chosen_goal']==spec['alternative_goal']
   partitions={arm:native_partition(x,spec) for arm,x in [('OFF',off),('ON',on)]};stage_delta={key:partitions['ON']['unit_lengths'][key]-partitions['OFF']['unit_lengths'][key] for key in partitions['OFF']['unit_lengths']}
   row={'case':c['id'],'base_id':c['base_id'],'seed':seed,'initial_U':spec['initial_U'],'trigger_pending':len(spec['pending']),'raw_distance_delta':diff(on['views']['A'],off['views']['A']),'post_distance_delta':diff(on['views']['B'],off['views']['B']),'relative_post_delta':(on['views']['B']['metrics']['length']-off['views']['B']['metrics']['length'])/off['views']['B']['metrics']['length'],'raw_route':seq(off['views']['A']['path'],on['views']['A']['path']),'post_route':seq(off['views']['B']['path'],on['views']['B']['path']),'raw_decisions':seq(ta,tb),'nominal_anchor_order':seq([z['point'] for z in off['post']['locked_nominal_anchors']],[z['point'] for z in on['post']['locked_nominal_anchors']]),'raw_credit_order':seq(order(off['views']['A']),order(on['views']['A'])),'post_credit_order':seq(order(off['views']['B']),order(on['views']['B'])),'native_partition_delta':stage_delta,'time_delta':{key:on['timing'][key]-off['timing'][key] for key in ('native_entry_seconds','raw_common_end_to_end','post_increment','post_engine_seconds','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds','combined_end_to_end')},'hook_time_delta':on['native']['diagnostic']['diagnostic_hook_seconds']-off['native']['diagnostic']['diagnostic_hook_seconds'],'causal_pair_natural':all(x['timing']['termination']=='natural' and not any(x['timing'][key] for key in ('native_late','raw_stage_late','combined_late','post_late')) for x in (off,on))}
   for arm,x in [('OFF',off),('ON',on)]:
    row.update({arm+'_raw':x['views']['A']['metrics']['length'],arm+'_post':x['views']['B']['metrics']['length'],arm+'_raw_turns':x['views']['A']['metrics']['turns'],arm+'_post_turns':x['views']['B']['metrics']['turns'],arm+'_seconds':x['timing']['combined_end_to_end'],arm+'_last_credit':order(x['views']['B'])[-1:],arm+'_native_last':partitions[arm]['last_new_center'],arm+'_native_seconds':x['timing']['native_entry_seconds'],arm+'_hook_seconds':x['native']['diagnostic']['diagnostic_hook_seconds']})
   stages={v:{key:dict(ediff(Expr.load(on['views'][alias]['metrics']['stages'][key]['exact']),Expr.load(off['views'][alias]['metrics']['stages'][key]['exact'])),display=display_cert(on['views'][alias]['metrics']['stages'][key])-display_cert(off['views'][alias]['metrics']['stages'][key])) for key in ('to_first_witness','between_first_last_witness','after_last_witness_return')} for v,alias in [('raw','A'),('post','B')]}
   crosses={}
   for arm,x in [('OFF',off),('ON',on)]:
    t=x['native']['diagnostic']['trigger'];boundaries={'trigger_start':t['route_index'],'chosen_target_reached':t['route_index']+len(t['actual_recovery_path'])-1}
    crosses[arm]={name:[e for e in x['post']['edges'] if e['left']<i<e['right']] for name,i in boundaries.items()}
   proof.append({'case':c['id'],'seed':seed,'OFF_old_equivalence':off['off_equivalence'],'same_input_bytes':on['input']==off['input'],'pretrigger_raw_route_equal':True,'pretrigger_full_decisions_equal':True,'pretrigger_full_pending_equal':True,'only_trigger_event_goal_differs_at_that_record':True,'ON_authorized_exceptions':on['decision_audit']['authorized_exceptions'],'OFF_authorized_exceptions':off['decision_audit']['authorized_exceptions'],'triggers':{'OFF':a,'ON':b},'native_partitions':partitions,'native_partition_delta':stage_delta,'witness_stage_deltas':stages,'post_edges_crossing_original_boundaries':crosses,'post_decomposition_caution':'global post may cross native intervention/recovery boundaries; no strict native three-stage causal decomposition transferred to post. Witness-stage midpoint is not unique physical first-entry time.','all_later_decisions_checked_by_independent_auditor':True})
   oldrefs={}
   for lab,branch,env in [('old_B_N','B','N'),('old_R_E','R','E'),('old_C_N','C','N'),('old_C_E','C','E')]:
    f=old/'outputs'/f"formal__{c['id']}__{seed}__{branch}__{env}.json";x=read(f);v=x['views']['C' if branch=='C' else 'B'];oldrefs[lab]={'source':str(f),'sha256':sha(f),'post_distance':v['metrics']['length'],'raw_distance':x['views']['C0' if branch=='C' else 'A']['metrics']['length'],'historical_combined_seconds':x['timing']['combined_end_to_end'],'same_post_route_as_new_ON':v['path']==on['views']['B']['path'],'new_ON_minus_old_reference':diff(on['views']['B'],v),'not_new_same_batch_time_ranking':True}
   refs.append({'case':c['id'],'seed':seed,'references':oldrefs,'new_N_R_P2_calls':0})
   pairs.append(row)
 states=[]
 for c in selection['selected']:
  pp=[p for p in pairs if p['case']==c['id']]
  if not pp:continue
  states.append({'case':c['id'],'base_id':c['base_id'],'shape':'Z','seed_count':len(pp),'raw_delta':stats([p['raw_distance_delta']['display'] for p in pp]),'post_delta':stats([p['post_distance_delta']['display'] for p in pp]),'relative_post_delta':stats([p['relative_post_delta'] for p in pp]),'time_delta':stats([p['time_delta']['combined_end_to_end'] for p in pp]),'raw_equal_pairs':sum(p['raw_route']['equal'] for p in pp),'post_equal_pairs':sum(p['post_route']['equal'] for p in pp),'credit_equal_pairs':sum(p['post_credit_order']['equal'] for p in pp),'post_signs':dict(Counter(str(p['post_distance_delta']['sign']) for p in pp)),'native_partition_mean_delta':{key:mean(p['native_partition_delta'][key] for p in pp) for key in pp[0]['native_partition_delta']}})
 timingkeys=('native_entry_seconds','raw_common_end_to_end','post_engine_seconds','post_increment','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds','combined_end_to_end','diagnostic_hook_seconds','cold_import_seconds','independent_wall_seconds','decision_audit_seconds','worker_wall_seconds','artifact_flush_excluded_seconds')
 timingstats=[{'case':c['id'],'arm':arm,'statistics':{key:stats([t[key] for t in times if t['case']==c['id'] and t['arm']==arm]) for key in timingkeys}} for c in selection['selected'] for arm in ('OFF','ON')]
 summary={'completed':len(status['completed']),'views':len(views),'pairs':len(pairs),'state_count':len(states),'state_results':states,'state_equal_raw_delta':stats([s['raw_delta']['mean'] for s in states]),'state_equal_post_delta':stats([s['post_delta']['mean'] for s in states]),'two_first_OFF_gate_passed':status['two_OFF_gate_passed'],'all_OFF_old_equal':all(x['off_equivalence']['passed'] for x in outputs.values() if x['job']['arm']=='OFF'),'all_ON_unique_trigger_and_audit':all(x['native']['diagnostic']['counts']['matched']==x['native']['diagnostic']['counts']['applied']==x['decision_audit']['authorized_exceptions']==1 for x in outputs.values() if x['job']['arm']=='ON'),'all_natural_pairs':all(p['causal_pair_natural'] for p in pairs),'termination':dict(Counter(x['job']['arm']+'_'+x['timing']['termination'] for x in outputs.values())),'late_ids':{key:[t['id'] for t in times if t[key]] for key in ('native_late','raw_stage_late','combined_late','post_late')},'post_fallback':dict(Counter(str(x['post_envelope']['fallback']) for x in outputs.values())),'failure':status['failure'],'not_run':status['not_run'],'excluded':excluded,'worst_pair':max(pairs,key=lambda p:p['post_distance_delta']['display']) if pairs else None,'new_calls_in_export':0,'new_online_selector_or_innovation':False}
 for name,data in [('24视图完整指标.json',views),('12入口完整计时.json',times),('6对ON减OFF全指标.json',pairs),('逐决策干预证明.json',proof),('旧N_R_P2只读参考.json',refs),('两状态等权.json',states),('逐状态计时统计.json',timingstats),('summary.json',summary)]:dump(H/name,data)
 csvwrite('24视图完整指标.csv',[dict({k:v for k,v in r.items() if k not in ('metrics','counts')},**r['metrics']) for r in views]);csvwrite('12入口完整计时.csv',times);csvwrite('6对ON减OFF全指标.csv',pairs)
 events=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];started=[e for e in events if e['event']=='started'];pre=read(H/'prechecks.json');prevpre=read(H/'prechecks_preparation_v01_passed_count_incomplete.json')
 ledger={'core_attempted':len(started),'core_completed':len(status['completed']),'post_saved':sum((H/'outputs'/(j['id']+'_post_raw.json')).exists() for j in plan['jobs']),'views':len(views),'OFF':sum(j['arm']=='OFF' for j in started),'ON':sum(j['arm']=='ON' for j in started),'complete_pairs':len(pairs),'state_count':len(states),'warmup':0,'technical_core':0,'new_N_R_P2':0,'new_maps':0,'pure_fixed_identities':8,'pure_item_attempts':len(pre['cases'])+len(prevpre['cases']),'preparation_repairs':read(H/'preparation_repairs.json')['used'],'pure_choose_attempts_both_rounds':pre['pure_counts']['hook_attempts']+prevpre['pure_counts']['hook_attempts'],'pure_finish_attempts_both_rounds':2,'pure_audit_attempts_both_rounds':pre['pure_counts']['audit_attempts']+prevpre['pure_counts']['audit_attempts'],'formal_failure':status['failure'],'not_run':status['not_run'],'new_calls_after_formal':0,'no_holdout_new_selector_rollout_closedloop':True}
 dump(H/'ledger.json',ledger)
 dump(H/'调用与查询总账.json',{'formal_per_entry':query,'formal_observed_aggregates':{k:dict(v) for k,v in ag.items()},'pure_final_round':pre,'pure_round1_preserved':prevpre,'round1_missing_partial_queries':'not observed, not zero; finish attempt reconstructible from fixed single invocation (1)','native_detailed_profile_counts':None,'alias_rules':'post service_intersections and post_service_intersections are aliases; independent post prefix contains aliases; query_scope.total is a subtotal, not extra work. target_box_tests are cheap box tests; independent decision BFS separate from main. No scalar sum of heterogeneous counters.','timing_metadata_note':'saved timing.main_measured_includes is inherited accepted worker text mentioning original profile ON; actual job.config/profile and native_observation are OFF/null in both target arms; target ON is separate. Diagnostic hook seconds exclude some constructor/export/encoding cost; full entry/end-to-end contains them. Do not infer complete diagnostic overhead by subtracting old-batch clocks.'})
 dump(H/'失败不适用触顶与未知.json',{'formal_failure':status['failure'],'not_run':status['not_run'],'inapplicable':[],'late':summary['late_ids'],'fallback':summary['post_fallback'],'preparation':'round1 all eight assertions passed, query instrumentation incomplete; one accounting repair, old source/pass result retained; round2 eight passed','still_unknown':['R advantage in large is not explained by this fixed goal replacement','which other specific path/order choice would explain large R advantage','online conditions identifying a useful replacement','cross-shape/unseen generalization and innovation'],'new_core_after_batch':0})
 lines=['# 六个同E、同seed的ON−OFF配对','','负数表示本次固定目标替换省路。旧N/R/C不混入新同轮排名。三个seed不是三张几何。','','|状态|seed|OFF原生/直达米|ON原生/直达米|Δ原生|Δ直达|Δ直达比例|OFF/ON端到端秒|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for p in pairs:lines.append(f"|{p['case']}|{p['seed']}|{p['OFF_raw']:.6f}/{p['OFF_post']:.6f}|{p['ON_raw']:.6f}/{p['ON_post']:.6f}|{p['raw_distance_delta']['display']:.6f}|{p['post_distance_delta']['display']:.9f}|{p['relative_post_delta']:.6%}|{p['OFF_seconds']:.6f}/{p['ON_seconds']:.6f}|")
 lines+=['','|状态三seed等权|原生Δ均值|直达Δ均值/中位/[范围]米|时间Δ均值/中位/[范围]秒|','|---|---:|---|---|']
 for s in states:
  d,t=s['post_delta'],s['time_delta'];lines.append(f"|{s['case']}|{s['raw_delta']['mean']:.6f}|{d['mean']:.9f}/{d['median']:.9f}/[{d['min']:.9f},{d['max']:.9f}]|{t['mean']:.6f}/{t['median']:.6f}/[{t['min']:.6f},{t['max']:.6f}]|")
 lines+=['','逐视图分母、H/暂缓/覆盖/返航/资源、长度根式、转弯90/180/其他、末采和信用在24视图与outputs；逐决策pending、默认/实际目标和审核在逐决策干预证明及每入口decision_audit。计时统计含均值/中位/范围/P95/最坏，P95为ceil(.95n)序位，小样本不能宣称稳定加速。']
 (H/'03_六配对与全指标入口.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'ledger':ledger,'states':states,'all_OFF_equal':summary['all_OFF_old_equal'],'all_pairs_natural':summary['all_natural_pairs']},ensure_ascii=False))
if __name__=='__main__':main()
