"""Exact unit-step coverage-return BFS. No strip/tree service constraints."""
from array import array
from collections import deque
import time


def exact_coverage(s,seconds=30,max_targets=12):
    if s.radius!=0:
        raise ValueError('single-cell coverage required')
    begin=time.perf_counter()
    pending=sorted(s.targets-s.covered)
    if len(pending)>max_targets:
        raise ValueError('exact target limit exceeded')
    points=sorted(s.free)
    indexes={p:i for i,p in enumerate(points)}
    n=len(points)
    bits={p:1<<i for i,p in enumerate(pending)}
    neighbors=[]
    for x,y in points:
        neighbors.append([indexes[p] for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if p in indexes])
    point_bits=[bits.get(p,0) for p in points]
    start=bits.get(s.current,0)*n+indexes[s.current]
    goal=((1<<len(pending))-1)*n+indexes[s.base]
    parent=array('i',[-2])*(n*(1<<len(pending)))
    parent[start]=-1
    queue=deque([start])
    expanded=0
    while queue:
        if expanded%1024==0 and time.perf_counter()>begin+seconds:
            return {'status':'timeout','route':(),'seconds':time.perf_counter()-begin,'expanded':expanded}
        state=queue.popleft()
        if state==goal:
            route=[]
            while state!=-1:
                route.append(points[state%n])
                state=parent[state]
            route=tuple(reversed(route))
            return {'status':'optimal','route':route,'length':len(route)-1,
                'seconds':time.perf_counter()-begin,'expanded':expanded,
                'pending':len(pending),'state_capacity':len(parent),
                'budget_feasible':len(route)-1<=s.distance_budget}
        mask,pose=divmod(state,n)
        for nxt in neighbors[pose]:
            successor=(mask|point_bits[nxt])*n+nxt
            if parent[successor]==-2:
                parent[successor]=state
                queue.append(successor)
        expanded+=1
    return {'status':'infeasible','route':(),'seconds':time.perf_counter()-begin,'expanded':expanded}


def independent_metric_optimum(s,max_targets=12):
    """Independent BFS distances + Held-Karp; exact for this single-cell model.

    Any legal coverage walk induces a first-visit terminal order, and any metric
    terminal tour expands to a legal covering walk. Both optimum values coincide.
    """
    targets=sorted(s.targets-s.covered)
    if len(targets)>max_targets:
        raise ValueError('exact target limit exceeded')
    terminals=[s.current]+targets+[s.base]
    matrix=[]
    for origin in terminals:
        ds={origin:0}
        queue=deque([origin])
        while queue:
            x,y=queue.popleft()
            for p in ((x,y+1),(x,y-1),(x+1,y),(x-1,y)):
                if p in s.free and p not in ds:
                    ds[p]=ds[x,y]+1
                    queue.append(p)
        matrix.append([ds[t] for t in terminals])
    if not targets:
        return matrix[0][-1]
    count=len(targets)
    dp={(1<<j,j):matrix[0][j+1] for j in range(count)}
    for mask in range(1,1<<count):
        for last in range(count):
            value=dp.get((mask,last))
            if value is None:
                continue
            for nxt in range(count):
                if not mask>>nxt&1:
                    key=mask|1<<nxt,nxt
                    candidate=value+matrix[last+1][nxt+1]
                    dp[key]=min(dp.get(key,float('inf')),candidate)
    final=(1<<count)-1
    return min(dp[final,last]+matrix[last+1][-1] for last in range(count))
