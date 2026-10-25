"""Saved-evidence-only old/new local-option audit. Standard library only.

No project imports, planner, scoring function, graph traversal or alternative
route execution. Pending sets are updated along the saved literal route.
"""
from pathlib import Path
import json,hashlib,collections,csv,math,sys,traceback,datetime
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021'
SEEDS=(20261020,20261021,20261022);CONDS=('CONTROL','H_SIDE','MIXED_SIDE','U_SIDE');METHODS=('PPCPP','P2_MULTI')
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(name,rows):
    with (H/name).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()} for r in rows])
def points(xs):return set(map(tuple,xs))
def classify(p,old,new):return 'old' if tuple(p) in old else 'new' if tuple(p) in new else 'not_pending'
def captures(c,route,T0,A):
    old=T0-points(c['covered']);new=A-points(c['covered']);events=[];stages=[]
    for i,p in enumerate(map(tuple,route)):
        kind=classify(p,old,new)
        if kind=='not_pending':continue
        (old if kind=='old' else new).remove(p);event=dict(route_index=i,cell=p,kind=kind);events.append(event)
        if stages and stages[-1]['kind']==kind:stages[-1]['captures']+=1;stages[-1]['end_route_index']=i
        else:stages.append(dict(kind=kind,captures=1,start_route_index=i,end_route_index=i))
    assert not old and not new,('unfinished_saved_route',len(old),len(new))
    return dict(captures=events,stages=stages,pattern='→'.join(s['kind'] for s in stages),alternations=max(0,len(stages)-1))
def examine(st,c,out):
    j=out['job'];raw=out['result']['raw'];route=list(map(tuple,raw['route']));trace=raw['branches']['P0']['trace'];F=points(c['free']);T0=points(c['initial_targets']);A=points(st['A']);hist=points(c['covered'])
    assert route and list(route[0])==c['current'] and list(route[-1])==c['base']
    assert all(p in F for p in route) and all(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for p,q in zip(route,route[1:]))
    assert not A&T0 and not A&hist and hist<=T0 and points(c['targets'])==T0|A and points(c['published_targets'])==T0|A
    assert T0=={(x,y) for x in range(4,4+st['L']) for y in range(4,4+st['w'])}
    assert raw['mode']=='PPCPP' and set(raw['branches'])=={'P0'} and list(map(tuple,raw['branches']['P0']['route']))==route
    assert trace and trace[0]['index']==0 and trace[-1]['kind']=='return'
    old=T0-hist;new=A-hist;cursor=0;decisions=[]
    for k,e in enumerate(trace):
        i=e['index'];end=trace[k+1]['index'] if k+1<len(trace) else len(route)-1
        assert isinstance(i,int) and i==cursor and i<=end<len(route),(j['id'],k,'index')
        old.discard(route[i]);new.discard(route[i]);assert tuple(e['current'])==route[i] and e['pending_count']==len(old)+len(new),(j['id'],k,'current_or_pending')
        previous=route[i-1] if i else tuple(c['previous']) if c['previous'] is not None else None
        if e['kind']!='return':assert (tuple(e['previous']) if e['previous'] is not None else None)==previous,(j['id'],k,'previous')
        else:assert 'previous' not in e and e['pending_count']==0 and k==len(trace)-1 and e['goal']==c['base']
        x,y=route[i];neighbors={(x-1,y),(x+1,y),(x,y-1),(x,y+1)}&F;old_adj=neighbors&old;new_adj=neighbors&new
        options=e.get('options',[]);cells=[tuple(o['cell']) for o in options];assert len(cells)==len(set(cells))
        category=classify(e['goal'],old,new);byclass={name:[o for o in options if classify(o['cell'],old,new)==name] for name in ('old','new')}
        tie=False;goal_score=None
        if e['kind']=='local':
            assert set(cells)==old_adj|new_adj and options and category in ('old','new'),(j['id'],k,'local_options')
            assert end==i+1 and tuple(e['goal'])==route[i+1],(j['id'],k,'local_goal_segment')
            assert all(isinstance(o['score'],(int,float)) and math.isfinite(o['score']) for o in options)
            top=max(o['score'] for o in options);top_classes={classify(o['cell'],old,new) for o in options if o['score']==top};tie=top_classes=={'old','new'}
            chosen=next(o for o in options if o['cell']==e['goal']);goal_score=chosen['score']
        elif e['kind']=='recovery':
            assert not old_adj and not new_adj and not options and category in ('old','new') and end>i and tuple(e['goal'])==route[end],(j['id'],k,'recovery_contract')
        else:assert e['kind']=='return' and not old and not new and tuple(e['goal'])==route[end]
        decisions.append(dict(state=st['id'],geometry=st['geometry'],condition=st['condition'],seed=j['seed'],source_output=str(B/'outputs'/f'{j["id"]}.json'),trace_index=k,trace_pointer=f'$.result.raw.branches.P0.trace[{k}]',route_index=i,next_trace_index=end,current=e['current'],previous=previous,kind=e['kind'],old_pending_count=len(old),new_pending_count=len(new),old_legal_neighbors=sorted(old_adj),new_legal_neighbors=sorted(new_adj),saved_options=options,old_options=byclass['old'],new_options=byclass['new'],goal=e['goal'],chosen_class=category if e['kind']!='return' else 'return',chosen_saved_score=goal_score,cross_class_highest_score_tie=tie,is_competition=bool(e['kind']=='local' and old_adj and new_adj),A_already_collected=len(A-new),literal_segment=route[i:end+1]))
        # Movement is observed from the literal saved segment, never planned.
        for p in route[i+1:end+1]:old.discard(p);new.discard(p)
        cursor=end
    assert not old and not new
    first_A=next((i for i,p in enumerate(route) if p in A),None)
    entry=None
    if first_A is not None:
        if first_A==0:entry=dict(mode='initial_occupancy',route_index=0,owner_trace_index=None,owner_pointer=None,was_competition=False,local_only_new_options=False,local_single_new_option=False,literal_segment=[route[0]])
        else:
            owner=next(d for d in decisions if d['route_index']<=first_A-1<d['next_trace_index']);assert owner['kind'] in ('local','recovery')
            entry=dict(mode=owner['kind'],route_index=first_A,owner_trace_index=owner['trace_index'],owner_pointer=owner['trace_pointer'],was_competition=owner['is_competition'],local_only_new_options=bool(owner['kind']=='local' and not owner['old_options'] and owner['new_options']),local_single_new_option=bool(owner['kind']=='local' and len(owner['saved_options'])==1 and owner['new_options']),literal_segment=owner['literal_segment'],source_output=owner['source_output'])
    opportunities=[d for d in decisions if d['is_competition']];first=opportunities[0] if opportunities else None
    summary=dict(state=st['id'],geometry=st['geometry'],condition=st['condition'],seed=j['seed'],trace_entries=len(trace),local_entries=sum(d['kind']=='local' for d in decisions),recovery_entries=sum(d['kind']=='recovery' for d in decisions),return_entries=1,competition_count=len(opportunities),competition_trace_indices=[d['trace_index'] for d in opportunities],competition_choice_counts=dict(collections.Counter(d['chosen_class'] for d in opportunities)),competition_cross_class_ties=sum(d['cross_class_highest_score_tie'] for d in opportunities),first_competition=first,first_A_capture_index=first_A,first_A_entry=entry,competition_before_first_A=bool(first and first_A is not None and first['route_index']<first_A),first_competition_A_already_collected=first['A_already_collected'] if first else None,first_competition_is_first_entry_decision=bool(first and entry and first['trace_index']==entry['owner_trace_index']),all_trace_prefix_neighbor_checks_passed=True)
    return decisions,summary
def main():
    assert not (H/'analysis.json').exists() and not (H/'STOP.json').exists(),'do not overwrite/resume evidence'
    manifest=read(B/'completion_manifest.json')['files'];source_rows=[]
    for n,h in manifest.items():
        p=B/n;actual=sha(p);assert actual==h,('source_hash_drift',str(p));source_rows.append(dict(path=str(p),sha256=actual,expected_sha256=h))
    save(H/'source_hash_manifest.json',dict(source_completion_manifest_sha256=sha(B/'completion_manifest.json'),files=source_rows,source_files=len(source_rows)))
    states=read(B/'states.json');groups=read(B/'groups.json');a=read(B/'analysis.json');assert len(states)==48 and len(groups)==12 and len(a['pairs'])==144
    pair={(p['case'],p['seed']):p for p in a['pairs']};old_rows={r['id']:r for r in a['rows']};old_state={s['id']:s for s in a['views']['timely']['states']};decisions=[];call_audits=[];sequences=[];equivalence=[];summaries=[];variants=[]
    for st in states:
        c=read(B/st['input']);T0=points(c['initial_targets']);A=points(st['A']);outs={};analyses={};fingerprints=[]
        for seed in SEEDS:
            ppjob=f'formal_{st["id"]}_{seed}_PPCPP';pp=read(B/'outputs'/f'{ppjob}.json');assert pp['input_sha256']==sha(B/st['input']) and pp['job']['case']==st['id'] and pp['job']['seed']==seed
            dd,ss=examine(st,c,pp);outs[seed]=pp;analyses[seed]=(dd,ss);fingerprints.append(dict(seed=seed,source_job=ppjob,source_file_sha256=sha(B/'outputs'/f'{ppjob}.json'),route_sha256=canon(pp['result']['raw']['route']),non_time_trace_sha256=canon(pp['result']['raw']['branches']['P0']['trace'])))
            call_audits.append({k:v for k,v in ss.items() if k not in ('first_competition','first_A_entry')})
            for method in METHODS:
                jid=f'formal_{st["id"]}_{seed}_{method}';out=pp if method=='PPCPP' else read(B/'outputs'/f'{jid}.json');assert out['input_sha256']==sha(B/st['input']) and out['job']['case']==st['id'] and out['job']['seed']==seed
                route=out['result']['raw']['route'];assert route[0]==c['current'] and route[-1]==c['base'];assert all(tuple(p) in points(c['free']) for p in route);assert all(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for p,q in zip(route,route[1:]))
                seq=captures(c,route,T0,A);metrics=old_rows[jid]['metrics'];completion=max((z['route_index'] for z in seq['captures']),default=0)
                assert metrics['length']==len(route)-1 and metrics['completion_step']==completion and metrics['return_tail_steps']==len(route)-1-completion
                sequences.append(dict(state=st['id'],geometry=st['geometry'],condition=st['condition'],seed=seed,method=method,source_output=str(B/'outputs'/f'{jid}.json'),source_sha256=sha(B/'outputs'/f'{jid}.json'),**seq))
                assert pair[st['id'],seed]['legal'] and pair[st['id'],seed]['timely']
        equal=len({(r['route_sha256'],r['non_time_trace_sha256']) for r in fingerprints})==1
        equivalence.append(dict(state=st['id'],geometry=st['geometry'],condition=st['condition'],three_routes_equal=len({r['route_sha256'] for r in fingerprints})==1,three_non_time_traces_equal=len({r['non_time_trace_sha256'] for r in fingerprints})==1,collapsed=equal,seeds=fingerprints,trace_time_fields_removed=[],note='Native saved P0 trace contains no timing fields; compared all saved trace fields exactly'))
        local_variants=[]
        for seed in (SEEDS[:1] if equal else SEEDS):
            dd,ss=analyses[seed];ss=dict(ss,equivalent_seeds=list(SEEDS) if equal else [seed],representative_seed_only=equal,previous_first_A_event=old_rows[f'formal_{st["id"]}_{seed}_PPCPP']['pp_first_A_event']);local_variants.append(ss);variants.append(ss)
            decisions += [dict(d,equivalent_seeds=list(SEEDS) if equal else [seed]) for d in dd]
        first_classes={v['first_competition']['chosen_class'] if v['first_competition'] else 'none' for v in local_variants};entry_modes={v['first_A_entry']['mode'] if v['first_A_entry'] else 'CONTROL_no_A' for v in local_variants}
        s0=old_state[st['id']];summaries.append(dict(state=st['id'],geometry=st['geometry'],group=st['group'],condition=st['condition'],L=st['L'],w=st['w'],boundary_count=st['boundary_count'],three_PP_seeds_equivalent=equal,decision_variants=len(local_variants),competition_counts_by_seed={str(seed):analyses[seed][1]['competition_count'] for seed in SEEDS},any_competition=any(v['competition_count'] for v in local_variants),all_variants_have_competition=all(v['competition_count'] for v in local_variants),first_competition_choice=next(iter(first_classes)) if len(first_classes)==1 else 'varies_across_seeds',first_entry_mode=next(iter(entry_modes)) if len(entry_modes)==1 else 'varies_across_seeds',first_entry_is_competitive=all(v['first_A_entry'] and v['first_A_entry']['was_competition'] for v in local_variants),competition_before_first_A=all(v['competition_before_first_A'] for v in local_variants),first_competition_A_already_collected=[v['first_competition_A_already_collected'] for v in local_variants],first_entry_local_only_new_options=all(v['first_A_entry'] and v['first_A_entry']['local_only_new_options'] for v in local_variants),first_entry_local_single_new_option=all(v['first_A_entry'] and v['first_A_entry']['local_single_new_option'] for v in local_variants),PP_sequence_patterns=sorted({s['pattern'] for s in sequences if s['state']==st['id'] and s['method']=='PPCPP'}),P2_sequence_patterns=sorted({s['pattern'] for s in sequences if s['state']==st['id'] and s['method']=='P2_MULTI'}),existing_pair_denominator=3,existing_mean_D=s0['mean_D'],existing_D_range=s0['D_range'],existing_mean_delta_C=s0['mean_delta']['completion_step'],existing_mean_delta_R=s0['mean_delta']['return_tail_steps'],existing_by_seed=[dict(seed=seed,D=pair[st['id'],seed]['D'],delta_C=pair[st['id'],seed]['delta']['completion_step'],delta_R=pair[st['id'],seed]['delta']['return_tail_steps']) for seed in SEEDS]))
    condition=[]
    for cond in CONDS:
        rr=[r for r in summaries if r['condition']==cond];vv=[v for v in variants if v['condition']==cond]
        condition.append(dict(condition=cond,states=len(rr),base_geometries=len({r['geometry'] for r in rr}),with_competition_states=sum(r['any_competition'] for r in rr),without_competition_states=sum(not r['any_competition'] for r in rr),first_competition_choice_state_counts=dict(collections.Counter(r['first_competition_choice'] for r in rr)),first_entry_mode_state_counts=dict(collections.Counter(r['first_entry_mode'] for r in rr)),first_entry_competitive_states=sum(r['first_entry_is_competitive'] for r in rr),competition_before_first_A_states=sum(r['competition_before_first_A'] for r in rr),first_entry_local_only_new_options_states=sum(r['first_entry_local_only_new_options'] for r in rr),first_entry_local_single_new_option_states=sum(r['first_entry_local_single_new_option'] for r in rr),PP_sequence_state_counts=dict(collections.Counter('|'.join(r['PP_sequence_patterns']) for r in rr)),P2_sequence_state_counts=dict(collections.Counter('|'.join(r['P2_sequence_patterns']) for r in rr)),competition_geometry_ids=sorted({r['geometry'] for r in rr if r['any_competition']}),canonical_decision_variant_count=len(vv),canonical_competition_decisions=sum(v['competition_count'] for v in vv),existing_mean_D=sum(r['existing_mean_D'] for r in rr)/len(rr)))
    data=dict(scope='READONLY_PRECONDITION_REVIEW_NOT_NEW_EXPERIMENT',states=summaries,variants=variants,conditions=condition,seed_equivalence=equivalence,call_trace_audits=call_audits,decisions=decisions,sequences=sequences,source_experiment='v0.4',budgets=dict(new_real_entries=0,new_core_calls=0,new_candidates=0,coverage_exact_searches=0,counterfactual_simulations=0,BFS=0,Dijkstra=0,new_routes=0,new_route_figures=0),notes=['Competition requires both classes among actual legal local options. Global remaining work alone is insufficient.','P2 sequences use its own saved route and own prefix; not a replacement action at a PPCPP decision state.','Canonical per-state decisions are collapsed only after equality of all three saved routes and complete non-time P0 traces.'])
    save(H/'analysis.json',data);save(H/'三seed等价表.json',equivalence);save(H/'逐决策机会账.json',decisions);save(H/'全部144条PPCPP前缀邻格核对.json',call_audits);save(H/'两方法288条首次采集阶段序列.json',sequences)
    csvsave('48状态完整汇总.csv',summaries);csvsave('36事件状态主表.csv',[s for s in summaries if s['condition']!='CONTROL']);csvsave('逐决策机会账.csv',decisions);csvsave('按条件状态与几何汇总.csv',condition);csvsave('三seed等价表.csv',equivalence)
    save(H/'zero_call_ledger.json',dict(**data['budgets'],source_real_entries_reused=306,source_formal_outputs_read=288,PPCPP_saved_calls_audited=144,P2_saved_routes_read=144,states=48,event_states=36,control_states=12,independent_base_geometries=6,original_verify_rerun=False,source_original_BFS_ledger_unchanged=72,reviewer_prior_BFS_separate=24,algorithm_modules_imported=[n for n in sys.modules if n in ('runtime','candidate','p2_adapter','ppcpp','p2_search_audit','common','analysis')]))
    assert not read(H/'zero_call_ledger.json')['algorithm_modules_imported']
    print(json.dumps(dict(status='READONLY_ANALYSIS_COMPLETE',all_three_seed_equivalent=all(e['collapsed'] for e in equivalence),canonical_decisions=len(decisions),conditions=condition,budgets=data['budgets']),ensure_ascii=False),flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as ex:
        if not (H/'STOP.json').exists():save(H/'STOP.json',dict(stage='readonly_audit',reason=repr(ex),new_planner_calls=0,new_graph_searches=0))
        raise
