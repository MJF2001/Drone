"""Exactly one branching point, at the SECOND native recovery; no nested rollout."""
import sys,time,math,copy
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'基线复现准备_20261019/独立版_v0.2'));import ppcpp as native
core=native.core

def solve(s,initial,budget,seed,predator,previous,*,mode='three',_clock=time.perf_counter,_hook=None):
    if mode not in ('one','three'):raise ValueError('mode')
    begin=_clock();deadline=begin+budget;route=[];events=[];branches=[];branch_state=None;chosen=None;status='not_started';reason=None
    def tick(stage):
        if _hook:_hook(stage)
        if _clock()>=deadline:raise native.DeadlineExceeded()
    def move(path,goals,pending):
        for point in goals:
            tick('move');path.append(point);pending.discard(point)
    def finish(path,tr,pending,first_goal):
        first=True;forced=first_goal
        while pending:
            tick('branch_decision');cur=path[-1];prev=path[-2] if len(path)>1 else previous
            options=core.reward_options(cur,prev,pending,s.free,predator,(2.,.5));tick('branch_options')
            e=dict(index=len(path)-1,current=cur,previous=prev,pending_count=len(pending))
            if options:
                goal=core.choose_neighbor(options);e.update(kind='local',options=options,goal=goal);segment=(cur,goal)
            else:
                if first and forced is not None:goal=forced
                else:goal=min(pending,key=lambda q:(g.distance(cur,q),q))
                e.update(kind='recovery',goal=goal);segment=g.path(cur,goal)
            first=False;tr.append(e);move(path,segment[1:],pending)
        tick('return');tr.append(dict(kind='return',index=len(path)-1,current=path[-1],goal=s.base,pending_count=0))
        move(path,g.path(path[-1],s.base)[1:],pending);tick('branch_audit')
        ck=native.single_cell_audit(s,tuple(path));tick('branch_audited');accepted=_clock()-begin
        return dict(status='core_complete' if ck['valid'] else 'core_invalid',route=path if ck['valid'] else [],diagnostic_route=path,trace=tr,
            reason=ck['errors'],accepted_seconds=accepted,budget=budget,predator=predator,initial_previous=previous,weights=(2.,.5),fallback_selected=False,forced_goal=first_goal,override_recovery=2)
    try:
        native.check_contract(s,initial,budget)
        if not math.isfinite(budget):raise ValueError('budget')
        if len(predator)!=2 or not all(math.isfinite(v) for v in predator):raise ValueError('predator')
        if s.free and not (predator[0]<min(x for x,y in s.free) or predator[0]>max(x for x,y in s.free)):raise ValueError('predator bounds')
        if previous is not None and sum(abs(a-b) for a,b in zip(previous,s.current))!=1:raise ValueError('previous')
        tick('input');g=native.UnifiedGeometry(s,deadline);reason=g.precheck();tick('geometry')
        if reason:status='environment_infeasible'
        else:
            pending=set(s.targets)-set(s.covered)-{s.current};route=[s.current];recovery_count=0
            while pending:
                tick('prefix');cur=route[-1];prev=route[-2] if len(route)>1 else previous
                options=core.reward_options(cur,prev,pending,s.free,predator,(2.,.5));tick('prefix_options')
                e=dict(index=len(route)-1,current=cur,previous=prev,pending_count=len(pending))
                if options:
                    goal=core.choose_neighbor(options);e.update(kind='local',options=options,goal=goal);segment=(cur,goal)
                else:
                    recovery_count+=1
                    if recovery_count==2:break
                    tick('ordinary_recovery');goal=min(pending,key=lambda q:(g.distance(cur,q),q));tick('ordinary_ready')
                    e.update(kind='recovery',goal=goal);segment=g.path(cur,goal)
                events.append(e);move(route,segment[1:],pending)
            if not pending:
                branches.append(finish(list(route),copy.deepcopy(events),set(),None));chosen=0
            else:
                tick('second_recovery');nearest=min(pending,key=lambda q:(g.distance(route[-1],q),q));tick('nearest_ready')
                branch_state=dict(path=list(route),pending=sorted(pending),previous=route[-2] if len(route)>1 else previous,nearest=nearest,recovery_index=2)
                goals=[nearest]
                branches.append(finish(list(route),copy.deepcopy(events),set(pending),nearest));tick('baseline_ready')
                if mode=='three' and branches[0]['status']=='core_complete':
                    tick('candidate_generation');near=min(pending,key=lambda q:(g.distance(s.base,q),q));far=min(pending,key=lambda q:(-g.distance(s.base,q),q))
                    for goal in (near,far):
                        if goal not in goals:goals.append(goal)
                    tick('candidates_ready')
                    for goal in goals[1:]:
                        tick('alternative_start');branches.append(finish(list(route),copy.deepcopy(events),set(pending),goal));tick('alternative_done')
                valid=[i for i,b in enumerate(branches) if b['status']=='core_complete']
                if valid:chosen=min(valid,key=lambda i:(len(branches[i]['route']),i))
            status='core_complete' if chosen is not None and branches[chosen]['status']=='core_complete' else 'core_invalid'
    except native.DeadlineExceeded:status='deadline'
    except native.NoPath as exc:status='planning_failure';reason=str(exc)
    try:tick('result_ready')
    except native.DeadlineExceeded:status='deadline'
    elapsed=_clock()-begin
    if elapsed>=budget:status='deadline'
    selected=branches[chosen] if chosen is not None else None
    return dict(version='PPCPP_SECOND_RECOVERY_ROLLOUT_v0.1',override_recovery=2,mode=mode,status=status,seconds=elapsed,reason=reason,
        route=selected['route'] if status=='core_complete' else [],trace=selected['trace'] if selected else [],
        branches=branches,selected_branch=chosen,branch_state=branch_state,diagnostic_prefix=route,
        budget=budget,seed=seed,predator=predator,initial_previous=previous,weights=(2.,.5),fallback_selected=False)
