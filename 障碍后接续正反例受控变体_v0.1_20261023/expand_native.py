"""Frozen-input four-neighbor PPCPP adaptation; core only, no external candidates."""
import sys,time,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'基线复现准备_20261019'))
from ppcpp_independent import core,UnifiedGeometry,single_cell_audit,check_contract,DeadlineExceeded,NoPath
VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'
def solve(s,initial,budget,seed,predator,previous,*,_clock=time.perf_counter,_geometry=UnifiedGeometry,_audit=single_cell_audit,_diag=None):
    begin=_clock();deadline=begin+budget;route=[];trace=[];status='not_started';reason=None;accepted=None
    def tick():
        if _clock()>=deadline:raise DeadlineExceeded()
    def move(segment,pending):
        assert segment[0]==route[-1]
        for p in segment[1:]:tick();route.append(p);pending.discard(p)
    try:
        check_contract(s,initial,budget)
        if not math.isfinite(budget):raise ValueError('finite budget')
        if len(predator)!=2 or not all(math.isfinite(v) for v in predator):raise ValueError('finite predator')
        if s.free and not (predator[0]<min(x for x,y in s.free) or predator[0]>max(x for x,y in s.free)):raise ValueError('predator outside fixed flight-domain x bounds required')
        if previous is not None and sum(abs(a-b) for a,b in zip(previous,s.current))!=1:raise ValueError('historical heading must be adjacent')
        tick();g=_geometry(s,deadline);reason=g.precheck();tick()
        if reason:status='environment_infeasible'
        else:
            pending=set(s.targets)-set(s.covered)-{s.current};route=[s.current]
            while pending:
                tick();cur=route[-1];prev=route[-2] if len(route)>1 else previous
                options=core.reward_options(cur,prev,pending,s.free,predator,(2.,.5));tick()
                event=dict(index=len(route)-1,current=cur,previous=prev,pending_count=len(pending))
                if options:
                    goal=core.choose_neighbor(options);event.update(kind='local',options=options,goal=goal);segment=(cur,goal)
                else:
                    goal=min(pending,key=lambda q:(g.distance(cur,q),q));tick()
                    if _diag is not None:goal=_diag.choose(trace,route,cur,prev,pending,goal,g);tick()
                    segment=g.path(cur,goal)
                    event.update(kind='recovery',goal=goal)
                if _diag is not None:_diag.record(trace,event,pending,route,segment);tick()
                trace.append(event);move(segment,pending)
            tick();trace.append(dict(kind='return',index=len(route)-1,current=route[-1],goal=s.base,pending_count=0))
            move(g.path(route[-1],s.base),pending);tick()
            checked=_audit(s,tuple(route));tick()
            if checked['valid']:accepted=_clock()-begin;tick();status='core_complete'
            else:status='core_invalid';reason=checked['errors']
    except DeadlineExceeded:status='deadline'
    except NoPath as e:status='planning_failure';reason=str(e)
    seconds=_clock()-begin
    return dict(version=VERSION,method='PPCPP_INDEPENDENT',route=tuple(route) if status=='core_complete' else (),status=status,reason=reason,
        seconds=seconds,budget=budget,seed=seed,seed_used=False,predator=predator,initial_previous=previous,weights=(2.,.5),
        trace=trace,accepted_seconds=accepted if status=='core_complete' else None,fallback_selected=False,
        overrun_gt_10ms=seconds>budget+.01)
