"""Read saved certificates only; enumerates no new states and runs no search."""
import gzip,json
def audit(request,result,path):
    with gzip.open(path,'rt',encoding='utf8') as f:c=json.load(f)
    area=set(map(tuple,request['free']));cells=sorted(area);n=len(cells);index={p:i for i,p in enumerate(cells)};ts=sorted(map(tuple,request['tasks']));bits={p:1<<i for i,p in enumerate(ts)};full=(1<<len(ts))-1;s=tuple(request['start']);b=tuple(request['base']);e=tuple(request['last']) if request['last'] is not None else None
    rows=[]
    if c['engine']=='BFS':
        assert list(map(tuple,c['cells']))==cells and list(map(tuple,c['tasks']))==ts
        for packed,parent,d in c['records']:mask,pos=divmod(packed,n);rows.append((cells[pos],mask,parent,d))
    else:
        assert c['engine']=='DIJKSTRA';mapping=list(map(tuple,c['tasks']));assert set(mapping)==set(ts)
        for x,y,remaining,parent,d in c['records']:
            acquired=0
            for i,p in enumerate(mapping):
                if not remaining&(1<<i):acquired|=bits[p]
            rows.append(((x,y),acquired,parent,d))
    seen={(p,m):(i,d) for i,(p,m,parent,d) in enumerate(rows)};assert len(rows)==len(seen)==result['discovered'];assert rows[0]==(s,bits.get(s,0),-1,0)
    invalid=e==s and bool(set(ts)-{s});assert c['invalid_start']==invalid
    for i,(p,m,parent,d) in enumerate(rows):
        assert p in area and 0<=m<=full and (not bits.get(p,0) or m&bits[p])
        if i:
            assert 0<=parent<len(rows);a,old,_,depth=rows[parent];assert depth+1==d and abs(a[0]-p[0])+abs(a[1]-p[1])==1 and m==old|bits.get(p,0)
            assert not(e==p and not old&bits.get(e,0) and (old|bits.get(e,0))!=full)
    popped=c['popped'];popped_set=set(popped);assert len(popped)==len(popped_set)==result['expanded']
    ds=[rows[i][3] for i in popped];assert ds==sorted(ds)
    if result['status']=='unresolved':assert result['length'] is None and not result['route'];return dict(status='partial_only',states=len(rows))
    if invalid:
        assert result['status']=='infeasible' and len(rows)==1 and not popped;return dict(status='proved_infeasible_start',states=1)
    if result['status']=='optimal':
        goal=c['goal'];p,m,parent,d=rows[goal];assert p==b and m==full and d==result['length']<=request['resource']
        assert all(i in popped_set for i,r in enumerate(rows) if r[3]<d)
        if c['engine']=='BFS':assert popped==list(range(len(popped))) and goal==len(popped)
        rebuilt=[];k=goal
        while k!=-1:rebuilt.append(rows[k][0]);k=rows[k][2]
        assert rebuilt[::-1]==list(map(tuple,result['route']))
    else:assert result['status']=='infeasible' and c['goal'] is None and len(popped)==len(rows)
    # Parent witnesses establish reachability; closure before the first goal (or
    # over all states if exhausted) proves no lower-cost terminal was omitted.
    for i in popped:
        p,m,parent,d=rows[i];assert not(p==b and m==full)
        if d>=request['resource']:continue
        x,y=p
        for z in ((x,y-1),(x+1,y),(x,y+1),(x-1,y)):
            if z not in area:continue
            bit=bits.get(z,0)
            if e==z and not m&bit and (m|bit)!=full:continue
            assert (z,m|bit) in seen and seen[z,m|bit][1]<=d+1
    return dict(status='optimality_closed' if result['status']=='optimal' else 'infeasibility_closed',states=len(rows),closure_checked=len(popped))
