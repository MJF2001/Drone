"""Read saved artifacts only; additional descriptive tables, no planning replay."""
from common import *
from report import stats,sequence,raw,post,order,ex,ediff
from collections import Counter
from statistics import mean
import sys
from center_bench_v01_20261022.exact import Expr
def display(cert):
 lo,hi=Expr.load(cert['exact']).interval();return float((lo+hi)/2)
def main():
 plan=read(H/'plan.json');outs=[read(H/'outputs'/(j['id']+'.json')) for j in plan['jobs'] if j['id'] in read(H/'status.json')['completed']]
 timings=[];stages=[];relations=[];identity=[]
 for c in read(H/'selection.json')['selected']:
  for b in ('B','R','C'):
   for e in ('N','E'):
    xx=[x for x in outs if x['job']['case']==c['id'] and x['job']['branch']==b and x['job']['env']==e]
    if not xx:continue
    timings.append({'case':c['id'],'branch':b,'env':e,'n':len(xx),'stats':{k:stats([x['timing'][k] for x in xx]) for k in ('native_entry_seconds','raw_common_end_to_end','post_engine_seconds','post_increment','combined_end_to_end','raw_necessary_wrapper_seconds','post_necessary_wrapper_seconds')},'outside_main':{k:stats([x[k] for x in xx]) for k in ('cold_import_seconds','independent_wall_seconds','worker_wall_seconds')},'clock_delta_warning':'three single runs per input; no controlled CPU isolation or repeated time significance test'})
    identity.append({'case':c['id'],'branch':b,'env':e,'all_raw_routes_equal':all(raw(x)['path']==raw(xx[0])['path'] for x in xx),'all_post_routes_equal':all(post(x)['path']==post(xx[0])['path'] for x in xx),'all_credit_orders_equal':all(order(post(x))==order(post(xx[0])) for x in xx)})
  for seed in plan['seeds']:
   xx={x['job']['branch']+x['job']['env']:x for x in outs if x['job']['case']==c['id'] and x['job']['seed']==seed}
   if len(xx)!=6:continue
   n,e=xx['BN'],xx['BE']
   for view,fun in [('raw',raw),('post',post)]:
    keys=('to_first_witness','between_first_last_witness','after_last_witness_return')
    stages.append({'case':c['id'],'seed':seed,'view':view,'N':{k:display(fun(n)['metrics']['stages'][k]) for k in keys},'E':{k:display(fun(e)['metrics']['stages'][k]) for k in keys},'delta':{k:display(fun(e)['metrics']['stages'][k])-display(fun(n)['metrics']['stages'][k]) for k in keys},'first_credit':{'N':order(fun(n))[:1],'E':order(fun(e))[:1]},'last_credit':{'N':order(fun(n))[-1:],'E':order(fun(e))[-1:]},'unique_physical_service_time':False})
   def sig(x):return [{k:z.get(k) for k in ('current','previous','pending_count','kind','goal')} for z in x['native']['raw'].get('trace',[])]
   relations.append({'case':c['id'],'seed':seed,'semantic_decisions_without_route_index':sequence(sig(n),sig(e)),'B_N_equals_R_N_raw':raw(n)['path']==raw(xx['RN'])['path'],'B_N_equals_R_N_post':post(n)['path']==post(xx['RN'])['path'],'R_N_no_repair':xx['RN']['native']['repair_intervals']==[],'R_E_fixed_repair_intervals':xx['RE']['native']['repair_intervals'],'B_E_feasible_in_N_by_set_inclusion':{'proof':'F_E subset F_N; same physical H, P, U, S/base/resource; saved independent E path is legal and covers U, so same path is legal and complete in N without geometry replay. This does not prove optimality or general event benefit.','included':ps(e['input']['free'])<=ps(n['input']['free'])},'B_R_E_difference_is_not_connection_only':order(post(e))!=order(post(xx['RE']))})
 dump(H/'逐状态计时统计.json',timings);dump(H/'B阶段距离与末采补充.json',stages);dump(H/'顺序衔接与种子一致性.json',{'relations':relations,'repeat_identity':identity,'no_new_core_R_post_geometry_BFS':True})
 q=read(H/'调用与查询总账.json');q['counts_scope']='Flat counters are preserved as emitted, not summed across names. Post engine service_intersections and post_service_intersections are aliases of the same call; independent post prefix counters contain aliases too. Main query_scope.total is an alias subtotal, not extra work. target_box_tests counts bounding-box tests, not expensive region intersections. Scopes are separately reported; OFF native detail is null, not zero.'
 a=q['formal_aggregated_observed'];p=a['post_engine'];v=a['primary_virtual'];i=a['independent'];r=a['R_runtime']
 assert p['service_intersections']==p['post_service_intersections']
 q['selected_nonduplicated_counters']={'post_candidate_geometry':p['candidate'],'post_source_unit_validation':p['source_validation'],'post_output_geometry_validation':p['output_validation'],'post_service_intersections_one_alias':p['service_intersections'],'primary_virtual_target_box_tests':v['target_box_tests'],'primary_virtual_expensive_intersections':v['execute_service_intersections'],'primary_virtual_post_path_geometry':v['main_geometry'],'independent_virtual_target_box_tests':i['target_box_tests'],'independent_virtual_expensive_intersections':i['independent_service_intersections'],'independent_post_geometry':i['post_independent_geometry'],'independent_post_box_tests_one_alias':i['post_independent_service_intersections'],'formal_R_BFS_started':r['BFS_started'],'formal_R_BFS_popped':r['BFS_popped'],'formal_R_BFS_neighbor_tests':r['neighbor_tests'],'not_a_total_cpu_work_estimate':True}
 dump(H/'调用与查询总账.json',q)
 lines=['# 每状态计时与转弯摘表','','每个环境/方法三个原seed；列值均为主端到端秒的均值/中位/[最小,最大]。核心、修复、直达、包装及主外费用完整分列见逐状态计时统计.json；逐入口见36入口完整计时.csv。','','|状态|分支/环境|原生或修复均值秒|直达引擎均值秒|必要包装均值秒|端到端均值/中位/[范围]秒|','|---|---|---:|---:|---:|---|']
 for t in timings:
  a=t['stats'];z=a['combined_end_to_end'];wrap=a['raw_necessary_wrapper_seconds']['mean']+a['post_necessary_wrapper_seconds']['mean'];lines.append(f"|{t['case']}|{t['branch']}/{t['env']}|{a['native_entry_seconds']['mean']:.6f}|{a['post_engine_seconds']['mean']:.6f}|{wrap:.6f}|{z['mean']:.6f}/{z['median']:.6f}/[{z['min']:.6f},{z['max']:.6f}]|")
 lines+=['','|状态|B原生N→E转弯（总/90/180/其他）|B直达N→E转弯（总/90/180/其他）|','|---|---|---|']
 for c in read(H/'selection.json')['selected']:
  n,e=[next(x for x in outs if x['job']['case']==c['id'] and x['job']['branch']=='B' and x['job']['seed']==20261020 and x['job']['env']==env) for env in ('N','E')]
  def txt(v):return '/'.join(str(v['metrics']['turns'].get(k,0)) for k in ('total','90','180','other'))
  lines.append(f"|{c['id']}|{txt(raw(n))} → {txt(raw(e))}|{txt(post(n))} → {txt(post(e))}|")
 lines+=['','B与R三个seed的同环境路线一致；以上转弯代表全部三seed，不删除零类。C的逐seed转弯完整保存，距离更短不等于转弯更少。转弯是非零方向变化，90/180/其他互斥，不计起始历史来向。','', '阶段长度依据内部中点见证，仅作固定证据切分，不是唯一物理入区时刻。大Z的B直达增量发生在首末见证之间，返航项不变；中Z首末见证间增加约0.236068米，末采后项减少约0.747283米，合计−0.511215米。原生分别+2米，以及覆盖项+1/收尾−1合计0。']
 (H/'03_实际成本转弯与阶段说明.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print({'timing_groups':len(timings),'stage_rows':len(stages),'new_search_calls':0})
if __name__=='__main__':main()
