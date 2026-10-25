"""Read-only source/data review. Standard library only; no experiment imports.
Only set/index checks on SAVED routes; no new route or simulated execution.
"""
from pathlib import Path
import json,hashlib,ast,sys,traceback
H=Path(__file__).resolve().parent;R=H.parent
A=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
C=A/'continuous_history_diagnostics';F=A/'frozen_baselines/v2_20261012/source'
V=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021';S=R/'复杂障碍压力开发测试_v0.1_20261021'
DOC=R/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009'
SEEN={}
def digest(b):return hashlib.sha256(b).hexdigest()
def raw(p):
    p=Path(p).resolve();assert p.is_relative_to(R) and not any('holdout' in q.lower() or '留出' in q for q in p.parts),p
    b=p.read_bytes();h=digest(b)
    if str(p) in SEEN:assert SEEN[str(p)]==h,p
    SEEN[str(p)]=h;return b
def read(p):return json.loads(raw(p).decode('utf-8-sig'))
def text(p):return raw(p).decode('utf-8-sig')
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def pts(x):return set(map(tuple,x))
def pathcheck(c,route):
    # Existing sequence only. No graph reachability or shortest paths.
    assert route and route[0]==c['current'] and route[-1]==c['base'] and pts(route)<=pts(c['free'])
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
    assert not pts(c['targets'])-pts(c['covered'])-pts(route) and len(route)-1<=c['distance_budget']
def manifests(folder):
    p=folder/'sha256.json';m=read(p)
    for n,h in m.items():assert digest(raw(folder/n))==h,(folder,n)
    return dict(directory=str(folder),files=len(m),matched=True)
def sources():
    names=['continuous_history_inputs_20261016.py','test_continuous_history_20261016.py','prepare_continuous_history_runs_20261016.py','verify_continuous_preparation_20261016.py','run_continuous_comparison_20261016.py','verify_continuous_comparison_20261016.py','report_continuous_comparison_20261016.py','portable_frozen.py',
      'PPCPP侧向拓宽开发诊断_v0.4_20261021/generate.py','复杂障碍压力开发测试_v0.1_20261021/stress.py','复杂障碍压力开发测试_v0.1_20261021/预登记.md',
      'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/runtime.py','PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/candidate.py','PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/p2_adapter.py','PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/预登记.md',
      'PPCPP结构候选新开发验证_v0.1_20261020/validation.py','基线复现准备_20261019/独立版_v0.2/ppcpp.py','基线复现准备_20261019/ppcpp_independent.py',
      '评价指标完整补算与数据审计_v0.1_20261020/metrics.py','评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py',
      'CAP目标状态契约与接续原型_v0.2_20261020/runtime/target_contract.py','CAP目标状态契约与接续原型_v0.2_20261020/replay_saved.py','CAP目标状态契约与接续原型_v0.2_20261020/CAP目标状态契约与接续原型报告_20261020.md',
      'TRACE_CAP适配复现_20261020/runtime/planners.py','Cstar连接器等价提速_v0.7_20261020/runtime/history_core/public_map.py',
      'PPCPP单步新开发验证负责人审核_20261021/审核与关闭结论.md','连续事件执行评估第一步只读审查执行稿_给sol_20261021.md']
    paths=[R/n for n in names]+[F/n for n in ('baseline_suite.py','p2_search_audit.py','model.py','unified_geometry.py','audit.py')]+[A/n for n in ('scale_scene_generator_20261014.py','scenarios.py','scenarios_v3.py')]+[DOC/n for n in ('02_论文主题与具体研究问题.md','42_三种基线适配审查与冻结说明_20261012.md','00_阅读入口.md','67_连续执行历史开发验证协议与输入预检_20261016.md','68_连续执行初始计划准备与事件状态核验_20261016.md','69_连续执行历史共同预算比较结果_20261016.md')]
    anchors=[]
    tokens=('def ','initial_targets','previous','old_route','distance_budget','unsupported_','deferred','checkpoint(','publish(','case_sha256','route[:','for progress','for count','if cur not in f','seed','deadline','global_complete','published_observation')
    for p in paths:
        s=text(p)
        if p.suffix=='.py':ast.parse(s,filename=str(p))
        hits=[dict(line=i,text=line) for i,line in enumerate(s.splitlines(),1) if any(t in line for t in tokens)]
        anchors.append(dict(path=str(p),sha256=SEEN[str(p.resolve())],lines=len(s.splitlines()),anchors=hits))
    pairs=[]
    for folder in (C/'preparation_v0.1_20261016/source_snapshot',C/'comparison_v0.1_20261016/source_snapshot'):
        for p in folder.glob('*.py'):
            b=raw(p);current=R/p.name;pairs.append(dict(saved=str(p),current=str(current),saved_sha256=digest(b),current_sha256=digest(raw(current)),equal=b==raw(current)))
    return anchors,pairs
def old_continuous():
    pre=C/'preflight_v0.1_20261016';prep=C/'preparation_v0.1_20261016';check=C/'preparation_verification_v0.1_20261016';comp=C/'comparison_v0.1_20261016'
    manifest_rows=[manifests(p) for p in (pre,prep,check,comp,C/'comparison_verification_v0.1_20261016')]
    jobs=read(prep/'protocol.json')['jobs'];events={e['map_id']:e for e in read(pre/'records.json')};checks={e['map_id']:e for e in read(check/'checks.json')};rows=[]
    assert len(jobs)==len(events)==len(checks)==10
    for j in jobs:
        p=Path(j['case']);c=read(p);out=read(prep/'runs'/(j['run_id']+'.json'));route=out['raw']['route'];pathcheck(c,route);h=checks[j['map_id']]['history'];cut=h['index'];T=pts(c['targets']);prefix=route[:cut+1];history=pts(prefix)&T
        assert c['covered']==[] and c['current']==c['base'] and c['distance_budget']==8*len(c['free'])
        assert set(c['metadata'])=={'map_id','split','stage','initial_policy'}
        assert out['case_sha256']==digest(raw(p)) and out['seed']==out['raw']['seed']==j['seed']
        assert prefix==h['executed_route'] and route[cut:]==h['old_route'] and h['current']==route[cut] and pts(h['covered'])==history
        assert len(history)>=(len(T)+1)//2 and len(pts(route[:cut])&T)<(len(T)+1)//2
        assert h['executed_steps']==cut and h['remaining_budget']==c['distance_budget']-cut
        e=events[j['map_id']];eventpath=Path(e['event_source']);event=read(eventpath);assert digest(raw(eventpath))==e['event_source_sha256']
        statepath=check/'cases'/(j['map_id']+'.json');state=read(statepath);published=pts(event['metadata']['published_targets']);free=pts(event['free'])
        assert state['current']==route[cut] and pts(state['covered'])==history and state['old_route']==route[cut:] and state['distance_budget']==c['distance_budget']-cut
        assert pts(state['targets'])==published&free and pts(state['metadata']['published_targets'])==published and pts(state['metadata']['deferred_targets'])==published-free-history
        assert not history-(T&pts(prefix));assert 'previous' not in state
        rows.append(dict(map_id=j['map_id'],initial_job=j['run_id'],initial_input=str(p),initial_output=str(prep/'runs'/(j['run_id']+'.json')),event_source=str(eventpath),response_input=str(statepath),initial_output_sha256=digest(raw(prep/'runs'/(j['run_id']+'.json'))),response_input_sha256=digest(raw(statepath)),cut=cut,covered=len(history),executed_steps=cut,remaining_budget=state['distance_budget'],derived_previous=route[cut-1] if cut else None,previous_stored_in_response_input=False,earliest_50percent_pass=True,exact_prefix_suffix_budget_pass=True,published_active_deferred_pass=True,external_event_publications_per_map_in_this_chain=1))
    cj=read(comp/'protocol.json')['jobs'];assert len(cj)==80;response=[]
    for j in cj:
        p=Path(j['case']);c=read(p);outpath=comp/'runs'/(j['run_id']+'.json');out=read(outpath);pathcheck(c,out['raw']['route'])
        assert p==check/'cases'/(j['map_id']+'.json') and out['case_sha256']==digest(raw(p))
        assert out['method']==j['method'] and out['seed']==j['seed'] and out['budget']==j['budget']
        response.append(dict(run_id=j['run_id'],map_id=j['map_id'],method=j['method'],input=str(p),input_sha256=digest(raw(p)),output=str(outpath),output_sha256=digest(raw(outpath)),input_is_fixed_first_event_case=True,route_saved_but_not_fed_to_next_event_in_this_controller=True))
    return dict(manifests=manifest_rows,histories=rows,responses=response,classification=2,initial_plan_method='P2_MULTI',response_methods=sorted({j['method'] for j in cj}),response_inputs_unique=len({r['input_sha256'] for r in response}),response_calls_saved=80,type4_not_evidenced_for_this_specific_chain=True)
def widening():
    maps=read(V/'maps.json');groups=read(V/'groups.json');states=read(V/'states.json');assert len(maps)==6 and len(groups)==12 and len(states)==48;rows=[]
    for m in maps:
        c=read(V/m['input']);outpath=V/'outputs'/('prep_'+m['id']+'.json');route=read(outpath)['result']['raw']['route'];pathcheck(c,route)
        gg=[g for g in groups if g['geometry']==m['id']];assert len(gg)==2
        for g in gg:
            h=read(V/'history'/(g['id']+'.json'));cut=g['history_cut'];prefix=route[:cut+1];history=pts(prefix)&pts(c['targets']);assert h['prefix']==prefix and h['old_suffix']==route[cut:] and pts(h['H'])==history
            B={(x,4) for x in range(4,4+m['L'])};assert len(pts(prefix)&B)==g['boundary_count'] and len(pts(route[:cut])&B)<g['boundary_count']
            for s in [s for s in states if s['group']==g['id']]:
                inp=read(V/s['input']);assert pts(inp['covered'])==history and inp['current']==route[cut] and inp['previous']==route[cut-1] and inp['old_route']==route[cut:] and inp['distance_budget']==c['distance_budget']-cut and pts(inp['initial_targets'])==pts(c['targets'])
                assert not pts(s['A'])&history
            rows.append(dict(group=g['id'],shared_initial_output=str(outpath),history_file=str(V/'history'/(g['id']+'.json')),cut=cut,source='same one original preparation route; independent cut',prefix_previous_credit_resource_pass=True))
    return dict(classification=3,maps=6,groups=12,states=48,checks=rows,second_cut_not_from_first_event_response=True)
def obstacles():
    states=read(S/'states.json');preps=read(S/'prep_order.json');assert len(states)==16 and len(preps)==2;rows=[]
    for j in preps:
        c=read(S/j['input']);route=read(S/'prep'/(j['id']+'.json'))['result']['raw']['route'];pathcheck(c,route)
        for s in [s for s in states if s['prep']==j['id']]:
            inp=read(S/'inputs'/(s['name']+'.json'));cut=s['history_index'];history=pts(route[:cut+1]);pub=pts(inp['published_targets']);free=pts(inp['free']);assert pts(inp['covered'])==history and inp['current']==route[cut] and inp['previous']==route[cut-1] and inp['old_route']==route[cut:]
            assert pts(inp['targets'])==pub&free and pts(inp['deferred_targets'])==pub-free-history
            assert inp['distance_budget']==c['distance_budget'] and cut>0
            rows.append(dict(state=s['name'],classification=3,cut=cut,history_and_previous_exact=True,deferred=len(pub-free-history),historical_now_blocked=len(history-free),connection_opened_count=len(s['connection_opened']),saved_budget=inp['distance_budget'],initial_budget=c['distance_budget'],would_be_cumulative_remaining=c['distance_budget']-cut,resource_budget_is_snapshot_limit_not_cumulative_debit=True,input=str(S/'inputs'/(s['name']+'.json'))))
    return dict(states=16,checks=rows,position_dependent_opening_states=sum(bool(r['connection_opened_count']) for r in rows),resource_not_debited_states=16,scope='Declared saved single-event pressure fixtures, not a bug claim against that protocol; cannot reuse as common-exogenous-world execution.')
def main():
    assert not (H/'saved_evidence_checks.json').exists();anchors,pairs=sources();old=old_continuous();wide=widening();stress=obstacles()
    cap=read(R/'CAP目标状态契约与接续原型_v0.2_20261020/mechanism_cases.json');cap_replay=read(R/'CAP目标状态契约与接续原型_v0.2_20261020/saved_replay.json')
    result=dict(passed=True,old_continuous=old,widening=wide,stress=stress,source_snapshot_identity=pairs,other_scope=dict(CAP='saved one-region API mechanism cases and same-map residual split; not external multi-event publication proof',CAP_saved_payload_type=type(cap).__name__,CAP_saved_replay_keys=list(cap_replay)),claim_boundary='No type4 evidence found in the specifically traced chains; no claim that entire repository contains no such evidence',new_planner_calls=0,new_cores=0,new_candidates=0,new_graph_searches=0,new_routes=0,new_real_or_simulated_closed_loops=0,old_modules_imported=[])
    save(H/'saved_evidence_checks.json',result);save(H/'source_anchors.json',anchors);save(H/'source_hashes.json',SEEN)
    save(H/'zero_call_ledger.json',dict(task='B路线第一步只读能力审查',planner_entries=0,native_cores=0,candidate_trials=0,BFS=0,Dijkstra=0,Astar=0,coverage_exact=0,new_routes=0,new_worlds=0,real_closed_loops=0,simulated_closed_loops=0,old_verify_or_tests_executed=0,old_algorithm_modules_imported=[],allowed_work='read bytes/JSON/AST; saved path adjacency, prefix/index, sets and hashes only',source_files_read=len(SEEN),read_source_unchanged_at_end=all(digest(Path(p).read_bytes())==h for p,h in SEEN.items())))
    print(json.dumps(dict(status='PASS',source_files=len(SEEN),saved_initial_histories=10,saved_independent_responses=80,widening_independent_cuts=12,stress_inputs=16,position_dependent_openings=stress['position_dependent_opening_states'],all_new_algorithm_graph_execution_counts=0),ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except BaseException:
        with (H/'audit_failure.log').open('x',encoding='utf8') as f:f.write(traceback.format_exc())
        raise
