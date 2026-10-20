"""Two initial repairs retained under one deadline; optional unmodified PLUS1 continuation."""
import time
from model import Snapshot,DeadlineExceeded,NoPath
from baseline_suite import check_contract
from unified_geometry import UnifiedGeometry,single_cell_audit
from road_range_candidate_20261015 import range_plan,tick,digest
from fixed_scope_candidate import responsibilities,outside_segments,solve as fixed_solve

def repair_visits(s):
    left=set(s.targets-s.covered);visits=[]
    for p in s.old_route:
        if p in left and p in s.free:visits.append(p);left.remove(p)
    visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
    return visits

def solve(s,initial,method,budget,seed):
    t0=time.perf_counter();deadline=t0+budget;best=None;best_event=None;events=[];acceptances=[];stages=[]
    plan=None;init_records=[];phase='public';active_cfg=None;continuation=None
    def register(event,source):
        nonlocal best,best_event
        e=dict(event);e['candidate_id']=len(events);e['source']=source
        e['accepted']=False;e['completed']=True
        now=time.perf_counter();e['decision_public_elapsed']=now-t0
        e['late_rejected']=now>deadline
        events.append(e)
        if e['valid'] and now<=deadline and (best is None or len(e['route'])<len(best)):
            best=tuple(e['route']);e['accepted']=True;e['accepted_public_elapsed']=now-t0;best_event=e
            acceptances.append(dict(public_seconds=now-t0,seconds=now-t0,steps=len(best)-1,
                                    source=source,source_scope=e.get('source_scope'),candidate_id=e['candidate_id'],route_sha256=e['route_sha256']))
        return e
    def offer(route,label,patch=None):
        tick(deadline);route=tuple(route);valid=bool(route) and single_cell_audit(s,route)['valid'];checked=time.perf_counter()
        event=dict(label=label,source_scope=active_cfg['scope'] if patch is not None else None,
                   route=route,patch=tuple(patch) if patch is not None else None,
                   cfg=active_cfg['cfg'] if patch is not None else None,valid=bool(valid),
                   validation_complete_public_elapsed=checked-t0,public_elapsed=checked-t0,
                   before_deadline=checked<=deadline,steps=len(route)-1,route_sha256=digest(route))
        register(event,phase+':'+label);tick(deadline);return valid
    def stage(name,fn):
        start=time.perf_counter();record=dict(stage=name,start_public_elapsed=start-t0,status='running');stages.append(record)
        try:value=fn();record['status']='completed';return value
        except DeadlineExceeded:record['status']='deadline';raise
        except (NoPath,ValueError) as exc:record['status']='construction_failure';record['reason']=str(exc);return None
        finally:record['end_public_elapsed']=time.perf_counter()-t0
    status='finished';construct_best=None;continuation_entry=None;continuation_available=0
    try:
        check_contract(s,initial,budget)
        if method not in ('POOL_INIT','POOL_PLUS1'):raise ValueError('unknown pool method')
        g=UnifiedGeometry(s,deadline)
        if g.precheck():raise ValueError('infeasible environment')
        def public_fallback():
            offer(s.old_route,'old_suffix');offer(g.expand(repair_visits(s)),'common_fallback')
        stage('public_fallback',public_fallback)
        plan=stage('shared_range_plan',lambda:range_plan(s,initial,deadline))
        if plan is None:raise ValueError('range plan unavailable')
        for scope in ('R_PLUS1','R_SEED'):
            phase='construct_'+scope;cfg=plan['plans'][scope];active_cfg=dict(scope=scope,cfg=cfg)
            record=dict(scope=scope,cfg=cfg,start_public_elapsed=time.perf_counter()-t0,candidate_ids=[],status='running');init_records.append(record)
            before=len(events)
            def initial_repair():
                assigned=responsibilities(s,cfg,deadline);pre,post=outside_segments(s,cfg,assigned,g,'LITERAL',deadline)
                record['responsibilities']=assigned;record['prefix']=pre;record['suffix']=post
                def accept(patch,label):return offer(pre[:-1]+tuple(patch)+post[1:],label,patch)
                l,r=cfg['left'],cfg['right'];outside_steps=len(pre)+len(post)-2
                if l==r:accept((s.old_route[l],),'empty');return
                if s.distance_budget-outside_steps<0:raise ValueError('scope_resource_infeasible')
                local=Snapshot(s.name+'_LITERAL',s.free,frozenset(map(tuple,cfg['required'])),frozenset(),
                               s.old_route[l],s.old_route[r],s.old_route[l:r+1],0,s.distance_budget-outside_steps)
                tick(deadline);localg=UnifiedGeometry(local,deadline)
                if localg.precheck():raise ValueError('infeasible input')
                # Exactly the original engine fallback stage, before H/V candidate generation.
                accept(local.old_route,'old_suffix')
                accept(localg.expand(repair_visits(local)),'common_fallback')
            try:
                stage(phase,initial_repair);record['status']=stages[-1]['status']
            except DeadlineExceeded:record['status']='deadline';raise
            finally:
                record['candidate_ids']=list(range(before,len(events)));record['end_public_elapsed']=time.perf_counter()-t0
        construct_best=best_event['candidate_id'] if best_event else None
        construction_end=time.perf_counter();active_cfg=None
        if method=='POOL_PLUS1' and construction_end<deadline:
            phase='continue_R_PLUS1';continuation_entry=time.perf_counter();continuation_available=deadline-continuation_entry
            def callback(event):register(event,'continue_R_PLUS1:'+event['label'])
            continuation=fixed_solve(s,initial,'LITERAL',continuation_available,seed,scope_name='R_PLUS1',
                                     absolute_deadline=deadline,public_t0=t0,on_candidate=callback)
    except DeadlineExceeded:status='deadline'
    except (NoPath,ValueError) as exc:status='planning_failure';stages.append(dict(stage=phase,status='planning_failure',reason=str(exc),end_public_elapsed=time.perf_counter()-t0))
    end=time.perf_counter()
    if construct_best is None:
        construct_events=[e for e in events if not e['source'].startswith('continue_') and e['accepted']]
        construct_best=construct_events[-1]['candidate_id'] if construct_events else None
    construction_seconds=(continuation_entry-t0) if continuation_entry is not None else end-t0
    return dict(method=method,budget=budget,seed=seed,route=best or (),
        core_route=(best or ()) if best_event and best_event.get('patch') is not None else (),
        core_patch=best_event.get('patch') or () if best_event else (),core_scope=best_event.get('source_scope') if best_event else None,
        source=best_event['source'] if best_event else None,selected_candidate_id=best_event['candidate_id'] if best_event else None,
        seconds=end-t0,status=status,public_t0=t0,absolute_deadline=deadline,range_plan=plan,
        initial_repairs=init_records,candidate_events=events,acceptances=acceptances,stages=stages,
        construction_best_candidate_id=construct_best,construction_seconds=construction_seconds,
        continuation_entry_public_elapsed=continuation_entry-t0 if continuation_entry is not None else None,
        continuation_available_seconds=continuation_available,continuation_seconds=end-continuation_entry if continuation_entry is not None else 0,
        continuation=continuation,continuation_subcalls=int(continuation_entry is not None),
        local_initial_fallback_subcalls=len(init_records),overrun_gt_10ms=end-t0>budget+.01)
