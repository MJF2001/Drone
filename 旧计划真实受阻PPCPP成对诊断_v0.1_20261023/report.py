"""Export saved results only. Exact length arithmetic, no planning/geometry replay."""
from common import *
from collections import Counter,defaultdict
from statistics import mean,median
from fractions import Fraction
from math import ceil
import sys,csv,json,math
sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
from center_bench_v01_20261022.exact import Expr,Uncertain,certificate
def stats(xs):
 xs=sorted(xs);return {'n':len(xs),'mean':mean(xs) if xs else None,'median':median(xs) if xs else None,'P95':xs[ceil(.95*len(xs))-1] if xs else None,'max':max(xs) if xs else None,'min':min(xs) if xs else None}
def expr(x):return Expr.load(x['metrics']['length_certificate']['exact'])
def diff(x,y):
 z=expr(x)-expr(y)
 try:s=z.sign()
 except Uncertain:s='uncertain'
 lo,hi=z.interval();return {'display':x['metrics']['length']-y['metrics']['length'],'sign':s,'certificate':certificate(z),'certified_interval':[str(lo),str(hi)]}
def order(x):return [e['cell'] for e in x['events'] if e['new']]
def goal_trace(x):return [{k:t.get(k) for k in ('current','previous','pending_count','kind','goal')} for t in x['native']['raw'].get('trace',[])]
def first_difference(a,b):
 for i in range(max(len(a),len(b))):
  u=a[i] if i<len(a) else None;v=b[i] if i<len(b) else None
  if u!=v:return {'index':i,'N':u,'E':v}
 return None
def writecsv(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def main():
 assert not (H/'summary.json').exists()
 plan=read(H/'plan.json');status=read(H/'status.json');sel=read(H/'selection.json');jobs={j['id']:j for j in plan['jobs']}
 assert len(status['completed'])+len(status['not_run'])+int(status['failure'] is not None)==len(plan['jobs'])
 outputs={};views=[];timings=[];exclusions=[];counts={'selection':sel['counts'],'pure_round_1':read(H/'prechecks_preparation_v01_failed.json'),'pure_round_2':read(H/'prechecks.json'),'formal':{}}
 ag={k:Counter() for k in ('primary_virtual','post','independent','R_runtime','R_structure')}
 for ident in status['completed']:
  x=read(H/'outputs'/(ident+'.json'));j=x['job'];outputs[(j['case'],j['seed'],j['branch'],j['env'])]=x
  timings.append(dict(j,**x['timing'],cold_import_seconds=x['cold_import_seconds'],independent_wall_seconds=x['independent_wall_seconds'],worker_wall_seconds=x['worker_wall_seconds']))
  if j['branch']=='R':ag['R_runtime'].update(x['native']['repair_counts']);ag['R_structure'].update(x['independent']['repair_structure']['counts'])
  ag['post'].update(x['post_envelope']['counts']);ag['independent'].update(x['independent']['counts'])
  for alias,v in x['views'].items():
   ag['primary_virtual'].update(v['counts'])
   views.append({'id':ident,'case':j['case'],'base_id':j['base_id'],'seed':j['seed'],'branch':j['branch'],'env':j['env'],'view':'post' if alias in ('B','C') else 'raw','alias':alias,'termination':x['timing']['termination'],'post_late':x['timing']['post_late'],'metrics':v['metrics'],'counts':v['counts'],'source_sha256':sha(H/'outputs'/(ident+'.json'))})
  counts['formal'][ident]={'branch':j['branch'],'core_detail':None,'core_detail_status':'not_applicable_R' if j['branch']=='R' else 'unobservable_profile_OFF','main_query_scope':x['query_scope_schema'],'post':x['post_envelope']['counts'],'independent':x['independent']['counts'],'R_runtime':x['native'].get('repair_counts'),'R_structure':x['independent'].get('repair_structure')}
 pairs=[];analysis=[]
 for c in sel['selected']:
  for seed in plan['seeds']:
   ks=[(c['id'],seed,b,e) for b in ('B','R','C') for e in ('N','E')]
   if not all(k in outputs for k in ks):exclusions.append({'case':c['id'],'seed':seed,'reason':'missing complete 6-branch pair','missing':[k for k in ks if k not in outputs]});continue
   xx={b+e:outputs[(c['id'],seed,b,e)] for b in ('B','R','C') for e in ('N','E')}
   vv={key:x['views']['C' if key[0]=='C' else 'B'] for key,x in xx.items()}
   row={'case':c['id'],'base_id':c['base_id'],'shape':c['shape'],'seed':seed,'B_E_minus_B_N':diff(vv['BE'],vv['BN']),'R_E_minus_R_N':diff(vv['RE'],vv['RN']),'B_E_minus_R_E':diff(vv['BE'],vv['RE']),'B_N_minus_R_N':diff(vv['BN'],vv['RN']),'B_E_minus_C_E':diff(vv['BE'],vv['CE']),'B_N_minus_C_N':diff(vv['BN'],vv['CN'])}
   interact=(expr(vv['BE'])-expr(vv['CE']))-(expr(vv['BN'])-expr(vv['CN']))
   try:interactsign=interact.sign()
   except Uncertain:interactsign='uncertain'
   row['environment_flow_interaction_only']={'certificate':certificate(interact),'sign':interactsign,'display':row['B_E_minus_C_E']['display']-row['B_N_minus_C_N']['display']}
   for k,v in vv.items():row[k+'_distance']=v['metrics']['length'];row[k+'_time']=xx[k]['timing']['combined_end_to_end'];row[k+'_turns']=v['metrics']['turns'];row[k+'_termination']=xx[k]['timing']['termination']
   row['B_time_delta']=row['BE_time']-row['BN_time'];row['B_relative_distance_delta']=row['B_E_minus_B_N']['display']/row['BN_distance'];row['B_turn_delta']={k:vv['BE']['metrics']['turns'].get(k,0)-vv['BN']['metrics']['turns'].get(k,0) for k in ('total','90','180','other')}
   anchors={k:[p['point'] for p in xx[k]['post']['locked_nominal_anchors']] for k in xx};credits={k:order(vv[k]) for k in xx}
   bn,be=xx['BN'],xx['BE'];firstgoal=first_difference(goal_trace(bn),goal_trace(be));firstrecord=first_difference(bn['native']['raw'].get('trace',[]),be['native']['raw'].get('trace',[]))
   anc=anchors['BN'];last=anc[-1] if anc else None
   def cut_last(path):
    if last is None:return 0
    return next(i for i,p in enumerate(path) if p==last)
   bnpath,be_path=vv['BN']['path'],vv['BE']['path'];bncut,becut=cut_last(bnpath),cut_last(be_path)
   prefixsame=bnpath[:bncut+1]==be_path[:becut+1]
   later_same=anchors['BN']==anchors['BE'] and credits['BN']==credits['BE'] and firstgoal is None
   shorter=[k for k in ('RE','CE') if diff(vv['BE'],vv[k])['sign']==1]
   # An order difference from C already present in N is not promoted to a B event mechanism.
   changed_B_decision=firstgoal is not None or anchors['BN']!=anchors['BE']
   tier=3 if shorter and changed_B_decision else 2 if shorter else 1
   detail={'case':c['id'],'base_id':c['base_id'],'seed':seed,'old_failed_intervals':read(H/c['history'])['old_suffix_E_invalid_interiors'],'B_N_E_first_decision_signature_difference':firstgoal,'B_N_E_first_full_trace_difference':firstrecord,'B_N_E_same_nominal_anchor_order':anchors['BN']==anchors['BE'],'B_N_E_same_actual_credit_order':credits['BN']==credits['BE'],'B_N_E_same_last_nominal_center':anchors['BN'][-1:]==anchors['BE'][-1:],'B_N_E_same_actual_last_credit':credits['BN'][-1:]==credits['BE'][-1:],'B_post_prefix_through_last_anchor_equal':prefixsame,'B_N_return_suffix':bnpath[bncut:],'B_E_return_suffix':be_path[becut:],'nominal_anchor_orders':anchors,'actual_credit_witness_orders':credits,'B_N_E_trace_signature_equal':firstgoal is None,'B_vs_R_E_same_raw_route':be['native']['raw']['route']==xx['RE']['native']['raw']['route'],'B_vs_R_E_same_post_route':be['post']['vertices']==xx['RE']['post']['vertices'],'more_efficient_legal_references':shorter,'tier':tier,'tier_label':{1:'未获可避免证据（含无增程/等长反例）',2:'存在同条件更短参照，未定位PPCPP事件决策原因',3:'更短参照及可核实B事件行为差异，仍非因果证明'}[tier],'P2_internal_final_visit_order':None,'P2_internal_order_status':'not saved; wrapper anchors and actual credit are separate, not inverse inferred','stage_convention':'midpoint first segment witness; not unique physical first-entry time','B_stages_N':vv['BN']['metrics']['stages'],'B_stages_E':vv['BE']['metrics']['stages']}
   pairs.append(row);analysis.append(detail)
 state=[]
 for c in sel['selected']:
  rr=[p for p in pairs if p['case']==c['id']];aa=[a for a in analysis if a['case']==c['id']]
  if not rr:continue
  state.append({'case':c['id'],'base_id':c['base_id'],'shape':c['shape'],'seed_count':len(rr),'delta_B':mean(p['B_E_minus_B_N']['display'] for p in rr),'relative_delta_B':mean(p['B_relative_distance_delta'] for p in rr),'delta_R':mean(p['R_E_minus_R_N']['display'] for p in rr),'B_E_minus_R_E':mean(p['B_E_minus_R_E']['display'] for p in rr),'B_E_minus_C_E':mean(p['B_E_minus_C_E']['display'] for p in rr),'B_N_minus_C_N':mean(p['B_N_minus_C_N']['display'] for p in rr),'time_delta_B':mean(p['B_time_delta'] for p in rr),'same_B_anchor_order_all':all(a['B_N_E_same_nominal_anchor_order'] for a in aa),'same_B_credit_order_all':all(a['B_N_E_same_actual_credit_order'] for a in aa),'same_B_decision_signature_all':all(a['B_N_E_trace_signature_equal'] for a in aa),'prefix_through_last_equal_all':all(a['B_post_prefix_through_last_anchor_equal'] for a in aa),'tiers':sorted({a['tier'] for a in aa})})
 timingstats={b+e:{k:stats([t[k] for t in timings if t['branch']==b and t['env']==e]) for k in ('native_entry_seconds','combined_end_to_end','post_increment','cold_import_seconds','independent_wall_seconds','worker_wall_seconds')} for b in ('B','R','C') for e in ('N','E')}
 aggregate={'complete_pairs':len(pairs),'state_count':len(state),'delta_B_pairs':stats([p['B_E_minus_B_N']['display'] for p in pairs]),'delta_B_state_equal':stats([p['delta_B'] for p in state]),'relative_delta_B_state_equal':stats([p['relative_delta_B'] for p in state]),'B_time_delta_pairs':stats([p['B_time_delta'] for p in pairs]),'B_time_delta_state_equal':stats([p['time_delta_B'] for p in state]),'B_delta_signs':dict(Counter(str(p['B_E_minus_B_N']['sign']) for p in pairs)),'B_E_R_E_signs':dict(Counter(str(p['B_E_minus_R_E']['sign']) for p in pairs)),'B_E_C_E_signs':dict(Counter(str(p['B_E_minus_C_E']['sign']) for p in pairs)),'same_B_nominal_order_pairs':sum(a['B_N_E_same_nominal_anchor_order'] for a in analysis),'same_B_credit_order_pairs':sum(a['B_N_E_same_actual_credit_order'] for a in analysis),'same_B_decision_signature_pairs':sum(a['B_N_E_trace_signature_equal'] for a in analysis),'same_B_prefix_through_last_anchor_pairs':sum(a['B_post_prefix_through_last_anchor_equal'] for a in analysis),'same_B_R_post_E_pairs':sum(a['B_vs_R_E_same_post_route'] for a in analysis),'tier_counts':dict(Counter(str(a['tier']) for a in analysis)),'timing':timingstats,'termination':dict(Counter(t['branch']+'_'+t['termination'] for t in timings)),'post_late_ids':[t['id'] for t in timings if t['post_late']],'native_late_ids':[t['id'] for t in timings if t['native_late']],'raw_stage_late_ids':[t['id'] for t in timings if t['raw_stage_late']],'failure':status['failure'],'not_run':status['not_run'],'exclusions':exclusions,'worst_delta_B_pair':max(pairs,key=lambda p:p['B_E_minus_B_N']['display']) if pairs else None,'worst_relative_delta_B_pair':max(pairs,key=lambda p:p['B_relative_distance_delta']) if pairs else None,'new_calls_in_export':{'core':0,'R':0,'post':0,'geometry':0,'BFS':0}}
 counts['formal_aggregate_observed']={k:dict(v) for k,v in ag.items()};counts['unobservable']={'B_C_native_detailed_queries':None,'primary_and_independent_internal_box_calls_without_hooks':None,'not_zero':True}
 dump(H/'同状态同seed六分支配对.json',pairs);dump(H/'PPCPP行为与返航差异.json',analysis);dump(H/'六状态等权.json',state);dump(H/'216视图完整指标.json',views);dump(H/'正式逐入口计时.json',timings);dump(H/'调用与几何BFS总账.json',counts);dump(H/'summary.json',aggregate)
 writecsv('18组完整成对结果.csv',pairs);writecsv('216视图指标.csv',[dict({k:v for k,v in x.items() if k not in ('metrics','counts')},**x['metrics']) for x in views]);writecsv('108入口计时.csv',timings)
 attempts=[json.loads(x) for x in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];started=[a for a in attempts if a['event']=='started']
 ledger={'attempted_processing':len(started),'completed_processing':len(status['completed']),'PPCPP_attempted':sum(a['branch']=='B' for a in started),'P2_attempted':sum(a['branch']=='C' for a in started),'core_attempted':sum(a['core_slot'] for a in started),'R_attempted':sum(a['R_slot'] for a in started),'technical_core':0,'warmup':0,'post_attempted_saved':sum((H/'outputs'/(j['id']+'_post_raw.json')).exists() for j in plan['jobs']),'pure_case_identities':12,'pure_case_attempts':len(read(H/'prechecks_preparation_v01_failed.json')['cases'])+len(read(H/'prechecks.json')['cases']),'preparation_repairs':1,'failure':status['failure'],'not_run':status['not_run'],'selection_counts':sel['counts'],'mechanism_implemented_as_new_algorithm':False,'holdout':False,'new_base_maps':0,'new_region_experiments':0,'new_closed_loops':0,'readonly_export_core_R_post_geometry_BFS':0}
 dump(H/'ledger.json',ledger);dump(H/'失败触顶迟到及未运行.json',{'failure':status['failure'],'not_run':status['not_run'],'native_budget_ids':[t['id'] for t in timings if t['termination']=='budget'],'late_ids':aggregate['post_late_ids'],'incomplete_pair_exclusions':exclusions,'preparation_failure_receipt':'prechecks_preparation_v01_failed.json'})
 table=['# 六例三seed及状态等权','', '|状态|seed|B_N m|B_E m|ΔB m|R_N m|R_E m|C_N m|C_E m|B_N s|B_E s|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for p in pairs:table.append('|'+p['case']+'|'+str(p['seed'])+'|'+ '|'.join(f'{p[k]:.9f}' for k in ('BN_distance','BE_distance'))+'|'+f"{p['B_E_minus_B_N']['display']:.9f}"+'|'+ '|'.join(f'{p[k]:.9f}' for k in ('RN_distance','RE_distance','CN_distance','CE_distance','BN_time','BE_time'))+'|')
 table+=['','R/C全计时见108入口计时.csv；全部原/直达指标见216视图完整指标.json，不能只读此摘表。所有完整距离差均保留根式证书及认证符号，不按浮点近零猜测。','', '|状态（3seed等权）|ΔB m|ΔB/B_N|ΔR m|B_E−R_E m|B_E−C_E m|B时间变化s|B锚点/信用/决策签名是否全相同|','|---|---:|---:|---:|---:|---:|---:|---|']
 for p in state:table.append(f"|{p['case']}|{p['delta_B']:.9f}|{p['relative_delta_B']:.6%}|{p['delta_R']:.9f}|{p['B_E_minus_R_E']:.9f}|{p['B_E_minus_C_E']:.9f}|{p['time_delta_B']:.9f}|{p['same_B_anchor_order_all']}/{p['same_B_credit_order_all']}/{p['same_B_decision_signature_all']}|")
 (H/'02_全量配对与状态等权表.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
 print(json.dumps({'completed':len(status['completed']),'pairs':len(pairs),'state_equal':state,'aggregate_except_timing':{k:v for k,v in aggregate.items() if k not in ('timing','worst_delta_B_pair','worst_relative_delta_B_pair')}},ensure_ascii=False))
if __name__=='__main__':main()
