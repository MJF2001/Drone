"""Independent diagnostic physics/ledger auditor, no planner imports."""
import math,heapq,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3'))
from audit_special import prune_checks
def pts(xs):return set(map(tuple,xs))
def cost(path):return math.fsum(math.hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(path,path[1:]))
def legal(a,b,f):
    dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1])
    return a in f and b in f and (dx,dy) in ((1,0),(0,1),(1,1)) and (dx!=dy or {(a[0],b[1]),(b[0],a[1])}<=f)
def distance(f,a,b):
    ds={a:0.};q=[(0.,a)]
    while q:
        d,u=heapq.heappop(q)
        if d!=ds[u]:continue
        if u==b:return d
        for dx in range(-1,2):
            for dy in range(-1,2):
                v=u[0]+dx,u[1]+dy
                if legal(u,v,f):
                    z=d+math.hypot(dx,dy)
                    if z<ds.get(v,math.inf):ds[v]=z;heapq.heappush(q,(z,v))
    return math.inf
def audit(c,r,budget):
    f=pts(c['free']);t=pts(c['targets']);h=pts(c['covered']);start=tuple(c['current']);service=t-h-{start}
    assert r['version']=='CSTAR_DIAGONAL_SENSITIVITY_v0.1' and pts(r['initial_service'])==service
    path=list(map(tuple,r['diagnostic_route']));assert path and path[0]==start and set(path)<=f
    assert all(legal(a,b,f) for a,b in zip(path,path[1:]))
    assert abs(r['diagnostic_distance']-cost(path))<1e-8
    pending=set(service);cursor=0
    for e in r['task_events']:
        a,b=e['start_index'],e['end_index'];assert a==cursor and a<=b<len(path)
        credits=pending&set(path[a+1:b+1]);assert credits==pts(e['credited']);pending-=credits
        assert pending==pts(e['pending_after']);cursor=b
        if not e['interrupted']:
            rcg=list(map(tuple,e['rcg_route']));assert path[a]==rcg[0] and path[b]==rcg[-1]
            assert abs(cost(path[a:b+1])-cost(rcg))<1e-8,'executed graph edge metric mismatch'
    assert pending==pts(r['pending'])==t-h-set(path)
    assert not r['completion_tsp'] and r['knowledge_scope']=='closed_current_task_domain'
    good=r['status']=='task_complete';prunes,partial=prune_checks(r,good)
    for e in r['prune_audits']:
        for snap in (e['before'],e['after']):assert all(n[2]=='Cl' for n in snap['nodes'] if tuple(n[:2]) not in service)
    events=[e for e in r['events'] if e['type']=='tsp']
    assert [it['tsp'] for it in r['iterations'] if it.get('tsp')]==[e for e in events if 'moved_steps' in e]
    for e in events:
        s=tuple(e['start']);g=tuple(e['goal']);dense=pts(e['dense_nodes']);order=list(map(tuple,e['order']))
        assert dense-{s,g}<=service and dense<=set(order) and order[0]==s
        if e['case'] in (1,2):assert order[-1]==(g if e['case']==1 else s)
        else:assert e['end'] is None
        assert path[e['step']]==s
        if 'moved_steps' in e:assert path[e['step']+e['moved_steps']]==order[-1]
    if good:
        assert list(map(tuple,r['route']))==path and path[-1]==tuple(c['base']) and not pending
        assert cost(path)<=c['distance_budget']+1e-9 and r['seconds']<budget
        assert abs(r['route_distance']-cost(path))<1e-8
        assert abs(cost(path[cursor:])-distance(f,path[cursor],tuple(c['base'])))<1e-8
    else:assert not r['route'] and r['route_distance'] is None
    return dict(accepted=good,status=r['status'],moves=len(path)-1,distance=cost(path) if good else None,diagonal_moves=sum(abs(a[0]-b[0])==abs(a[1]-b[1])==1 for a,b in zip(path,path[1:])),prunes=prunes,interrupted_prunes=partial,hole_tours=len(events),seconds=r['seconds'])
