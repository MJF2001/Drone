"""Single-interval range diagnostic adapter; no automatic range selector."""
from collections import deque
import time,hashlib,json
import portable_frozen
from model import Snapshot,DeadlineExceeded,NoPath
from baseline_suite import check_contract
from unified_geometry import UnifiedGeometry,single_cell_audit
from audit import audit
from range_p2_engine_20261015 import solve as engine_solve

RANGES=('R_SEED','R_PLUS1','R_PLUS2','R_ALL')
def tick(deadline):
    if time.perf_counter()>deadline:raise DeadlineExceeded()
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def neighbors(p):
    x,y=p;return ((x-1,y),(x,y-1),(x,y+1),(x+1,y))

def service_blocks(s,initial,deadline=float('inf')):
    pending=set(initial)-set(s.covered)-{s.current};seen=set();blocks=[];group=[];direction=None
    def finish():
        nonlocal group,direction
        if group:blocks.append(dict(start=group[0][0],end=group[-1][0],cells=[p for _,p in group]))
        group=[];direction=None
    for i,p in enumerate(s.old_route):
        tick(deadline)
        if p not in pending or p in seen:finish();continue
        seen.add(p)
        if group:
            prev_i,prev=group[-1];vec=(p[0]-prev[0],p[1]-prev[1])
            if i!=prev_i+1 or (direction is not None and direction!=vec):finish()
            else:direction=vec
        group.append((i,p))
    finish()
    if pending-seen:raise ValueError('old_plan_does_not_service_initial_pending')
    return blocks

def range_plan(s,initial,deadline=float('inf')):
    blocks=service_blocks(s,initial,deadline);old=s.old_route;N=len(old)-1
    bounds=sorted({0,N}|{b['start'] for b in blocks});legal=[i for i in bounds if old[i] in s.free]
    bad=[i for i,p in enumerate(old) if p not in s.free];spans=[]
    if bad:
        spans.append((max(i for i in legal if i<min(bad)),min(i for i in legal if i>max(bad))))
    new=set(s.targets)-set(initial)-set(s.covered)-set(old);components=[]
    while new:
        tick(deadline);start=min(new);new.remove(start);component={start};q=deque([start])
        while q:
            tick(deadline)
            for p in neighbors(q.popleft()):
                if p in new:new.remove(p);component.add(p);q.append(p)
        ds={p:0 for p in component};q=deque(sorted(component))
        while q:
            tick(deadline);p=q.popleft()
            for z in neighbors(p):
                if z in s.free and z not in ds:ds[z]=ds[p]+1;q.append(z)
        reachable=[i for i in legal if old[i] in ds]
        if not reachable:raise NoPath('new_component_unreachable')
        anchor=min(reachable,key=lambda i:(ds[old[i]],i));at=bounds.index(anchor)
        left=bounds[max(0,at-1)];right=bounds[min(len(bounds)-1,at+1)]
        # Closure extends through blocked boundary endpoints; never relocate obstacles.
        left=max(i for i in legal if i<=left);right=min(i for i in legal if i>=right)
        spans.append((left,right));components.append(dict(cells=sorted(component),anchor_index=anchor,distance=ds[old[anchor]]))
    if spans:l=min(a for a,b in spans);r=max(b for a,b in spans)
    else:l=r=0
    seed=(l,r);li=bounds.index(l);ri=bounds.index(r);plans={}
    for method,steps in (('R_SEED',0),('R_PLUS1',1),('R_PLUS2',2),('R_ALL',None)):
        if steps is None:left,right=0,N
        else:
            left=bounds[max(0,li-steps)];right=bounds[min(len(bounds)-1,ri+steps)]
            left=max(i for i in legal if i<=left);right=min(i for i in legal if i>=right)
        prefix=old[:left+1];suffix=old[right:];done=set(s.covered)|(set(prefix)&s.targets)
        required=((s.targets-done)&set(old[left:right])) | (s.targets-done-set(suffix))
        assert set(prefix)|set(suffix)<=s.free
        plans[method]=dict(left=left,right=right,start=old[left],join=old[right],required=sorted(required),
            prefix_steps=left,suffix_steps=N-right,pending_count=len(s.targets-s.covered-{s.current}),
            required_count=len(required),modifiable_blocks=sum(b['start']>=left and b['start']<right for b in blocks),
            block_count=len(blocks),prefix_sha256=digest(prefix),suffix_sha256=digest(suffix))
    return dict(blocks=blocks,boundaries=bounds,old_collision_indices=bad,new_components=components,
        seed_span=seed,plans=plans,limitation='One enclosing route interval; nearest-graph-distance insertion anchor; fixed literal prefix/suffix.')

def solve(s,initial,method,budget,seed):
    begin=time.perf_counter();deadline=begin+budget;best=None;source=None;core_best=None;core_patch=None
    detail=dict(core_valid_before_deadline=False,acceptances=[],core_acceptances=[],stages={},range_plan=None);active='contract'
    def offer(route,label,patch=None):
        nonlocal best,source,core_best,core_patch
        tick(deadline);route=tuple(route);patch=tuple(patch) if patch is not None else None
        valid=bool(route) and single_cell_audit(s,route)['valid'];accepted_at=time.perf_counter();tick(deadline)
        if valid:
            if patch is not None and (core_best is None or len(route)<len(core_best)):
                core_best=tuple(route);core_patch=tuple(patch);detail['core_valid_before_deadline']=True
                detail['core_acceptances'].append(dict(seconds=accepted_at-begin,steps=len(route)-1,label=label,route_sha256=digest(route)))
            if best is None or len(route)<len(best):
                best=tuple(route);source=label;detail['acceptances'].append(dict(seconds=accepted_at-begin,
                    steps=len(route)-1,label=label,route_sha256=digest(route)))
        return valid
    try:
        check_contract(s,initial,budget)
        if method not in RANGES:raise ValueError('unknown range')
        active='global_geometry';g=UnifiedGeometry(s,deadline)
        if g.precheck():raise ValueError('environment_infeasible')
        active='common_fallback';offer(s.old_route,'old_suffix');left=set(s.targets-s.covered);visits=[]
        for p in s.old_route:
            tick(deadline)
            if p in left and p in s.free:visits.append(p);left.remove(p)
        visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
        offer(g.expand(visits),'common_fallback');detail['stages']['fallback_end']=time.perf_counter()-begin
        active='range_plan';plan=range_plan(s,initial,deadline);detail['range_plan']=plan
        cfg=plan['plans'][method];l,r=cfg['left'],cfg['right'];prefix=s.old_route[:l+1];suffix=s.old_route[r:]
        detail['stages']['range_plan_end']=time.perf_counter()-begin
        def accept(patch,label):return offer(prefix[:-1]+tuple(patch)+suffix[1:],'range_core:'+label,patch)
        active='scope_search'
        if l==r:
            accept((s.old_route[l],),'unchanged')
            detail['engine']=dict(status='empty_window',source='unchanged')
        elif s.distance_budget-l-(len(s.old_route)-1-r)<0:
            detail['engine']=dict(status='scope_resource_infeasible')
        else:
            local=Snapshot(s.name+'_'+method,s.free,frozenset(map(tuple,cfg['required'])),frozenset(),
                s.old_route[l],s.old_route[r],s.old_route[l:r+1],0,s.distance_budget-l-(len(s.old_route)-1-r))
            remaining=deadline-time.perf_counter();tick(deadline)
            er=engine_solve(local,remaining,'multi',seed,accept=accept)
            detail['engine']={k:v for k,v in er.items() if k!='route'}
        status='deadline' if detail.get('engine',{}).get('status')=='deadline' else 'finished'
    except DeadlineExceeded:status='deadline'
    except (NoPath,ValueError) as e:status='planning_failure';detail['reason']=str(e)
    seconds=time.perf_counter()-begin
    raw=dict(route=best or (),source=source,status=status,seconds=seconds,method=method,budget=budget,seed=seed,
        active_stage=active,detail=detail,core_route=core_best or (),core_patch=core_patch or (),
        fallback_selected=source in ('old_suffix','common_fallback'),overrun_gt_10ms=seconds>budget+.01)
    raw['independent_audit']=audit(s,raw['route']) if raw['route'] else None
    raw['core_independent_audit']=audit(s,raw['core_route']) if raw['core_route'] else None
    if raw['route']:assert raw['independent_audit']['valid']
    if raw['core_route']:assert raw['core_independent_audit']['valid']
    return raw
