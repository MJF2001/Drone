"""Independent reward/prefix audit of saved routes; no planner/graph imports."""
from common import *
import math
from intervention import exception_budget
def adjacent(p):
    x,y=p;return ((x+1,y),(x,y+1),(x-1,y),(x,y-1))
def saved_audit(c,out,expected_trigger=None):
    x=out['result'];raw=x['raw'];n=raw['branches']['P0'];route=list(map(tuple,raw['route']));trace=n['trace'];m=both(c,route);assert n['route']==raw['route'] and n['trace']==raw['trace']
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']));old=set(map(tuple,c['initial_targets']));new=set(map(tuple,c['published_targets']))-old;assert not old&new and not new&h and t==old|new
    assert f=={(a,b) for a in range(min(p[0] for p in f),max(p[0] for p in f)+1) for b in range(min(p[1] for p in f),max(p[1] for p in f)+1)},'Manhattan audit requires full rectangle'
    log=n['diagnostic']['log'];exception_budget(log);assert len(log)<=1 and n['diagnostic']['trigger_count']==len(log) and n['diagnostic']['intervention_used']==bool(log) and n['diagnostic']['mode']==out['job']['mode']
    if out['job']['mode']=='OFF':assert not log
    if expected_trigger is not None:assert len(log)==expected_trigger,('unexpected_trigger_count',out['job']['id'],len(log),expected_trigger)
    forced=log[0] if log else None;pred=tuple(c['predator']);rows=[];exceptions=0;first_competition=None
    for i,e in enumerate(trace):
        idx=e['index'];end=trace[i+1]['index'] if i+1<len(trace) else len(route)-1;cur=route[idx];prev=route[idx-1] if idx else tuple(c['previous']) if c['previous'] is not None else None;pending=t-h-set(route[:idx+1]);op=old&pending;np=new&pending
        assert e['current']==list(cur) and e['pending_count']==len(pending)
        legal=sorted(q for q in adjacent(cur) if q in pending and q in f)
        if e['kind']=='local':
            assert e['previous']==(list(prev) if prev is not None else None) and legal and end==idx+1 and e['goal']==list(route[idx+1])
            distances={q:math.hypot(q[0]-pred[0],q[1]-pred[1]) for q in legal};low=min(distances.values());high=max(distances.values());expected=[]
            for q in legal:
                distance=(distances[q]-low)/(high-low) if high>low else 0.
                straight=0. if prev is None else ((cur[0]-prev[0])*(q[0]-cur[0])+(cur[1]-prev[1])*(q[1]-cur[1])+1)/2
                boundary=(4-len(set(adjacent(q))&pending&f))/4;expected.append(dict(cell=list(q),distance_reward=distance,straight_reward=straight,boundary_reward=boundary,score=distance+2.*straight+.5*boundary))
            assert expected==e['options'],('independent_reward_mismatch',out['job']['id'],i)
            original=min(expected,key=lambda z:(-z['score'],tuple(z['cell'])))['cell'];oldopts=[z for z in expected if tuple(z['cell']) in old];newopts=[z for z in expected if tuple(z['cell']) in new]
            if oldopts and newopts and first_competition is None:first_competition=idx
            if forced is not None and forced['index']==idx:
                exceptions+=1;assert oldopts and len(newopts)==1 and idx==first_competition and tuple(original) in old
                assert forced['original_selected']==original and forced['forced_selected']==newopts[0]['cell']==e['goal']
                assert forced['options']==e['options'] and forced['old_options']==oldopts and forced['new_options']==newopts
                assert forced['current']==list(cur) and forced['previous']==list(prev) and forced['pending_count']==len(pending) and forced['old_pending_count']==len(op) and forced['new_pending_count']==len(np)
                assert forced['before_pending']==norm(sorted(pending)) and forced['after_pending']==norm(sorted(pending-{tuple(e['goal'])})) and forced['after_current']==e['goal'] and forced['after_previous']==list(cur)
                assert forced['resource_before']==c['distance_budget']-idx and forced['resource_after']==c['distance_budget']-idx-1 and forced['reason']=='first_local_both_classes_unique_new_one_step'
            else:assert e['goal']==original,('unauthorized_selection_exception',out['job']['id'],i)
        elif e['kind']=='recovery':
            assert e['previous']==(list(prev) if prev is not None else None) and not legal and pending
            goal=min(pending,key=lambda q:(abs(cur[0]-q[0])+abs(cur[1]-q[1]),q));assert e['goal']==list(goal) and route[end]==goal and end-idx==abs(cur[0]-goal[0])+abs(cur[1]-goal[1])
        elif e['kind']=='return':assert not pending and e['goal']==c['base'] and route[end]==tuple(c['base']) and end-idx==abs(cur[0]-c['base'][0])+abs(cur[1]-c['base'][1])
        else:raise AssertionError(('unknown_saved_decision_kind',e['kind']))
        rows.append(dict(trace_index=i,route_index=idx,end_index=end,kind=e['kind'],pending=len(pending),old_pending=len(op),new_pending=len(np),selection_exception=bool(forced and forced['index']==idx),passed=True))
    assert exceptions==len(log);return norm(dict(metrics=m,trigger_count=exceptions,first_competition_index=first_competition,intervention_log=log,decisions=rows,external_BFS=0,external_Dijkstra=0,independent_rectangle_Manhattan_audit=True))
def paired_audit(c,off,on):
    nn=on['result']['raw']['branches']['P0'];logs=nn['diagnostic']['log'];aa=off['result']['raw']['route'];bb=on['result']['raw']['route']
    if not logs:
        assert aa==bb and off['result']['raw']['trace']==on['result']['raw']['trace'];assert both(c,aa)==both(c,bb)
        return dict(protection_equal=True,triggered=False)
    k=logs[0]['index'];assert aa[:k+1]==bb[:k+1]
    t=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));assert t-set(map(tuple,aa[:k+1]))==t-set(map(tuple,bb[:k+1]))
    e0=next(e for e in off['result']['raw']['trace'] if e['index']==k);e1=next(e for e in on['result']['raw']['trace'] if e['index']==k);assert {q:v for q,v in e0.items() if q!='goal'}=={q:v for q,v in e1.items() if q!='goal'} and e0['goal']==logs[0]['original_selected'] and e1['goal']==logs[0]['forced_selected']
    lookup=collections.defaultdict(list)
    for i,p in enumerate(aa):
        prev=tuple(aa[i-1]) if i else tuple(c['previous']);lookup[(tuple(p),prev,frozenset(t-set(map(tuple,aa[:i+1]))))].append(i)
    first=None
    for j in range(k+1,len(bb)):
        state=(tuple(bb[j]),tuple(bb[j-1]),frozenset(t-set(map(tuple,bb[:j+1]))))
        if state in lookup:
            i=lookup[state][0];first=dict(OFF_index=i,ON_index=j,current=state[0],previous=state[1],pending=sorted(state[2]),OFF_remaining_resource=c['distance_budget']-i,ON_remaining_resource=c['distance_budget']-j,same_resource=i==j,same_literal_suffix=aa[i:]==bb[j:],note='current/previous/pending match; resource explicitly separate; timing/cache not claimed identical');break
    return norm(dict(triggered=True,pre_intervention_prefix_equal=True,pre_intervention_decision_equal_except_goal=True,one_step_credit_passed=True,first_task_geometry_state_rejoin=first))
def job_row(j):
    p=H/'outputs'/f'{j["id"]}.json'
    if not p.exists():
        receipt_file=H/'logs'/f'{j["id"]}.receipt.json';q=read(receipt_file) if receipt_file.exists() else None
        return dict(job=j,ran=bool(q),valid=False,timely=False,metrics=None,status=q['status'] if q else 'NOT_RUN',seconds=None)
    out=read(p);assert out['job']==j and out['input_sha256']==sha(H/j['input']);c=read(H/j['input']);x=out['result'];route=x['raw'].get('route',[])
    if not route:
        assert x['raw']['status'] in ('deadline','planning_failure','environment_infeasible'),'non-native or invalid-route technical failure'
        return dict(job=j,ran=True,valid=False,timely=False,metrics=None,status=x['raw']['status'],seconds=x['entry_seconds'],native_failure=True)
    st=next(s for s in read(H/'states_metadata.json') if s['id']==j['state']);expected=1 if j['mode']=='ON' and st['condition'] in ('MIXED_SIDE','U_SIDE') else 0
    z=saved_audit(c,out,expected);m=z['metrics'];assert len(out['actual_core_calls'])==1 and set(out['runtime_reads'])=={str(H/j['input'])}
    eq=None
    if j['mode']=='OFF':
        original=read(B/'outputs'/f'formal_{j["state"]}_{j["seed"]}_PPCPP.json');eq=equivalent(out,original);oldmetrics=both(c,original['result']['raw']['route']);assert m==oldmetrics
    return dict(job=j,ran=True,valid=True,timely=x['entry_seconds']<20,metrics=m,status=x['raw']['status'],seconds=x['entry_seconds'],caller_wall_seconds=out['caller_wall_seconds'],audit=z,equivalence=eq)
