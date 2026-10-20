"""Fixed R_PLUS1 ports/tasks, literal versus ordered shortest outside segments."""
import time
import portable_frozen
from model import Snapshot,DeadlineExceeded,NoPath
from baseline_suite import check_contract
from unified_geometry import UnifiedGeometry,single_cell_audit
from audit import audit
from road_range_candidate_20261015 import range_plan,tick,digest
from range_p2_engine_20261015 import solve as engine_solve
METHODS=('LITERAL','RECONNECT')

def responsibilities(s,cfg,deadline=float('inf')):
    pending=set(s.targets)-set(s.covered)-{s.current};l,r=cfg['left'],cfg['right']
    def order(route,required):
        seen=set();out=[]
        for p in route:
            tick(deadline)
            if p in required and p not in seen:seen.add(p);out.append(p)
        assert seen==required
        return tuple(out)
    pre=pending&set(s.old_route[:l+1]);local=set(map(tuple,cfg['required']));post=pending-pre-local
    assert not pre&local and not pre&post and not local&post and pre|local|post==pending
    return dict(prefix_visits=order(s.old_route[:l+1],pre),suffix_visits=order(s.old_route[r:],post),
        prefix_required=tuple(sorted(pre)),local_required=tuple(sorted(local)),suffix_required=tuple(sorted(post)))

def connect(g,start,visits,end,deadline=float('inf')):
    route=[start]
    for p in tuple(visits)+(end,):
        tick(deadline)
        # No incidental-service skipping: prescribed waypoints remain ordered.
        if p!=route[-1]:route.extend(g.path(route[-1],p)[1:])
    return tuple(route)

def outside_segments(s,cfg,assigned,g,method,deadline=float('inf')):
    l,r=cfg['left'],cfg['right'];literal_pre=s.old_route[:l+1];literal_post=s.old_route[r:]
    if method=='LITERAL':pre,post=literal_pre,literal_post
    elif method=='RECONNECT':
        pre=connect(g,s.current,assigned['prefix_visits'],s.old_route[l],deadline)
        post=connect(g,s.old_route[r],assigned['suffix_visits'],s.base,deadline)
    else:raise ValueError('unknown outside mode')
    assert pre[0]==s.current and pre[-1]==s.old_route[l] and post[0]==s.old_route[r] and post[-1]==s.base
    assert len(pre)<=len(literal_pre) and len(post)<=len(literal_post)
    return pre,post

def solve(s,initial,method,budget,seed):
    begin=time.perf_counter();deadline=begin+budget;best=source=core=patch_best=None
    detail=dict(range_plan=None,responsibilities=None,outside=None,acceptances=[],core_acceptances=[],stages={});active='contract'
    def offer(route,label,patch=None):
        nonlocal best,source,core,patch_best
        tick(deadline);route=tuple(route)
        valid=single_cell_audit(s,route)['valid'];at=time.perf_counter()-begin;tick(deadline)
        if valid:
            record=dict(seconds=at,steps=len(route)-1,label=label,route_sha256=digest(route))
            if patch is not None and (core is None or len(route)<len(core)):
                core=route;patch_best=tuple(patch);detail['core_acceptances'].append(record)
            if best is None or len(route)<len(best):best=route;source=label;detail['acceptances'].append(record)
        return valid
    try:
        check_contract(s,initial,budget)
        if method not in METHODS:raise ValueError('unknown mode')
        active='global_geometry';g=UnifiedGeometry(s,deadline)
        if g.precheck():raise ValueError('infeasible environment')
        active='common_fallback';offer(s.old_route,'old_suffix');left=set(s.targets-s.covered);visits=[]
        for p in s.old_route:
            tick(deadline)
            if p in left and p in s.free:visits.append(p);left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        offer(g.expand(visits),'common_fallback');detail['stages']['fallback_end']=time.perf_counter()-begin
        active='range_plan';plan=range_plan(s,initial,deadline);detail['range_plan']=plan;cfg=plan['plans']['R_PLUS1']
        assigned=responsibilities(s,cfg,deadline);detail['responsibilities']=assigned;detail['stages']['plan_end']=time.perf_counter()-begin
        active='outside';pre,post=outside_segments(s,cfg,assigned,g,method,deadline);l,r=cfg['left'],cfg['right']
        outside_steps=len(pre)+len(post)-2
        detail['outside']=dict(prefix=pre,suffix=post,prefix_steps=len(pre)-1,suffix_steps=len(post)-1,
            literal_steps=l+len(s.old_route)-1-r,saved_steps=l+len(s.old_route)-1-r-outside_steps,
            prefix_sha256=digest(pre),suffix_sha256=digest(post))
        detail['stages']['outside_end']=time.perf_counter()-begin
        def accept(patch,label):return offer(pre[:-1]+tuple(patch)+post[1:],'scope_core:'+label,patch)
        active='scope_search'
        if l==r:
            accept((s.old_route[l],),'empty');detail['engine']=dict(status='empty_window')
        elif s.distance_budget-outside_steps<0:detail['engine']=dict(status='scope_resource_infeasible')
        else:
            local=Snapshot(s.name+'_'+method,s.free,frozenset(map(tuple,cfg['required'])),frozenset(),
                s.old_route[l],s.old_route[r],s.old_route[l:r+1],0,s.distance_budget-outside_steps)
            tick(deadline);er=engine_solve(local,deadline-time.perf_counter(),'multi',seed,accept=accept)
            detail['engine']={k:v for k,v in er.items() if k!='route'}
        status='deadline' if detail.get('engine',{}).get('status')=='deadline' else 'finished'
    except DeadlineExceeded:status='deadline'
    except (NoPath,ValueError) as e:status='planning_failure';detail['reason']=str(e)
    seconds=time.perf_counter()-begin
    raw=dict(route=best or (),core_route=core or (),core_patch=patch_best or (),method=method,budget=budget,seed=seed,
        seconds=seconds,status=status,source=source,active_stage=active,detail=detail,
        fallback_selected=source in ('old_suffix','common_fallback'),overrun_gt_10ms=seconds>budget+.01)
    raw['independent_audit']=audit(s,raw['route']) if raw['route'] else None
    raw['core_independent_audit']=audit(s,raw['core_route']) if raw['core_route'] else None
    if raw['route']:assert raw['independent_audit']['valid']
    if raw['core_route']:assert raw['core_independent_audit']['valid']
    return raw
