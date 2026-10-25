"""Independent input/history/witness checks; never imports a planner."""
from collections import deque
def pts(xs):return set(map(tuple,xs))
def legal(free,route):
    assert route,'empty witness';route=list(map(tuple,route));free=pts(free)
    assert set(route)<=free,'blocked witness'
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:])),'nonunit witness'
def check_case(c,witness):
    f=pts(c['free']);t=pts(c['targets']);h=pts(c['covered']);p=pts(c['published_targets']);d=pts(c['deferred_targets'])
    assert c['split']=='development' and c['radius']==0
    assert t==p&f and h<=p and d==p-f-h,'ledger'
    assert tuple(c['current']) in f and tuple(c['base']) in f
    # A newly blocked cell may have been legitimately captured before the event.
    # Historical completion is retained, but it is no longer traversable.
    assert c['distance_budget']>=0
    legal(c['free'],witness)
    assert tuple(witness[0])==tuple(c['current']) and tuple(witness[-1])==tuple(c['base']),'endpoints'
    assert t<=h|pts(witness),'incomplete witness'
    assert len(witness)-1<=c['distance_budget'],'witness exceeds resource'
    reached={tuple(c['current'])};queue=deque(reached)
    while queue:
        x,y=queue.popleft()
        for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if q in f and q not in reached:reached.add(q);queue.append(q)
    assert (t-h)|{tuple(c['base'])}<=reached,'inaccessible active task'
    return dict(free=len(f),active_targets=len(t),covered=len(h),remaining=len(t-h-{tuple(c['current'])}),deferred=len(d),witness_steps=len(witness)-1,resource=c['distance_budget'],physical_feasible=True)
def check_history(initial,h):
    route=h['executed_route'];legal(initial['free'],route)
    assert tuple(route[0])==tuple(initial['current']) and route[-1]==h['current']
    targets=pts(initial['targets']);covered=pts(route)&targets
    assert covered==pts(h['covered'])
    assert len(pts(route[:-1])&targets)<(len(targets)+1)//2<=len(covered),'not first threshold'
    assert len(route)-1==h['executed_steps']==h['index']
    assert initial['distance_budget']-(len(route)-1)==h['remaining_budget'],'resource debit'
    assert h['old_route'][0]==h['current']
    return dict(executed_steps=len(route)-1,covered=len(covered),remaining_budget=h['remaining_budget'],first_50_percent=True)
