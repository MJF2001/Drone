"""Four-neighbour model primitives; no baseline fallback or extra candidates."""
from collections import deque
from math import floor,ceil
class Deadline(Exception):pass
class Unreachable(Exception):pass
def neighbours(p):
    x,y=p;return ((x-1,y),(x,y+1),(x,y-1),(x+1,y))
def components(cells,check=lambda stage:None):
    unseen=set(cells);out=[]
    while unseen:
        check('components');s=min(unseen);unseen.remove(s);part={s};q=[s]
        while q:
            check('components');p=q.pop()
            for v in neighbours(p):
                if v in unseen:unseen.remove(v);part.add(v);q.append(v)
        out.append(part)
    return out
def center(cells):
    n=len(cells);sx=sum(p[0] for p in cells);sy=sum(p[1] for p in cells)
    return min(cells,key=lambda p:((n*p[0]-sx)**2+(n*p[1]-sy)**2,p)) if n else None
def cap_center(cells,free):
    if not cells:return None
    x=sum(p[0] for p in cells)/len(cells);y=sum(p[1] for p in cells)/len(cells)
    near=min({(a,b) for a in (floor(x),ceil(x)) for b in (floor(y),ceil(y))},key=lambda p:((p[0]-x)**2+(p[1]-y)**2,p))
    return near if near in free else center(cells)
class Metric:
    def __init__(self,free,check=lambda stage:None):
        self.free=set(free);self.check=check;self.points=sorted(free);self.ids={p:i for i,p in enumerate(self.points)}
        self.adj=[]
        for p in self.points:check('geometry');self.adj.append([self.ids[q] for q in neighbours(p) if q in self.ids])
        self.rows=0;self.path_builds=0
    def _bfs(self,start,goals,parents=False):
        self.check('bfs');s=self.ids[start];waiting={self.ids[p] for p in goals};waiting.discard(s)
        ds=[-1]*len(self.points);ds[s]=0;pr=[-1]*len(ds) if parents else None;q=deque([s])
        while q and waiting:
            self.check('bfs');u=q.popleft();nd=ds[u]+1
            for v in self.adj[u]:
                if ds[v]<0:
                    ds[v]=nd
                    if parents:pr[v]=u
                    q.append(v);waiting.discard(v)
        if waiting:raise Unreachable('current public free map disconnected for requested terminals')
        return ds,pr
    def distances_from(self,start,goals):
        """One exact BFS row, same geometry/ties as matrix; no state cache."""
        self.check('single_source');goals=list(goals)
        for p in [start]+goals:
            self.check('single_source')
            if p not in self.ids:raise Unreachable('terminal not in public free map')
        if not goals:return []
        ds,_=self._bfs(start,goals);self.rows+=1
        result=[]
        for p in goals:
            self.check('single_source');result.append(ds[self.ids[p]])
        return result
    def matrix(self,terminals):
        self.check('matrix');n=len(terminals);out=[[0]*n for _ in range(n)]
        for i,p in enumerate(terminals):
            self.check('matrix')
            if p not in self.ids:raise Unreachable('terminal not in public free map')
            needed=terminals[i+1:]
            if not needed:continue
            ds,_=self._bfs(p,needed);self.rows+=1
            for j in range(i+1,n):out[i][j]=out[j][i]=ds[self.ids[terminals[j]]]
        return out
    def path(self,a,b):
        self.check('connector')
        if a not in self.ids or b not in self.ids:raise Unreachable('connector endpoint')
        if a==b:return [a]
        # Canonical unordered-endpoint geometry, no call-order dependence.
        lo,hi=sorted((a,b));_,parent=self._bfs(lo,[hi],True);v=self.ids[hi];seq=[hi]
        while self.points[v]!=lo:
            self.check('reconstruct');v=parent[v];seq.append(self.points[v])
        seq.reverse();self.path_builds+=1
        return seq if a==lo else seq[::-1]
def tour(items,start,position,metric,end=None):
    """Fixed-start NN then strict improving 2-opt; end is item label or None.
    Distinct region labels may have identical coordinates and are NOT deduped.
    Solve the stated open objective directly, not CAP's ambiguous infinite dummy.
    """
    items=list(items);labels=[start]+[p for p in items if p!=start]
    if end is not None and end not in labels:labels.append(end)
    positions=[position(p) for p in labels];cost=metric.matrix(positions);index={v:i for i,v in enumerate(labels)}
    s=index[start];e=index[end] if end is not None else None
    remaining=set(range(len(labels)))-{s}
    if e is not None:remaining.discard(e)
    route=[s]
    while remaining:
        metric.check('nn');v=min(remaining,key=lambda v:(cost[route[-1]][v],v));route.append(v);remaining.remove(v)
    if e is not None and (e!=s or len(route)>1):route.append(e)
    def length(r):return sum(cost[a][b] for a,b in zip(r,r[1:]))
    initial=length(route);passes=0;improved=True
    while improved:
        improved=False;passes+=1;limit=len(route)-1 if e is not None else len(route)
        for i in range(1,limit-1):
            for j in range(i+1,limit):
                metric.check('2opt');a,b=route[i-1],route[i];c=route[j]
                old=cost[a][b];new=cost[a][c]
                if j+1<len(route):d=route[j+1];old+=cost[c][d];new+=cost[b][d]
                if new<old:route[i:j+1]=route[i:j+1][::-1];improved=True
    return [labels[i] for i in route],dict(initial_cost=initial,final_cost=length(route),passes=passes,terminal=end,point_count=len(labels))
