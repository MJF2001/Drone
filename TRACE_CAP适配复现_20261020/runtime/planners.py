"""Independent paper-guided public-map restart adaptations, not author code.
Unknown-sensing controllers are NOT simulated by concealing published cells.
"""
import time,math
from primitives import Metric,Deadline,Unreachable,tour
from structures import TraceTree,CapGraph,cap_greedy
def solve(c,method,budget=20,seed=0,*,clock=time.perf_counter,checkpoint_hook=None):
    begin=clock();deadline=begin+budget
    if method not in ('TRACE','CAP'):raise ValueError('method')
    if not math.isfinite(budget) or budget<=0:raise ValueError('time budget')
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']));current=tuple(c['current']);base=tuple(c['base'])
    published=set(map(tuple,c.get('published_targets',list(t|h))));deferred=published-f-h
    if current not in f or base not in f or not t<=f:raise ValueError('active geometry')
    if not h<=published or not t<=published or (published&f)-h-t:raise ValueError('published task ledger')
    if 'deferred_targets' in c and set(map(tuple,c['deferred_targets']))!=deferred:raise ValueError('deferred ledger')
    if c['distance_budget']<0:raise ValueError('resource')
    pending=t-h-{current};path=[current];moves=[];plans=[];states={p:'Fc' if p in h or p==current else 'Fu' for p in t}
    structure=None;metric=None;status='incomplete';error=None;changes=set()
    def check(stage):
        if checkpoint_hook:checkpoint_hook(stage)
        if clock()>=deadline:raise Deadline(stage)
    def execute(waypoints,mode):
        nonlocal current
        for destination in waypoints:
            check('execute');start=len(path)-1;credit=set();completed=False
            try:
                cells=metric.path(current,destination)
                for v in cells[1:]:
                    check('move_before');path.append(v);current=v
                    if v in pending:pending.remove(v);credit.add(v);changes.add(v);states[v]='Fc'
                    check('move_after')
                completed=True
            finally:moves.append(dict(mode=mode,start_index=start,end_index=len(path)-1,credited=sorted(credit),pending_after=sorted(pending),interrupted=not completed,destination=destination))
    try:
        check('input_ready');metric=Metric(f,check)
        structure=TraceTree(t,states,metric,current) if method=='TRACE' else CapGraph(pending,metric,current)
        while pending:
            check('region_select')
            if not structure.order:status='missing_task_region';break
            i=structure.order[0];node=structure.nodes[i];region=node['R']&pending
            if not region:status='stale_region';break
            snapshot=structure.snapshot();next_id=structure.order[1] if len(structure.order)>1 else None
            if method=='TRACE':
                end=structure.nodes[next_id]['center'] if next_id is not None else None
                end_source='next_region_virtual_center' if end is not None else 'free_end'
            else:
                end=cap_greedy(current,region);end_source='restart_direction_target'
                if end is None:
                    candidates=sorted(region);ds=metric.matrix([current]+candidates)[0]
                    end=candidates[min(range(len(candidates)),key=lambda k:(ds[k+1],candidates[k]))];end_source='restart_nearest_entry_target'
            order,info=tour(sorted(region),current,lambda p:p,metric,end)
            executed_order=order[:-1] if method=='TRACE' and end is not None else order
            plan=dict(region_id=i,structure_before=snapshot,required=sorted(region),start=current,next_id=next_id,end=end,end_source=end_source,order=order,executed_order=executed_order,tsp=info,path_start=len(path)-1,completed=False)
            plans.append(plan);changes.clear()
            execute(executed_order[1:],'region')
            assert not (region&pending),'local TSP omitted its required targets'
            if method=='TRACE':
                for p in changes:structure.states[p]='Fc'
                structure.update(changes,current)
            else:structure.sync(pending,current)
            plan.update(completed=True,path_end=len(path)-1,structure_after=structure.snapshot())
        else:status='coverage_complete'
        if status=='coverage_complete':
            check('return');execute([base],'return');check('final_audit')
            if len(path)-1>c['distance_budget']:status='resource_exceeded'
            elif not t<=h|set(path):status='coverage_incomplete'
            else:status='complete'
    except Deadline as exc:status='deadline';error=str(exc)
    except Unreachable as exc:status='unreachable';error=str(exc)
    result=dict(method=method,status=status,route=list(path) if status=='complete' else [],diagnostic_route=path,pending=sorted(pending),deferred=sorted(deferred),moves=moves,plans=plans,
                structure=structure.snapshot() if structure else None,structure_events=structure.events if structure else [],error=error,
                metric_counts=dict(distance_rows=metric.rows,path_builds=metric.path_builds) if metric else {},seed=seed,seed_used_for_ties=False,global_completion=False,
                scope='Public-map restart adaptation. Exploring helpers are mechanism-tested, not a native online-sensing controller.')
    check_ready=False
    try:check('result_ready');check_ready=True
    except Deadline as exc:
        if status=='complete':result.update(status='deadline',route=[],error=str(exc))
    end_time=clock();result['seconds']=end_time-begin
    if end_time>=deadline and result['status']=='complete':result.update(status='deadline',route=[],error='result_ready')
    return result
