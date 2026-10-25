"""Explicit KNOWN-MAP RESTART candidate, not author-code equivalence.

Policy KR1: global L/U/D/R pending neighbour, else nearest global pending.
Choose once before a region tour and retain through every connector. Region
selection remains CAP graph order, independent of target choice. No unknown
controller, candidate endpoint search, suffix fallback, or global completion.
"""
import time, math
from primitives import Metric, Deadline, Unreachable, tour, neighbours
from known_sync import KnownMapCapGraph

class ResourceLimit(Exception): pass

def solve(c,budget=20,*,clock=time.perf_counter,hook=None):
    if not math.isfinite(budget) or budget<=0:raise ValueError('budget')
    begin=clock();deadline=begin+budget
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']))
    current=tuple(c['current']);base=tuple(c['base']);published=set(map(tuple,c.get('published_targets',list(t|h))))
    limit=c.get('distance_budget',float('inf'))
    if current not in f or base not in f or not t<=f or not h<=published or not t<=published or (published&f)-h-t:raise ValueError('snapshot')
    if math.isnan(limit) or limit<0:raise ValueError('distance budget')
    deferred=published-f-h
    if 'deferred_targets' in c and set(map(tuple,c['deferred_targets']))!=deferred:raise ValueError('deferred')
    path=[current];pending=t-h-{current};events=[];plans=[];graph=None;state=None;generation=0;metric=None
    status='not_started';error=None
    resume=c.get('cap_resume_target')
    if resume is not None and (not isinstance(resume,dict) or tuple(resume.get('point',())) not in f or not isinstance(resume.get('reference'),str) or not resume['reference']):raise ValueError('resume target')
    def check(stage):
        if hook:hook(stage)
        if clock()>=deadline:raise Deadline(stage)
    def execute(goals,mode):
        nonlocal current
        for goal in goals:
            for point in metric.path(current,goal)[1:]:
                check('move_before')
                if len(path)-1>=limit:raise ResourceLimit('move budget')
                old=current;credit=[point] if point in pending else []
                current=point;path.append(point);pending.discard(point)
                events.append(dict(type='move',mode=mode,start=old,end=point,credited=credit,
                    generation=state['generation'] if state else None))
                check('move_after')
    try:
        check('input_ready');metric=Metric(f,check);graph=KnownMapCapGraph(pending,metric,current)
        while pending:
            check('region_select')
            if not graph.order:raise ValueError('missing region')
            region_id=graph.order[0];required=set(graph.nodes[region_id]['R'])
            assert required and required<=pending
            # A global target is not constrained to this region or its pending cells.
            check('target_select')
            if generation==0 and resume is not None:
                endpoint=tuple(resume['point']);source='provided_resume';reference=resume['reference']
            else:
                endpoint=next((p for p in neighbours(current) if p in pending),None)
                source='KR1_global_direction'
                if endpoint is None:
                    candidates=sorted(pending);ds=metric.distances_from(current,candidates)
                    endpoint=candidates[min(range(len(candidates)),key=lambda i:(ds[i],candidates[i]))]
                    source='KR1_global_nearest'
                reference='KR1_restart' if generation==0 else 'KR1_explicit_next_region'
            check('target_bind');generation+=1
            state=dict(point=endpoint,source=source,reference=reference,generation=generation,phase='bound')
            events.append(dict(type='bind',state=dict(state),pending=sorted(pending),current=current,region_id=region_id))
            order,info=tour(sorted(required),current,lambda p:p,metric,endpoint)
            plan=dict(region_id=region_id,required=sorted(required),start=current,end=endpoint,
                target_state=dict(state),order=order,tsp=info,path_start=len(path)-1,completed=False,structure_before=graph.snapshot())
            plans.append(plan);check('local_plan_ready')
            # First connector is the declared entry; do not rebind tau upon arrival
            # or upon passing/crediting tau early on this actual path.
            execute(order[1:],'region')
            assert not required&pending and current==endpoint
            state['phase']='reached';plan.update(completed=True,path_end=len(path)-1)
            events.append(dict(type='target_reached',generation=generation,point=current,path_index=len(path)-1))
            check('region_complete');before=graph.snapshot();event_start=len(graph.events)
            graph.sync(pending,current)
            plan.update(structure_after=graph.snapshot(),sync_events=graph.events[event_start:])
            check('sync_complete')
        check('return_start');execute([base],'return');check('return_complete')
        assert current==base and not pending
        status='complete'
    except Deadline as exc:status='deadline';error=str(exc)
    except ResourceLimit as exc:status='resource_exceeded';error=str(exc)
    except Unreachable as exc:status='unreachable';error=str(exc)
    try:check('result_ready')
    except Deadline as exc:status='deadline';error=str(exc)
    elapsed=clock()-begin
    if elapsed>=budget:status='deadline';error=error or 'serialization_boundary'
    return dict(version='CAP_KNOWN_RESTART_KR1_CANDIDATE_v0.1',status=status,error=error,seconds=elapsed,
        route=list(path) if status=='complete' else [],diagnostic_route=path,pending=sorted(pending),deferred=sorted(deferred),
        target_state=state,events=events,plans=plans,structure=graph.snapshot() if graph else None,
        structure_events=graph.events if graph else [],distance=len(path)-1,benchmark_eligible=False,
        global_completion_fallback=False,scope='Explicit KR1 restart adaptation; not author equivalence or frozen baseline')
