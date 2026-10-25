"""Frozen-input four-neighbor PPCPP adaptation; core only, no external candidates."""
import sys,time,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'基线复现准备_20261019'))
from ppcpp_independent import UnifiedGeometry,single_cell_audit,check_contract,DeadlineExceeded,NoPath
from h1_direction import parse_heading,after_edge
from h1_rewards import reward_options,choose_neighbor
VERSION='PPCPP_REAL_HEADING_H1_v0.1_20261022'
def solve(s,initial,budget,seed,predator,heading_request,*,_clock=time.perf_counter,_geometry=UnifiedGeometry,_audit=single_cell_audit):
    begin=_clock();deadline=begin+budget;route=[];trace=[];status='not_started';reason=None;accepted=None;heading_state=None
    def tick():
        if _clock()>=deadline:raise DeadlineExceeded()
    def move(segment,pending):
        nonlocal heading_state
        assert segment[0]==route[-1]
        for p in segment[1:]:
            tick();prior=route[-1];route.append(p);pending.discard(p)
            heading_state=after_edge(heading_state,prior,p,len(route)-1)
    try:
        check_contract(s,initial,budget)
        if not math.isfinite(budget):raise ValueError('finite budget')
        if len(predator)!=2 or not all(math.isfinite(v) for v in predator):raise ValueError('finite predator')
        if s.free and not (predator[0]<min(x for x,y in s.free) or predator[0]>max(x for x,y in s.free)):raise ValueError('predator outside fixed flight-domain x bounds required')
        heading_state=parse_heading(heading_request,s.current)
        tick();g=_geometry(s,deadline);reason=g.precheck();tick()
        if reason:status='environment_infeasible'
        else:
            pending=set(s.targets)-set(s.covered)-{s.current};route=[s.current]
            while pending:
                tick();cur=route[-1]
                options=reward_options(cur,heading_state,pending,s.free,predator,(2.,.5));tick()
                event=dict(index=len(route)-1,current=cur,incoming_heading=heading_state,pending_count=len(pending))
                if options:
                    goal=choose_neighbor(options);event.update(kind='local',options=options,goal=goal);segment=(cur,goal)
                else:
                    goal=min(pending,key=lambda q:(g.distance(cur,q),q));tick();segment=g.path(cur,goal)
                    event.update(kind='recovery',goal=goal)
                trace.append(event);move(segment,pending)
            tick();trace.append(dict(kind='return',index=len(route)-1,current=route[-1],goal=s.base,pending_count=0,incoming_heading=heading_state))
            move(g.path(route[-1],s.base),pending);tick()
            checked=_audit(s,tuple(route));tick()
            if checked['valid']:accepted=_clock()-begin;tick();status='core_complete'
            else:status='core_invalid';reason=checked['errors']
    except DeadlineExceeded:status='deadline'
    except NoPath as e:status='planning_failure';reason=str(e)
    seconds=_clock()-begin
    return dict(version=VERSION,method='PPCPP_INDEPENDENT',route=tuple(route) if status=='core_complete' else (),status=status,reason=reason,
        seconds=seconds,budget=budget,seed=seed,seed_used=False,predator=predator,initial_heading=heading_request,weights=(2.,.5),
        trace=trace,final_heading=heading_state,accepted_seconds=accepted if status=='core_complete' else None,fallback_selected=False,
        overrun_gt_10ms=seconds>budget+.01)
