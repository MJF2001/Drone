"""Saved-result export only; no coverage solver, repair, post or geometry calls."""
from common import *
from collections import Counter,defaultdict
from statistics import mean,median
from math import ceil
import sys,csv
sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
from center_bench_v01_20261022.exact import Expr,Uncertain,certificate
def stats(xs):
 xs=sorted(xs);return {'n':len(xs),'mean':mean(xs) if xs else None,'median':median(xs) if xs else None,'min':min(xs) if xs else None,'max':max(xs) if xs else None,'P95':xs[ceil(.95*len(xs))-1] if xs else None}
def ex(v):return Expr.load(v['metrics']['length_certificate']['exact'])
def ediff(a,b):
 z=a-b
 try:s=z.sign()
 except Uncertain:s='uncertain'
 lo,hi=z.interval();return {'sign':s,'certificate':certificate(z),'interval':[str(lo),str(hi)]}
def diff(a,b):return dict(ediff(ex(a),ex(b)),display=a['metrics']['length']-b['metrics']['length'])
def raw(x):return x['views']['C0' if x['job']['branch']=='C' else 'A']
def post(x):return x['views']['C' if x['job']['branch']=='C' else 'B']
def order(v):return [a['cell'] for a in v['events'] if a['new']]
def sequence(a,b):
 n=min(len(a),len(b));p=0
 while p<n and a[p]==b[p]:p+=1
 s=0
 while s<n-p and a[-1-s]==b[-1-s]:s+=1
 same=a==b
 return {'equal':same,'N_count':len(a),'E_count':len(b),'common_prefix_items':p,'common_suffix_items':s,'first_difference':None if same else {'index':p,'N':a[p] if p<len(a) else None,'E':b[p] if p<len(b) else None},'N_changed_index_range':None if same else [p,len(a)-s-1],'E_changed_index_range':None if same else [p,len(b)-s-1],'range_definition':'after equal prefix and before maximal disjoint equal suffix; index alignment only, not causal affected region'}
def trace_sig(x):return [{k:e.get(k) for k in ('index','current','previous','pending_count','kind','goal')} for e in x['native']['raw'].get('trace',[])]
def csvwrite(name,rows):
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
def comparison(a,b):
 return {'raw_distance':diff(raw(a),raw(b)),'post_distance':diff(post(a),post(b)),'raw_route':sequence(raw(b)['path'],raw(a)['path']),'post_route':sequence(post(b)['path'],post(a)['path']),'raw_credit_order':sequence(order(raw(b)),order(raw(a))),'post_credit_order':sequence(order(post(b)),order(post(a))),'nominal_anchor_order':sequence([z['point'] for z in b['post']['locked_nominal_anchors']],[z['point'] for z in a['post']['locked_nominal_anchors']]),'time_delta':{k:a['timing'][k]-b['timing'][k] for k in ('native_entry_seconds','raw_common_end_to_end','post_increment','combined_end_to_end','raw_necessary_wrapper_seconds','post_engine_seconds','post_necessary_wrapper_seconds')},'raw_turn_delta':{k:raw(a)['metrics']['turns'].get(k,0)-raw(b)['metrics']['turns'].get(k,0) for k in ('total','90','180','other')},'post_turn_delta':{k:post(a)['metrics']['turns'].get(k,0)-post(b)['metrics']['turns'].get(k,0) for k in ('total','90','180','other')},'sign_convention':'first argument minus second; sequence N/E labels refer to second/first respectively, also for between-method comparisons'}
def main():
 assert not (H/'summary.json').exists()
 plan,sel,status=map(lambda n:read(H/n),('plan.json','selection.json','status.json'))
 assert len(status['completed'])+len(status['not_run'])+int(status['failure'] is not None)==36
 outputs={};views=[];timings=[];counts={};ag=defaultdict(Counter)
 for ident in status['completed']:
  x=read(H/'outputs'/(ident+'.json'));j=x['job'];outputs[(j['case'],j['seed'],j['branch'],j['env'])]=x
  timings.append(dict(j,**x['timing'],cold_import_seconds=x['cold_import_seconds'],independent_wall_seconds=x['independent_wall_seconds'],worker_wall_seconds=x['worker_wall_seconds']))
  ag['post_engine'].update(x['post_envelope']['counts']);ag['independent'].update(x['independent']['counts'])
  if j['branch']=='R':ag['R_runtime'].update(x['native']['repair_counts']);ag['R_structure'].update(x['independent']['repair_structure']['counts'])
  for alias,v in x['views'].items():
   ag['primary_virtual'].update(v['counts'])
   views.append(dict(j,alias=alias,view='post' if alias in ('B','C') else 'raw',metrics=v['metrics'],counts=v['counts'],source_sha256=sha(H/'outputs'/(ident+'.json'))))
  counts[ident]={'branch':j['branch'],'native_detail':None,'native_detail_status':'not_applicable_R' if j['branch']=='R' else 'unobservable_profile_OFF','main_scopes':x['query_scope_schema'],'post':x['post_envelope']['counts'],'independent':x['independent']['counts'],'R_runtime':x['native'].get('repair_counts'),'R_structure':x['independent'].get('repair_structure')}
 en=[];bc=[];br=[];behavior=[];six=[];excluded=[]
 for c in sel['selected']:
  for seed in plan['seeds']:
   missing=[(b,e) for b in ('B','R','C') for e in ('N','E') if (c['id'],seed,b,e) not in outputs]
   if missing:excluded.append({'case':c['id'],'seed':seed,'missing':missing});continue
   xx={b+e:outputs[(c['id'],seed,b,e)] for b in ('B','R','C') for e in ('N','E')}
   for b in ('B','R','C'):
    en.append(dict(case=c['id'],seed=seed,branch=b,**comparison(xx[b+'E'],xx[b+'N'])))
   for e in ('N','E'):
    bc.append(dict(case=c['id'],seed=seed,env=e,**comparison(xx['B'+e],xx['C'+e])))
    br.append(dict(case=c['id'],seed=seed,env=e,**comparison(xx['B'+e],xx['R'+e])))
   b=next(p for p in en if p['case']==c['id'] and p['seed']==seed and p['branch']=='B')
   bn,be=xx['BN'],xx['BE'];tr=sequence(bn['native']['raw'].get('trace',[]),be['native']['raw'].get('trace',[]));sig=sequence(trace_sig(bn),trace_sig(be))
   stage={v:{k:ediff(Expr.load(fun(be)['metrics']['stages'][k]['exact']),Expr.load(fun(bn)['metrics']['stages'][k]['exact'])) for k in ('to_first_witness','between_first_last_witness','after_last_witness_return')} for v,fun in [('raw',raw),('post',post)]}
   BR=next(p for p in br if p['case']==c['id'] and p['seed']==seed and p['env']=='E');BC=next(p for p in bc if p['case']==c['id'] and p['seed']==seed and p['env']=='E')
   shorter=[k for k,p in [('R_E',BR),('C_E',BC)] if p['post_distance']['sign']==1]
   changed=not sig['equal'] or not b['nominal_anchor_order']['equal'] or not b['post_credit_order']['equal']
   tier=3 if shorter and changed else 2 if shorter else 1
   behavior.append({'case':c['id'],'seed':seed,'full_trace':tr,'decision_signature':sig,'B_raw_route':b['raw_route'],'B_post_route':b['post_route'],'B_nominal_anchor_order':b['nominal_anchor_order'],'B_raw_credit_order':b['raw_credit_order'],'B_post_credit_order':b['post_credit_order'],'saved_B_trace':{e:xx['B'+e]['native']['raw'].get('trace',[]) for e in ('N','E')},'nominal_anchor_orders':{k:[z['point'] for z in x['post']['locked_nominal_anchors']] for k,x in xx.items()},'actual_credit_orders':{k:{'raw':order(raw(x)),'post':order(post(x))} for k,x in xx.items()},'stage_deltas':stage,'stage_convention':'midpoint of first intersecting segment interval, not unique physical first-entry time','R_intervals':{e:xx['R'+e]['native']['repair_intervals'] for e in ('N','E')},'B_R_E_same_raw_route':BR['raw_route']['equal'],'B_R_E_same_post_route':BR['post_route']['equal'],'B_R_E_same_nominal_anchor_order':BR['nominal_anchor_order']['equal'],'B_R_E_same_actual_credit_order':BR['post_credit_order']['equal'],'shorter_legal_post_references':shorter,'tier':tier,'necessary_detour_unknown':True,'causal_fault_proven':False,'P2_internal_final_order':None,'P2_order_observability':'not saved by frozen core; nominal wrapper anchors and actual credits are available separately, not reverse-inferred'})
   row={'case':c['id'],'seed':seed,'B_raw_delta':b['raw_distance']['display'],'B_post_delta':b['post_distance']['display'],'B_relative_post_delta':b['post_distance']['display']/post(bn)['metrics']['length'],'B_time_delta':b['time_delta']['combined_end_to_end'],'R_raw_delta':next(p for p in en if p['case']==c['id'] and p['seed']==seed and p['branch']=='R')['raw_distance']['display'],'R_post_delta':next(p for p in en if p['case']==c['id'] and p['seed']==seed and p['branch']=='R')['post_distance']['display'],'C_post_delta':next(p for p in en if p['case']==c['id'] and p['seed']==seed and p['branch']=='C')['post_distance']['display'],'B_E_minus_R_E':BR['post_distance']['display'],'B_E_minus_C_E':BC['post_distance']['display'],'B_N_minus_C_N':next(p for p in bc if p['case']==c['id'] and p['seed']==seed and p['env']=='N')['post_distance']['display'],'tier':tier}
   for k,x in xx.items():row.update({k+'_raw':raw(x)['metrics']['length'],k+'_post':post(x)['metrics']['length'],k+'_seconds':x['timing']['combined_end_to_end'],k+'_native_seconds':x['timing']['native_entry_seconds'],k+'_turns':post(x)['metrics']['turns'],k+'_termination':x['timing']['termination']})
   six.append(row)
 state=[]
 numeric=('B_raw_delta','B_post_delta','B_relative_post_delta','B_time_delta','R_raw_delta','R_post_delta','C_post_delta','B_E_minus_R_E','B_E_minus_C_E','B_N_minus_C_N')
 for c in sel['selected']:
  rr=[r for r in six if r['case']==c['id']];bb=[r for r in behavior if r['case']==c['id']]
  if rr:state.append({'case':c['id'],'base_id':c['base_id'],'shape':c['shape'],'seeds':len(rr),'seed_statistics':{k:stats([r[k] for r in rr]) for k in numeric},'means':{k:mean(r[k] for r in rr) for k in numeric},'same_B_decision_all':all(r['decision_signature']['equal'] for r in bb),'same_B_anchor_all':all(r['B_nominal_anchor_order']['equal'] for r in bb),'same_B_credit_all':all(r['B_post_credit_order']['equal'] for r in bb),'same_B_R_E_post_all':all(r['B_R_E_same_post_route'] for r in bb),'tiers':sorted({r['tier'] for r in bb})})
 timingkeys=('native_entry_seconds','raw_common_end_to_end','post_increment','combined_end_to_end','raw_necessary_wrapper_seconds','post_engine_seconds','post_necessary_wrapper_seconds','cold_import_seconds','independent_wall_seconds','worker_wall_seconds','artifact_flush_excluded_seconds')
 summary={'completed':len(status['completed']),'views':len(views),'E_N_pairs':len(en),'B_E_N_pairs':sum(p['branch']=='B' for p in en),'R_E_N_pairs':sum(p['branch']=='R' for p in en),'C_E_N_pairs':sum(p['branch']=='C' for p in en),'B_C_pairs':len(bc),'B_R_aux_pairs':len(br),'complete_six_branch_seed_rows':len(six),'states':state,'state_equal_statistics':{k:stats([s['means'][k] for s in state]) for k in numeric},'paired_statistics':{k:stats([r[k] for r in six]) for k in numeric},'timing':{b+e:{k:stats([r[k] for r in timings if r['branch']==b and r['env']==e]) for k in timingkeys} for b in ('B','R','C') for e in ('N','E')},'termination':dict(Counter(t['branch']+'_'+t['termination'] for t in timings)),'budget_and_late':{k:[t['id'] for t in timings if t[k]] for k in ('native_late','raw_stage_late','combined_late','post_late')},'post_fallbacks':dict(Counter(str(x['post_envelope']['fallback']) for x in outputs.values())),'tier_counts':dict(Counter(str(x['tier']) for x in behavior)),'failure':status['failure'],'not_run':status['not_run'],'excluded':excluded,'worst_B_post_delta':max(six,key=lambda x:x['B_post_delta']) if six else None,'worst_B_time_delta':max(six,key=lambda x:x['B_time_delta']) if six else None,'new_calls_in_export':{'core':0,'R':0,'post':0,'geometry':0,'BFS':0}}
 for name,data in [('72视图完整指标.json',views),('36入口完整计时.json',timings),('18环境配对.json',en),('12_B_C配对.json',bc),('12_B_R辅助配对.json',br),('6组六分支逐seed.json',six),('行为与阶段差异.json',behavior),('两状态等权.json',state),('summary.json',summary)]:dump(H/name,data)
 csvwrite('72视图完整指标.csv',[dict({k:v for k,v in x.items() if k not in ('metrics','counts')},**x['metrics']) for x in views]);csvwrite('36入口完整计时.csv',timings);csvwrite('6组六分支逐seed.csv',six)
 attempts=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];started=[x for x in attempts if x['event']=='started']
 ledger={'processing_attempted':len(started),'processing_completed':len(status['completed']),'PPCPP':sum(x['branch']=='B' for x in started),'P2':sum(x['branch']=='C' for x in started),'actual_core':sum(x['core_slot'] for x in started),'R':sum(x['R_slot'] for x in started),'technical_core':0,'warmup':0,'post_saved':sum((H/'outputs'/(j['id']+'_post_raw.json')).exists() for j in plan['jobs']),'views':len(views),'E_N_pairs':len(en),'B_C_pairs':len(bc),'pure_case_identities':6,'pure_case_attempts':len(read(H/'prechecks.json')['cases'])+len(read(H/'prechecks_preparation_v02_failed.json')['cases']),'preparation_import_failure_before_cases':1,'preparation_repairs':read(H/'preparation_repairs.json')['repairs_used'],'pure_fixture_R_attempts':read(H/'prechecks.json')['fixed_stub_repair_attempts'],'new_selection_geometry_BFS':0,'postformal_export_new_core_R_post_geometry_BFS':0,'failure':status['failure'],'not_run':status['not_run'],'no_holdout_new_maps_mechanism_closedloop':True}
 dump(H/'ledger.json',ledger);dump(H/'调用与查询总账.json',{'formal_per_entry':counts,'formal_aggregated_observed':{k:dict(v) for k,v in ag.items()},'fixed_pure_precheck':read(H/'prechecks.json'),'failed_prechecks':read(H/'prechecks_preparation_v02_failed.json'),'unobservable_native_detail':None,'counts_scope':'engine, primary virtual, independent, R runtime and R structure are disjoint instrument scopes; main_scopes service intersection total is an alias subtotal and must not be added again. OFF native detail unobservable, not zero; structural R audit has no BFS; source certificate geometry not rerun in this batch.'})
 dump(H/'失败触顶迟到及未运行.json',{'formal_failure':status['failure'],'not_run':status['not_run'],'excluded_pairs':excluded,'termination':summary['termination'],'late':summary['budget_and_late'],'fallbacks':summary['post_fallbacks'],'preparation_failures':['prechecks_preparation_v01_failed.json','prechecks_preparation_v02_failed.json'],'preparation_repairs':2})
 lines=['# 全量配对与状态等权','','单位米、秒。每行同状态同seed，N/E主配对；seed不当独立几何。原生与直达分列。完整精确符号/根式与时间/转弯变化见18环境配对、12_B_C配对、12_B_R辅助配对；全部视图含覆盖分母及最终H。','','|状态|seed|B_N原/直达|B_E原/直达|ΔB直达|R_E直达|C_N/C_E直达|B_N/B_E端到端秒|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in six:lines.append(f"|{r['case']}|{r['seed']}|{r['BN_raw']:.6f}/{r['BN_post']:.6f}|{r['BE_raw']:.6f}/{r['BE_post']:.6f}|{r['B_post_delta']:.9f}|{r['RE_post']:.6f}|{r['CN_post']:.6f}/{r['CE_post']:.6f}|{r['BN_seconds']:.6f}/{r['BE_seconds']:.6f}|")
 lines+=['','|状态三seed等权|ΔB原生|ΔB直达|ΔB/B_N|ΔR直达|B_E−R_E|B_E−C_E|B_N−C_N|B时间变化秒|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for s in state:
  a=s['means'];lines.append('|'+s['case']+'|'+'|'.join(f'{a[k]:.9f}' for k in numeric if k!='C_post_delta')+'|')
 # Explicit column selection avoids relying on dictionary order in the state table.
 lines=lines[:len(lines)-len(state)]
 for s in state:
  a=s['means'];lines.append(f"|{s['case']}|{a['B_raw_delta']:.6f}|{a['B_post_delta']:.9f}|{a['B_relative_post_delta']:.6%}|{a['R_post_delta']:.9f}|{a['B_E_minus_R_E']:.9f}|{a['B_E_minus_C_E']:.9f}|{a['B_N_minus_C_N']:.9f}|{a['B_time_delta']:.6f}|")
 lines+=['','每指标均值/中位/范围/P95/最大见两状态等权.json与summary.json，P95为ceil(.95n)顺序统计量，小样本接近最大值。时间单次测量可能受系统噪声影响，保留所有较慢/较快seed，不将两例推断为普遍加速。']
 (H/'02_全量配对与状态等权.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'ledger':ledger,'state':state,'termination':summary['termination']},ensure_ascii=False))
if __name__=='__main__':main()
