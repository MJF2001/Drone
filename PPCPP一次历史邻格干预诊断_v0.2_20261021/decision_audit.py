"""Audit saved decisions independently. BFS distances only; no route search."""
from probe_common import *
import math,collections
def adjacent(p):
    x,y=p;return [(x+1,y),(x,y+1),(x-1,y),(x,y-1)]
def bfs(f,start):
    d={start:0};q=collections.deque([start])
    while q:
        p=q.popleft()
        for z in adjacent(p):
            if z in f and z not in d:d[z]=d[p]+1;q.append(z)
    return d

def audit(c,out):
    x=out['result'];native=x['raw']['branches']['P0'];route=list(map(tuple,x['raw']['route']));assert native['route']==x['raw']['route'] and native['trace']==x['raw']['trace'];m=both(c,route);trace=native['trace'];f=set(map(tuple,c['free']));h=set(map(tuple,c['covered']));targets=set(map(tuple,c['targets']));pending=targets-h-{route[0]};pred=tuple(c['predator']);previous=tuple(c['previous']);dist={};rows=[];forced=0
    def distance(p):
        if p not in dist:dist[p]=bfs(f,p)
        return dist[p]
    for i,e in enumerate(trace):
        idx=e['index'];cur=route[idx];prev=route[idx-1] if idx else previous;end=trace[i+1]['index'] if i+1<len(trace) else len(route)-1
        assert list(cur)==e['current'] and e['pending_count']==len(pending)
        if e['kind']=='forced_history_step':
            forced+=1;assert idx==0 and i==0 and route[1]==(5,1) and cur==(5,2) and prev==(4,2);assert route[1] in h and route[1] not in pending and end==1
            z=native['intervention'];assert z==e['intervention'] and z['trigger_count']==1 and z['added_steps']==1 and z['added_new_capture_credit']==0;assert z['before']['pending']==z['after']['pending']==norm(sorted(pending));assert z['before']['distance_remaining']==c['distance_budget'] and z['after']['distance_remaining']==c['distance_budget']-1;assert z['after']['previous']==list(cur) and z['route_index_after']==1
        elif e['kind']=='local':
            assert e['previous']==list(prev);opts=sorted(q for q in adjacent(cur) if q in pending and q in f);assert opts;ds={q:math.hypot(q[0]-pred[0],q[1]-pred[1]) for q in opts};lo=min(ds.values());hi=max(ds.values());expected=[]
            for q in opts:
                rd=(ds[q]-lo)/(hi-lo) if hi>lo else 0.;v=(cur[0]-prev[0],cur[1]-prev[1]);z=(q[0]-cur[0],q[1]-cur[1]);rs=(v[0]*z[0]+v[1]*z[1]+1)/2;rb=(4-sum(n in pending and n in f for n in adjacent(q)))/4;expected.append(dict(cell=list(q),distance_reward=rd,straight_reward=rs,boundary_reward=rb,score=rd+2.*rs+.5*rb))
            assert expected==e['options'];chosen=min(expected,key=lambda o:(-o['score'],tuple(o['cell'])))['cell'];assert e['goal']==chosen and list(route[idx+1])==chosen and end==idx+1
        elif e['kind']=='recovery':
            assert e['previous']==list(prev) and not any(q in pending and q in f for q in adjacent(cur));d=distance(cur);goal=min(pending,key=lambda q:(d[q],q));assert list(goal)==e['goal'] and route[end]==goal and end-idx==d[goal]
        elif e['kind']=='return':assert not pending and e['goal']==c['base'] and route[end]==tuple(c['base']) and end-idx==distance(cur)[tuple(c['base'])]
        else:raise AssertionError(('unknown event',e['kind']))
        # Audit only literal saved segments. Nothing is generated or connected.
        before=len(pending)
        for q in route[idx+1:end+1]:pending.discard(q)
        if e['kind'] in ('local','recovery'):assert len(pending)<before
        rows.append(dict(event=i,index=idx,end_index=end,kind=e['kind'],current=cur,previous=prev,goal=e['goal'],pending_before=before,pending_after=len(pending),passed=True))
    assert not pending and forced==(1 if out['job']['mode']=='ON' else 0)
    first=next((dict(index=i,cell=p) for i,p in enumerate(route[1:],1) if p in targets-h),None);return_origin=next((i for i,p in enumerate(route[1:],1) if p==route[0]),None)
    return norm(dict(metrics=m,decisions=rows,forced_count=forced,ordinary_BFS_tables=len(dist),BFS_start_points=sorted(dist),second_step_returns_to_origin=len(route)>2 and route[2]==route[0],first_return_origin_index=return_origin,first_new_capture=first,first_regular_decision=next((r for r in rows if r['kind'] in ('local','recovery')),None),completion_position=route[m['completion_step']]))

def rejoin(c,frozen,on):
    def states(route):
        pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])};out=[]
        for i,p in enumerate(route):
            p=tuple(p);pending.discard(p);prev=tuple(route[i-1]) if i else tuple(c['previous']);out.append((p,prev,frozenset(pending)))
        return out
    aa=frozen['result']['raw']['route'];bb=on['result']['raw']['route'];base=states(aa);probe=states(bb);lookup=collections.defaultdict(list)
    for i,state in enumerate(base):lookup[state].append(i)
    matches=[]
    for j,state in enumerate(probe[1:],1):
        for i in lookup.get(state,[]):matches.append(dict(frozen_index=i,probe_index=j,current=state[0],previous=state[1],pending=sorted(state[2]),same_literal_suffix=aa[i:]==bb[j:],frozen_remaining_resource=c['distance_budget']-i,probe_remaining_resource=c['distance_budget']-j,same_distance_resource=i==j))
    return norm(dict(found=bool(matches),first=matches[0] if matches else None,all_matches=matches,warning='These compare deterministic decision-state current/previous/pending plus fixed F/predator/weights/tie and policy phase. Absolute timing/cache/used distance may differ; not a claim of identical full running state.'))
