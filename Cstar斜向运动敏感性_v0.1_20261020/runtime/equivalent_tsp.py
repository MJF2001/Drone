"""Accelerate comparisons, never replace a canonical execution path.

Euclidean positive RCG edges, original A* epsilon=1e-9. A conservative
distance envelope covers per-edge epsilon suppression, summation rounding and
Euclidean heuristic rounding. Uncertain NN and 2-opt comparisons use ORIGINAL
canonical A* values. No altered tie convention or rounded distance is used.
"""
import heapq, math

class CertifiedCosts:
    def __init__(self,graph,points,check):
        self.graph=graph;self.points=sorted(points);self.check=check
        self.exact={};self.paths={};self.rows={}
        self.stats=dict(rows=0,exact_queries=0,nn_certified=0,nn_resolved=0,opt_certified=0,opt_resolved=0)
        self.adj={p:tuple(sorted(v.items())) for p,v in graph.edges.items()}
        n=max(1,len(self.adj));maxw=1.;lattice=True
        for p,edges in self.adj.items():
            for q,w in edges:
                if not math.isfinite(w) or w<=0 or w!=math.hypot(p[0]-q[0],p[1]-q[1]) or graph.edges[q].get(p)!=w:
                    raise ValueError('certified costs require the original positive undirected Euclidean RCG')
                maxw=max(maxw,w)
                lattice=lattice and (w.is_integer() or w==math.sqrt(2))
        # Even n accumulated epsilon suppressions and roundoff remain well
        # inside this envelope. No assumption that floats with equal analytic
        # distance are bitwise equal is made.
        self.bound=n*(1e-7+128*math.ulp(n*maxw))
        self.n=n
        # In this RCG every path length is A+B*sqrt(2), A,B integers.
        # Distinct lengths <=M differ by >=1/(4M) (integer algebraic norm).
        # If that gap safely exceeds float/epsilon search error, A* cannot
        # discard a genuinely shorter label; only equal analytic lengths can
        # have different summation roundoff. Otherwise retain the loose bound.
        self.tight=False
        self.stats.update(nodes=n,points=len(self.points),distance_bound=self.bound)
        for start in self.points:
            check('tsp_costs');row={start:0.};queue=[(0.,start)]
            while queue:
                check('tsp_row_search');g,p=heapq.heappop(queue)
                if g!=row[p]:continue
                for q,w in self.adj[p]:
                    ng=g+w
                    if ng<row.get(q,math.inf):row[q]=ng;heapq.heappush(queue,(ng,q))
            if not set(self.points)<=row.keys():raise ValueError('RCG disconnected in hole cost preparation')
            self.rows[start]=row;self.stats['rows']+=1
        anchor=self.rows[self.points[0]]
        # A connected anchor tree gives a <=2R route between any two nodes;
        # 4R+max-edge+1 safely bounds relevant search labels with slack, instead
        # of the useless n*max-edge bound on an arbitrary long simple path.
        M=max(1.,4*max(anchor.values())+maxw+1.)
        self.tight=lattice and len(anchor)==n and 1/(8*M)>32*n*math.ulp(M)+4e-9
        self.stats.update(tight_lattice_bound=self.tight,search_label_bound=M)
    def approx(self,a,b):
        # Match the historical upper-triangular orientation, not the row from
        # whichever endpoint happened to ask first.
        a,b=sorted((a,b));return self.rows[a][b]
    def error(self,a,b):
        if not self.tight:return self.bound
        d=self.approx(a,b)
        # All edges >=1; each simple path has <=min(n-1,ceil(d)) edges.
        # Bound the difference of two positive summations of the SAME analytic
        # lattice length, plus conservative rounding slack.
        return 2*min(self.n,math.ceil(d)+1)*math.ulp(d+1.)
    def value(self,a,b):
        a,b=sorted((a,b));key=a,b
        if key not in self.exact:
            self.check('tsp_exact');path,cost=self.graph.path(a,b)
            assert abs(cost-self.approx(a,b))<=self.error(a,b),'distance certificate violated'
            self.exact[key]=cost;self.paths[key]=path;self.stats['exact_queries']+=1
        return self.exact[key]
    def path(self,a,b):
        self.check('tsp_path_restore');self.value(a,b)
        lo,hi=sorted((a,b));p=self.paths[lo,hi];return p if a==lo else p[::-1]
    def nearest(self,a,remaining):
        upper=min(self.approx(a,b)+self.error(a,b) for b in remaining)
        contenders=[b for b in remaining if self.approx(a,b)-self.error(a,b)<=upper]
        if len(contenders)==1:self.stats['nn_certified']+=1;return contenders[0]
        self.check('tsp_nn_resolve');self.stats['nn_resolved']+=1
        return min(contenders,key=lambda b:(self.value(a,b),b))
    def improves(self,route,i,j):
        pairs=[(route[i-1],route[i]),(route[i-1],route[j])]
        if j+1<len(route):pairs.extend([(route[j],route[j+1]),(route[i],route[j+1])])
        old=self.approx(*pairs[0]);new=self.approx(*pairs[1])
        if len(pairs)==4:old+=self.approx(*pairs[2]);new+=self.approx(*pairs[3])
        # Covers both the four distance envelopes and comparison arithmetic.
        margin=sum(self.error(*p) for p in pairs)+16*math.ulp(max(abs(old),abs(new),1.))
        if abs((new-old)+1e-9)>margin:
            self.stats['opt_certified']+=1;return new<old-1e-9
        self.check('tsp_2opt_resolve');self.stats['opt_resolved']+=1
        old=self.value(*pairs[0]);new=self.value(*pairs[1])
        if len(pairs)==4:old+=self.value(*pairs[2]);new+=self.value(*pairs[3])
        return new<old-1e-9

def optimize_equivalent(points,start,end,cost,check):
    remaining=set(points)-{start}
    if end is not None:remaining.discard(end)
    route=[start]
    while remaining:
        check('tsp_nn');q=cost.nearest(route[-1],remaining);route.append(q);remaining.remove(q)
    if end is not None and (len(route)>1 or end!=start):route.append(end)
    length=lambda seq:sum(cost.value(a,b) for a,b in zip(seq,seq[1:]))
    before=length(route);improved=True
    while improved:
        improved=False;stop=len(route)-1 if end is not None else len(route)
        for i in range(1,stop-1):
            for j in range(i+1,stop):
                check('tsp_2opt')
                if cost.improves(route,i,j):route[i:j+1]=reversed(route[i:j+1]);improved=True
    return route,before,length(route)

def equivalent_cover_holes(self,holes,goal):
    start=self.current;points=self.densify(holes,goal)
    def open_outside(p):return any(self.graph.is_open(q) and q not in points for q in self.graph.edges[p])
    retain_start=self.graph.is_open(start) and open_outside(start)
    if open_outside(goal) or self.map.unknown_adjacent(goal):end,case=goal,1
    elif open_outside(start):end,case=start,2
    else:end,case=None,3
    costs=CertifiedCosts(self.graph,points,self._check_deadline)
    order,before,after=optimize_equivalent(points,start,end,costs,self._check_deadline)
    # Recover before navigating so later state changes cannot affect even a
    # hypothetical future path implementation. Canonical orientation matches
    # the original full upper-triangular cache, including reversed legs.
    paths={(a,b):costs.path(a,b) for a,b in zip(order,order[1:])}
    event=dict(type='tsp',step=len(self.path)-1,case=case,targets=len(points),nn_length=before,opt_length=after,
        hole_nodes=[list(p) for p in sorted(holes)],dense_nodes=[list(p) for p in sorted(points)],
        order=[list(p) for p in order],end=list(end) if end is not None else None,
        start=list(start),goal=list(goal),graph_before_tour=self.graph.snapshot())
    self.events.append(event)
    self.efficiency_stats=getattr(self,'efficiency_stats',[]);self.efficiency_stats.append(costs.stats)
    moved=0;self._fixed_tour=True
    try:
        for a,b in zip(order,order[1:]):moved+=self.navigate(paths[a,b],'tsp')
    finally:self._fixed_tour=False
    for p in points:self.graph.nodes[p].state='Cl'
    if retain_start:self.graph.nodes[start].state='Op'
    self.graph.nodes[self.current].state='Op';self.refresh_retreat();event['moved_steps']=moved
    return event
