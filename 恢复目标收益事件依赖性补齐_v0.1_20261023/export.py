"""Saved four-cell export: new N separated from reused E; no new route queries."""
from common import *
from eventdep_labels import validate
from eventdep_arithmetic import calculate
from eventdep_arithmetic_audit import audit as audit_arithmetic
from collections import Counter,defaultdict
from statistics import mean
import importlib.util,time
OLD=ROOT/'覆盖受阻恢复目标单变量诊断_v0.1_20261023'
sp=importlib.util.spec_from_file_location('_eventdep_accepted_saved_helpers',OLD/'recovery_diag_export.py');helpers=importlib.util.module_from_spec(sp);sp.loader.exec_module(helpers)
stats=helpers.stats;csvwrite=helpers.csvwrite;order=helpers.order
def seq(a,b):
 def rename(x):
  if isinstance(x,dict):return {k.replace('OFF','T0').replace('ON','T1'):rename(v) for k,v in x.items()}
  if isinstance(x,list):return [rename(v) for v in x]
  return x
 return rename(helpers.seq(a,b))
def view(x,v):return x['views']['A' if v=='raw' else 'B']
def main():
 assert not (H/'summary.json').exists()
 plan=read(H/'plan.json');status=read(H/'status.json');sel=read(H/'selection.json');four={};views=[];times=[];queries={};agg=defaultdict(Counter);source_rows=[]
 for ident in status['completed']:
  p=H/'outputs'/(ident+'.json');x=read(p);j=x['job'];validate(j);key=j['case'],j['seed'],'N',j['target_label'];four[key]=x
  row={'case':j['case'],'seed':j['seed'],'environment':'N','target_label':j['target_label'],'target_intervention_enabled':j['target_intervention_enabled'],'origin':'new_N','source':str(p),'source_sha256':sha(p),'id':ident};source_rows.append(row)
  for alias,v in x['views'].items():views.append(dict(row,view='raw' if alias=='A' else 'post',alias=alias,metrics=v['metrics'],counts=v['counts']));agg['new_N_primary_virtual'].update(v['counts'])
  times.append(dict(row,**x['timing'],diagnostic_hook_seconds=x['native']['diagnostic']['diagnostic_hook_seconds'],cold_import_seconds=x['cold_import_seconds'],independent_wall_seconds=x['independent_wall_seconds'],decision_audit_seconds=x['decision_audit']['seconds'],worker_wall_seconds=x['worker_wall_seconds']))
  for name,counters in [('new_N_post',x['post_envelope']['counts']),('new_N_independent_credit',x['independent']['counts']),('new_N_decision_audit',x['decision_audit']['counts']),('new_N_diagnostic',x['native']['diagnostic']['counts'])]:agg[name].update(counters)
  queries[ident]={'origin':'new_N','environment':'N','target_label':j['target_label'],'enabled':j['target_intervention_enabled'],'native_profile':None,'diagnostic':x['native']['diagnostic']['counts'],'post':x['post_envelope']['counts'],'virtual':[v['counts'] for v in x['views'].values()],'independent_geometry_credit':x['independent']['counts'],'independent_decision':x['decision_audit']['counts'],'main_scope_alias':x['query_scope_schema']}
 for ref in read(H/'reused_E/index.json')['references']:
  validate(ref);w=read(H/ref['wrapper']);x=w['saved_output'];assert sha(ref['source'])==ref['source_sha256'];four[(ref['case'],ref['seed'],'E',ref['target_label'])]=x
  row={k:ref[k] for k in ('id','case','seed','environment','target_label','target_intervention_enabled','origin','source','source_sha256','wrapper')};source_rows.append(row)
  for alias,v in x['views'].items():views.append(dict(row,view='raw' if alias=='A' else 'post',alias=alias,metrics=v['metrics'],counts=v['counts']))
 groups=[];proofs=[];arithmetic=[];missing=[];turnrows=[]
 for c in sel['selected']:
  spec=read(H/c['spec']);k=spec['trace_record']
  for seed in plan['seeds']:
   keys=[(c['id'],seed,e,t) for e in ('N','E') for t in ('T0','T1')]
   if not all(key in four for key in keys):missing.append({'case':c['id'],'seed':seed,'missing':[key for key in keys if key not in four]});continue
   xx={e+'_'+t:four[(c['id'],seed,e,t)] for e in ('N','E') for t in ('T0','T1')};row={'case':c['id'],'seed':seed,'shape':'Z','new_processing':2,'reused_processing':2,'four_distances':{},'effects':{}}
   for v in ('raw','post'):
    certs={key:view(x,v)['metrics']['length_certificate'] for key,x in xx.items()};p=calculate(certs);a=audit_arithmetic(certs,p);arithmetic.append({'case':c['id'],'seed':seed,'view':v,'primary':p,'independent':a,'input_length_certificates':certs})
    row['effects'][v]=p['values'];row['four_distances'][v]={key:view(x,v)['metrics']['length'] for key,x in xx.items()}
    turnrows.append({'case':c['id'],'seed':seed,'view':v,'four_turns':{key:{cat:view(x,v)['metrics']['turns'].get(cat,0) for cat in ('total','90','180','other')} for key,x in xx.items()},'T0_minus_T1':{env:{cat:view(xx[env+'_T0'],v)['metrics']['turns'].get(cat,0)-view(xx[env+'_T1'],v)['metrics']['turns'].get(cat,0) for cat in ('total','90','180','other')} for env in ('N','E')}})
   # E contrast equals the already sealed E_ON minus E_OFF certificate exactly.
   previous=next(p for p in read(OLD/'6对ON减OFF全指标.json') if p['case']==c['id'] and p['seed']==seed)
   assert row['effects']['raw']['D_E']['certificate']['exact']==previous['raw_distance_delta']['certificate']['exact'] and row['effects']['post']['D_E']['certificate']['exact']==previous['post_distance_delta']['certificate']['exact']
   traces=[x['native']['raw']['trace'][:k] for x in xx.values()];assert all(t==traces[0]==spec['original_trace'][:k] for t in traces)
   allproof={}
   for key,x in xx.items():
    tr=x['native']['diagnostic']['trigger'];env,target=key.split('_');assert tr['pending']==spec['pending'] and tr['current']==spec['current'] and tr['previous']==spec['previous'] and tr['chosen_goal']==spec[target]
    assert x['native']['raw']['route'][:tr['route_index']+1]==spec['original_route_prefix']
    path=tr['actual_recovery_path'];other='T1' if target=='T0' else 'T0';trace=x['native']['raw']['trace'];local=next((dict(e,trace_record=i) for i,e in enumerate(trace) if i>k and e['kind']=='local'),None)
    allproof[key]={'environment':env,'target_label':target,'target_intervention_enabled':x['job']['target_intervention_enabled'],'origin':'new_N' if env=='N' else 'reused_E_not_new_call','trigger':tr,'full_pending_match':True,'prefix_route_semantics_match':True,'other_target':spec[other],'recovery_path_passes_other_target':spec[other] in path,'other_target_position_in_recovery':path.index(spec[other]) if spec[other] in path else None,'first_local_after_recovery':local,'first_local_goes_to_other_target':local is not None and local['goal']==spec[other],'native_partition':helpers.native_partition(x,spec),'post_credit_order':order(x['views']['B']),'last_post_credit':order(x['views']['B'])[-1:],'post_metrics_stages':x['views']['B']['metrics']['stages'],'audit_source':'saved decision_audit and independent geometry/credit receipts; not rerun for reused E'}
   compar={env:{'raw_route':seq(view(xx[env+'_T0'],'raw')['path'],view(xx[env+'_T1'],'raw')['path']),'post_route':seq(view(xx[env+'_T0'],'post')['path'],view(xx[env+'_T1'],'post')['path']),'nominal_anchors':seq([z['point'] for z in xx[env+'_T0']['post']['locked_nominal_anchors']],[z['point'] for z in xx[env+'_T1']['post']['locked_nominal_anchors']]),'post_credit_order':seq(order(xx[env+'_T0']['views']['B']),order(xx[env+'_T1']['views']['B']))} for env in ('N','E')}
   row['target_comparisons']=compar;row['four_last_credits']={key:value['last_post_credit'] for key,value in allproof.items()};row['four_post_turns']={key:x['views']['B']['metrics']['turns'] for key,x in xx.items()}
   ds=row['effects']['post'];dn,de,inter=[ds[name]['sign'] for name in ('D_N','D_E','I')]
   classification='sign_uncertain' if 'uncertain' in (dn,de,inter) else 'same_preference_zero_interaction' if dn==de and inter==0 else 'same_preference_nonzero_interaction' if dn==de else 'strict_preference_reversal' if dn*de==-1 else 'preference_to_or_from_tie'
   row['classification']=classification
   row['natural_complete_four_cells']=all(x['timing']['termination']=='natural' and not any(x['timing'][f] for f in ('native_late','raw_stage_late','combined_late','post_late')) for x in xx.values())
   row['new_N_ON_minus_OFF_time']={field:xx['N_T1']['timing'][field]-xx['N_T0']['timing'][field] for field in ('native_entry_seconds','post_increment','combined_end_to_end')};row['cross_batch_E_N_time_interaction']='forbidden/not computed'
   groups.append(row);proofs.append({'case':c['id'],'seed':seed,'all_four_common_prefix_pending_heading_proven':True,'cells':allproof,'target_comparisons':compar,'caution':'full post does not lock prefix; witness midpoint not unique physical time; no strict native phase decomposition moved to post'})
 states=[]
 for c in sel['selected']:
  rr=[r for r in groups if r['case']==c['id']]
  if not rr:continue
  states.append({'case':c['id'],'shape':'Z','seed_count':len(rr),'effects':{v:{key:stats([r['effects'][v][key]['display'] for r in rr]) for key in ('D_N','D_E','I')} for v in ('raw','post')},'four_lengths':{v:{key:stats([r['four_distances'][v][key] for r in rr]) for key in ('N_T0','N_T1','E_T0','E_T1')} for v in ('raw','post')},'classifications':dict(Counter(r['classification'] for r in rr)),'physical_same_E_pairs':sum(r['target_comparisons']['E']['raw_route']['equal'] and r['target_comparisons']['E']['post_route']['equal'] for r in rr),'physical_same_N_pairs':sum(r['target_comparisons']['N']['raw_route']['equal'] and r['target_comparisons']['N']['post_route']['equal'] for r in rr)})
 tkeys=('native_entry_seconds','raw_common_end_to_end','post_increment','post_engine_seconds','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds','combined_end_to_end','diagnostic_hook_seconds','cold_import_seconds','independent_wall_seconds','decision_audit_seconds','worker_wall_seconds')
 tstats=[{'case':c['id'],'environment':'N','target_label':target,'origin':'new_N','statistics':{key:stats([t[key] for t in times if t['case']==c['id'] and t['target_label']==target]) for key in tkeys}} for c in sel['selected'] for target in ('T0','T1')]
 summary={'new_N_completed':len(status['completed']),'new_N_views':sum(v['origin']=='new_N' for v in views),'reused_E_outputs':12,'reused_E_views':sum(v['origin']!='new_N' for v in views),'combined_processing_routes':len(source_rows),'combined_views':len(views),'complete_four_cell_groups':len(groups),'state_count':len(states),'states':states,'first_two_N_OFF_gate_passed':status['two_OFF_gate_passed'],'all_N_OFF_old_B_N_equal':all(x['off_equivalence']['passed'] for key,x in four.items() if key[2:] == ('N','T0')),'new_N_termination':dict(Counter(t['target_label']+'_'+t['termination'] for t in times)),'new_N_late_ids':{k:[t['id'] for t in times if t[k]] for k in ('native_late','raw_stage_late','combined_late','post_late')},'failure':status['failure'],'not_run':status['not_run'],'missing_groups':missing,'all_four_cells_natural':all(g['natural_complete_four_cells'] for g in groups),'arithmetic_groups_checked':len(arithmetic),'new_geometry_core_post_BFS_in_export':0,'cross_batch_time_interaction_or_ranking_computed':False,'exploratory_seen_Z_only':True}
 newviews=[v for v in views if v['origin']=='new_N'];oldviews=[v for v in views if v['origin']!='new_N']
 for name,data in [('24新增N视图完整指标.json',newviews),('24复用E视图完整指标.json',oldviews),('48四格视图完整指标.json',views),('24条处理路线来源索引.json',source_rows),('12新增N入口完整计时.json',times),('新N逐状态计时统计.json',tstats),('6组四格对照.json',groups),('四格路径与local机制证据.json',proofs),('独立算术核验.json',arithmetic),('四格转弯完整表.json',turnrows),('两状态等权.json',states),('summary.json',summary)]:dump(H/name,data)
 csvwrite('24新增N视图完整指标.csv',[dict({k:v for k,v in row.items() if k not in ('metrics','counts')},**row['metrics']) for row in newviews]);csvwrite('24复用E视图完整指标.csv',[dict({k:v for k,v in row.items() if k not in ('metrics','counts')},**row['metrics']) for row in oldviews]);csvwrite('12新增N入口完整计时.csv',times)
 csvwrite('6组四格距离与效应.csv',[{'case':g['case'],'seed':g['seed'],'classification':g['classification'],**{v+'_'+key:value for v,values in g['four_distances'].items() for key,value in values.items()},**{v+'_'+key:value['display'] for v,values in g['effects'].items() for key,value in values.items()}} for g in groups])
 attempts=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];started=[r for r in attempts if r['event']=='started']
 ledger={'new_N_core_attempted':len(started),'new_N_core_completed':len(status['completed']),'new_N_post_saved':sum((H/'outputs'/(j['id']+'_post_raw.json')).exists() for j in plan['jobs']),'new_N_views':len(newviews),'reused_E_processing':12,'reused_E_views':len(oldviews),'combined_processing_routes':len(source_rows),'combined_views':len(views),'four_cell_groups':len(groups),'new_E_R_P2_history_warmup_technical_calls':0,'pure_fixed_identities':6,'pure_item_attempts':len(read(H/'prechecks.json')['cases']),'preparation_repairs':read(H/'preparation_repairs.json')['used'],'new_coverage_optimization_or_geometry_queries_after_batch':0,'arithmetic_primary_calls':len(arithmetic),'arithmetic_independent_calls':len(arithmetic),'failure':status['failure'],'not_run':status['not_run']};dump(H/'ledger.json',ledger)
 ac=defaultdict(Counter)
 for r in arithmetic:ac['primary'].update(r['primary']['counts']);ac['independent'].update(r['independent']['counts'])
 dump(H/'调用与查询及算术总账.json',{'new_N_per_entry':queries,'new_N_observed_aggregate':{k:dict(v) for k,v in agg.items()},'reused_E_not_executed_here':read(H/'reused_E/index.json'),'pure_prechecks':read(H/'prechecks.json'),'arithmetic_counts':{k:dict(v) for k,v in ac.items()},'arithmetic_seconds':{'primary':sum(r['primary']['seconds'] for r in arithmetic),'independent':sum(r['independent']['seconds'] for r in arithmetic)},'unobservable_native_profile':None,'aliases':'post service_intersections/post_service_intersections same call; independent post prefixes contain aliases; main_scope totals alias subtotal. Do not sum repeated aliases or treat old E receipt work as newly executed.','no_cross_batch_time_inference':True})
 dump(H/'失败触顶迟到与未运行.json',{'formal_failure':status['failure'],'not_run':status['not_run'],'missing_four_cells':missing,'new_N_late':summary['new_N_late_ids'],'new_N_termination':summary['new_N_termination'],'preparation_repairs':0,'new_E_R_P2_calls':0,'postformal_new_core_calls':0})
 lines=['# 逐seed四格完整距离与交互效应','','N为新增运行，E为只读复用。D_N=N_T0−N_T1，D_E=E_T0−E_T1，I=D_E−D_N。负D表示T0短；负I表示障碍增强T0相对优势。单位米。','','|状态|seed|N,T0原/直达|N,T1原/直达|E,T0原/直达（复用）|E,T1原/直达（复用）|D_N直达|D_E直达|I直达|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for g in groups:
  vals=g['four_distances'];eff=g['effects']['post'];lines.append('|'+g['case']+'|'+str(g['seed'])+'|'+'|'.join(f"{vals['raw'][key]:.0f}/{vals['post'][key]:.9f}" for key in ('N_T0','N_T1','E_T0','E_T1'))+'|'+'|'.join(f"{eff[key]['display']:.9f}" for key in ('D_N','D_E','I'))+'|')
 lines+=['','原生D_N/D_E/I、精确根式和认证符号见6组四格对照及独立算术核验；转弯各类别见四格转弯完整表；全部分母/暂缓/信用/H/资源返航见48视图。新N计时独立成表，不计算跨批时间交互。','', '|状态三seed等权|原生D_N/D_E/I|直达D_N/D_E/I|判断|','|---|---|---|---|']
 for s in states:lines.append('|'+s['case']+'|'+' / '.join(f"{s['effects']['raw'][k]['mean']:.6f}" for k in ('D_N','D_E','I'))+'|'+' / '.join(f"{s['effects']['post'][k]['mean']:.9f}" for k in ('D_N','D_E','I'))+'|'+str(s['classifications'])+'|')
 lines+=['','先逐seed后状态等权；均值/中位/范围/P95/最坏全部保留。只有2个尺度Z，事后目标来自已见分歧，不作显著性/跨形状/在线机制或创新结论。']
 (H/'02_六组四格距离与效应表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'ledger':ledger,'states':states,'all_N_OFF_equal':summary['all_N_OFF_old_B_N_equal']},ensure_ascii=False))
if __name__=='__main__':main()
