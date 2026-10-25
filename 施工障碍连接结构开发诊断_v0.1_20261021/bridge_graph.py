"""Offline grid graph operations. No planner imports."""
from collections import deque

def neighbors(p, f):
    x,y=p
    return sorted(q for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if q in f)

def reach(f,s,blocked=None):
    seen={s};todo=[s]
    for p in todo:
        for q in neighbors(p,f):
            if blocked is not None and frozenset((p,q))==blocked:continue
            if q not in seen:seen.add(q);todo.append(q)
    return seen

def bfs(f,s):
    d={s:0};parent={s:None};q=deque([s])
    while q:
        p=q.popleft()
        for v in neighbors(p,f):
            if v not in d:d[v]=d[p]+1;parent[v]=p;q.append(v)
    return d,parent

def bridges(f):
    # Iterative Tarjan avoids recursion depth assumptions.
    tin={};low={};parent={};out=[];t=0
    for root in sorted(f):
        if root in tin:continue
        tin[root]=low[root]=t;t+=1;parent[root]=None
        stack=[(root,iter(neighbors(root,f)))]
        while stack:
            p,it=stack[-1]
            try:q=next(it)
            except StopIteration:
                stack.pop();v=parent[p]
                if v is not None:
                    low[v]=min(low[v],low[p])
                    if low[p]>tin[v]:out.append(tuple(sorted((p,v))))
                continue
            if q==parent[p]:continue
            if q in tin:low[p]=min(low[p],tin[q])
            else:
                parent[q]=p;tin[q]=low[q]=t;t+=1
                stack.append((q,iter(neighbors(q,f))))
    return sorted(out)

def verified_bridges(f):
    tar=bridges(f);brute=[]
    # Verify every graph edge, including nonbridges, by independent deletion.
    for p in sorted(f):
        for q in neighbors(p,f):
            if p<q and q not in reach(f,p,frozenset((p,q))):brute.append((p,q))
    assert tar==brute
    return tar

def witness(f,s,b):
    # DFS spanning walk returns to s, then independent BFS to base.
    path=[s];seen={s};stack=[(s,iter(neighbors(s,f)))]
    while stack:
        p,it=stack[-1]
        try:q=next(it)
        except StopIteration:
            stack.pop()
            if stack:path.append(stack[-1][0])
            continue
        if q not in seen:seen.add(q);path.append(q);stack.append((q,iter(neighbors(q,f))))
    assert seen==f
    d,parents=bfs(f,s);tail=[b]
    while tail[-1]!=s:tail.append(parents[tail[-1]])
    path+=tail[::-1][1:]
    assert len(path)-1==2*(len(f)-1)+d[b]
    return path

def cut_table(c,route=None,verify=True):
    f=set(map(tuple,c['free']));s=tuple(c['current']);b=tuple(c['base'])
    u=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{s}
    edges=verified_bridges(f) if verify else bridges(f);rows=[];groups={}
    path=list(map(tuple,route)) if route else None
    for a,z in edges:
        side=f-reach(f,s,frozenset((a,z))) # canonical side excludes start
        tasks=sorted(u&side);cross=b in side;lb=1 if cross else 2 if tasks else 0
        r=dict(edge=[a,z],start_side=False,base_other_side=cross,other_size=len(side),other_pending=tasks,lower_bound=lb)
        signature=(cross,tuple(tasks));key=repr(signature)
        if path is not None:
            counts=sum(frozenset((p,q))==frozenset((a,z)) for p,q in zip(path,path[1:]));assert counts>=lb
            seen=set();visits=[];first_enter=None;last_complete=None;last_exit=None;unfinished_exits=0;waiting=False
            for i,p in enumerate(path):
                if p in tasks:seen.add(p)
                if tasks and len(seen)==len(tasks) and last_complete is None:last_complete=i
                if i and path[i-1] not in side and p in side:
                    if first_enter is None:first_enter=i
                    if waiting:unfinished_exits+=1;waiting=False
                if i and path[i-1] in side and p not in side:
                    remain=len(set(tasks)-seen);visits.append(dict(step=i,remaining=remain));last_exit=i;waiting=remain>0
            r.update(crossings=counts,excess=counts-lb,first_enter=first_enter,exits=visits,last_completion=last_complete,final_exit=last_exit,unfinished_exit_reentry=unfinished_exits)
        rows.append(r);groups.setdefault(key,[]).append(r)
    grouped=[]
    for key,rr in sorted(groups.items()):
        g=dict(signature=key,edge_count=len(rr),lower_bound=rr[0]['lower_bound'],other_pending=rr[0]['other_pending'],base_other_side=rr[0]['base_other_side'])
        if path is not None:
            g.update(crossings_min=min(r['crossings'] for r in rr),crossings_max=max(r['crossings'] for r in rr),excess_min=min(r['excess'] for r in rr),excess_max=max(r['excess'] for r in rr))
        grouped.append(g)
    return dict(edges=rows,groups=grouped)

def structure(c):
    f=set(map(tuple,c['free']));unseen=set(f);components=[]
    while unseen:
        comp=reach(f,min(unseen));components.append(len(comp));unseen-=comp
    tables=[bfs(f,p)[0] for p in sorted(f)]
    distances=[d[q] for p,d in zip(sorted(f),tables) for q in sorted(d) if p<q]
    cut=cut_table(c)
    return dict(free=len(f),components=components,diameter=max(distances,default=0),mean_pair_distance=sum(distances)/len(distances) if distances else 0,start_base_distance=bfs(f,tuple(c['current']))[0].get(tuple(c['base'])),bridge_count=len(cut['edges']),task_bridge_groups=sum(bool(g['other_pending']) for g in cut['groups']),cuts=cut)
