"""Independent decision/coverage/BFS-distance audit; no solver or reward imports."""
import math,collections
def points(xs):return set(map(tuple,xs))
def bfs(free,a):
    d={a:0};q=collections.deque([a])
    while q:
        x,y=q.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if p in free and p not in d:d[p]=d[x,y]+1;q.append(p)
    return d
def audit(c,r):
    route=list(map(tuple,r['route']));free=points(c['free']);targets=points(c['targets']);covered=points(c['covered'])
    assert route and route[0]==tuple(c['current']) and route[-1]==tuple(c['base'])
    assert set(route)<=free and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
    assert targets<=covered|set(route) and len(route)-1<=c['distance_budget']
    assert 0<=r['accepted_seconds']<r['budget'] and not r['fallback_selected']
    pending=targets-covered-{route[0]};cursor=0;events=r['trace'];pred=tuple(r['predator'])
    for i,e in enumerate(events):
        assert e['index']==cursor and tuple(e['current'])==route[cursor] and e['pending_count']==len(pending)
        goal=tuple(e['goal']);end=events[i+1]['index'] if i+1<len(events) else len(route)-1
        segment=route[cursor:end+1];assert segment[0]==route[cursor] and segment[-1]==goal
        x,y=route[cursor];opts=sorted(p for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if p in pending and p in free)
        if e['kind']=='local':
            assert opts and end==cursor+1
            prev=route[cursor-1] if cursor else (tuple(r['initial_previous']) if r['initial_previous'] is not None else None)
            assert e['previous'] is None if prev is None else tuple(e['previous'])==prev
            ds=[math.dist(q,pred) for q in opts];lo=min(ds);hi=max(ds);rows=[]
            for q,d in zip(opts,ds):
                rd=(d-lo)/(hi-lo) if hi>lo else 0
                rs=0 if prev is None else math.acos(max(-1,min(1,(prev[0]-x)*(q[0]-x)+(prev[1]-y)*(q[1]-y))))/math.pi
                rb=1-sum(p in pending and p in free for p in ((q[0]-1,q[1]),(q[0]+1,q[1]),(q[0],q[1]-1),(q[0],q[1]+1)))/4
                rows.append(dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,score=rd+2*rs+.5*rb))
            assert len(rows)==len(e['options'])
            for expected,actual in zip(rows,e['options']):
                assert expected['cell']==tuple(actual['cell'])
                for key in ('distance_reward','straight_reward','boundary_reward','score'):assert abs(expected[key]-actual[key])<1e-12
            assert goal==min(rows,key=lambda v:(-v['score'],v['cell']))['cell']
        elif e['kind']=='recovery':
            assert not opts and pending;d=bfs(free,route[cursor]);assert goal==min(pending,key=lambda p:(d[p],p)) and end-cursor==d[goal]
        else:
            assert e['kind']=='return' and not pending and goal==tuple(c['base']);assert end-cursor==bfs(free,route[cursor])[goal]
        pending-=set(segment);cursor=end
    assert cursor==len(route)-1 and not pending
    return dict(valid=True,steps=len(route)-1,decisions=len(events))
