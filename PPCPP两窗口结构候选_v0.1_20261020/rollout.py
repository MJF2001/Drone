"""Pay for structure and candidate distances BEFORE branching, in at most two windows."""
import sys,time,math,copy
from pathlib import Path
from collections import deque
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'基线复现准备_20261019/独立版_v0.2'));import ppcpp as native
core=native.core

def labels(pending,tick):
    tick('component_start');lab={};sizes=[];anchors=[]
    for root in sorted(pending):
        tick('component_root')
        if root in lab:continue
        k=len(sizes);lab[root]=k;q=deque([root]);n=0;anchors.append(root)
        while q:
            tick('component_visit');x,y=q.popleft();n+=1
            for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if z in pending and z not in lab:lab[z]=k;q.append(z)
        sizes.append(n)
    tick('component_done');return lab,sizes,anchors

def solve(s,initial,budget,seed,predator,previous,*,mode='three',_clock=time.perf_counter,_hook=None):
    if mode not in ('one','three'):raise ValueError('mode')
    begin=_clock();deadline=begin+budget;route=[];events=[];branches=[];windows=[];branch_state=None;chosen=None;status='not_started';reason=None;override=None
    def tick(stage):
        if _hook:_hook(stage)
        if _clock()>=deadline:raise native.DeadlineExceeded()
    def move(path,goals,pending):
        for point in goals:tick('move');path.append(point);pending.discard(point)
    def finish(path,tr,pending,first_goal):
        first=True
        while pending:
            tick('branch_decision');cur=path[-1];prev=path[-2] if len(path)>1 else previous
            options=core.reward_options(cur,prev,pending,s.free,predator,(2.,.5));tick('branch_options')
            e=dict(index=len(path)-1,current=cur,previous=prev,pending_count=len(pending))
            if options:
                goal=core.choose_neighbor(options);e.update(kind='local',options=options,goal=goal);segment=(cur,goal)
            else:
                goal=first_goal if first and first_goal is not None else min(pending,key=lambda q:(g.distance(cur,q),q))
                e.update(kind='recovery',goal=goal);segment=g.path(cur,goal)
            first=False;tr.append(e);move(path,segment[1:],pending)
        tick('return');tr.append(dict(kind='return',index=len(path)-1,current=path[-1],goal=s.base,pending_count=0))
        move(path,g.path(path[-1],s.base)[1:],pending);tick('branch_audit');ck=native.single_cell_audit(s,tuple(path));tick('branch_audited');accepted=_clock()-begin
        return dict(status='core_complete' if ck['valid'] else 'core_invalid',route=path if ck['valid'] else [],diagnostic_route=path,trace=tr,reason=ck['errors'],accepted_seconds=accepted,budget=budget,predator=predator,initial_previous=previous,weights=(2.,.5),fallback_selected=False,forced_goal=first_goal,override_recovery=override)
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
                options=core.reward_options(cur,prev,pending,s.free,predator,(2.,.5));tick('prefix_options');e=dict(index=len(route)-1,current=cur,previous=prev,pending_count=len(pending))
                if options:
                    goal=core.choose_neighbor(options);e.update(kind='local',options=options,goal=goal);segment=(cur,goal)
                else:
                    recovery_count+=1;tick('ordinary_recovery');nearest=min(pending,key=lambda q:(g.distance(cur,q),q));tick('nearest_ready')
                    if recovery_count<=2:
                        w=recovery_count
                        def wt(stage):tick(f'w{w}_{stage}')
                        wt('candidate_generation');near=min(pending,key=lambda q:(g.distance(s.base,q),q));far=min(pending,key=lambda q:(-g.distance(s.base,q),q));goals=[]
                        for q in (nearest,near,far):
                            if q not in goals:goals.append(q)
                        wt('candidates_ready');lab,sizes,anchors=labels(pending,wt);ids=[lab[q] for q in goals];eligible=len(set(ids))>=2
                        windows.append(dict(recovery_index=w,index=len(route)-1,current=cur,pending_count=len(pending),goals=goals,component_count=len(sizes),component_sizes=sizes,component_anchors=anchors,candidate_component_ids=ids,eligible=eligible));wt('window_ready')
                        if eligible:override=w;break
                    goal=nearest;e.update(kind='recovery',goal=goal);segment=g.path(cur,goal)
                events.append(e);move(route,segment[1:],pending)
            if override is None:
                assert not pending;branches.append(finish(list(route),copy.deepcopy(events),set(),None));chosen=0
            else:
                tick('trigger_ready');branch_state=dict(path=list(route),pending=sorted(pending),previous=route[-2] if len(route)>1 else previous,nearest=goals[0],recovery_index=override,goals=goals)
                branches.append(finish(list(route),copy.deepcopy(events),set(pending),goals[0]));tick('baseline_ready')
                if mode=='three' and branches[0]['status']=='core_complete':
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
    return dict(version='PPCPP_TWO_WINDOW_STRUCTURE_v0.1',mode=mode,status=status,seconds=elapsed,reason=reason,route=selected['route'] if status=='core_complete' else [],trace=selected['trace'] if selected else [],branches=branches,selected_branch=chosen,branch_state=branch_state,structural_windows=windows,override_recovery=override,diagnostic_prefix=route,budget=budget,seed=seed,predator=predator,initial_previous=previous,weights=(2.,.5),fallback_selected=False)
