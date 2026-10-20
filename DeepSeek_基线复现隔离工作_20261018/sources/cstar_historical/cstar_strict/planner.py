"""C* algorithms 1--4, with explicit paper ambiguities documented in SPEC.md."""
from __future__ import annotations
import math
import random
from geometry import KnownMap,dist,lap_points,point_segment_distance
from rcg import RCG

def optimize_tsp(points,start,end,cost):
    """Fixed-start nearest neighbor then exhaustive improving 2-opt.

    A free end is optimized directly, not via the infeasible dummy-node case.
    """
    remaining=set(points)-{start}
    if end is not None:
        remaining.discard(end)
    route=[start]
    while remaining:
        q=min(remaining,key=lambda p:(cost[route[-1],p],p))
        route.append(q);remaining.remove(q)
    if end is not None and (len(route)>1 or end!=start):
        route.append(end)
    def length(seq):
        return sum(cost[a,b] for a,b in zip(seq,seq[1:]))
    before=length(route)
    improved=True
    while improved:
        improved=False
        stop=len(route)-1 if end is not None else len(route)
        for i in range(1,stop-1):
            for j in range(i+1,stop):
                old=cost[route[i-1],route[i]]
                new=cost[route[i-1],route[j]]
                if j+1<len(route):
                    old+=cost[route[j],route[j+1]]
                    new+=cost[route[i],route[j+1]]
                if new<old-1e-9:
                    route[i:j+1]=reversed(route[i:j+1]);improved=True
    return route,before,length(route)

class CStar:
    def __init__(self,start,observe,seed=0,holes=True):
        self.map=KnownMap()
        self.graph=RCG(self.map)
        self.current=start
        self.observe=observe
        self.rng=random.Random(seed)
        self.holes_enabled=holes
        self.path=[start]
        self.modes=['start']
        self.observations=[]
        self.retreat=set()
        self.events=[]
        self.history=[]
        self.retreat_count=0
        self.keep_open_count=0
        self.sense(start)
        self.graph.sample_front(start)
        self.status='running'

    def sense(self,p):
        fresh=self.map.update(self.observe(p))
        self.observations.append([[x,y,int(v)] for (x,y),v in sorted(fresh.items())])

    def refresh_retreat(self,a=None,b=None):
        self.retreat={p for p in self.retreat if self.graph.is_open(p)}
        if a is None:
            a=b=self.current
        for p in self.graph.nodes:
            if self.graph.is_open(p) and point_segment_distance(p,a,b)<=math.sqrt(2)+1e-9:
                self.retreat.add(p)

    def register_new_retreats(self,new):
        # New frontier/link points can lie beside the just-traversed segment,
        # although the robot has already left it when the graph is expanded.
        segments=list(zip(self.path,self.path[1:])) or [(self.current,self.current)]
        for p in new:
            if self.graph.is_open(p) and any(point_segment_distance(p,a,b)<=math.sqrt(2)+1e-9 for a,b in segments):
                self.retreat.add(p)

    def navigate(self,route,mode):
        assert route[0]==self.current
        for a,b in zip(route,route[1:]):
            assert b in self.graph.edges[a],f'Motion outside RCG: {a,b}'
            assert self.map.feasible(a,b),'Motion through unknown/obstacle'
            self.refresh_retreat(a,b)
            # Continuous segment; sensing sampled at <= w/2 intervals.
            steps=max(1,math.ceil(dist(a,b)*2))
            for k in range(1,steps+1):
                t=k/steps
                p=(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
                self.path.append(p);self.modes.append(mode)
                self.sense(p)
            self.current=b

    def select_goal(self):
        p=self.current
        opened=[q for q in self.graph.edges[p] if self.graph.is_open(q)]
        groups=[sorted(q for q in opened if q[0]<p[0]),
                sorted(q for q in opened if q[0]==p[0] and q[1]>p[1]),
                sorted(q for q in opened if q[0]==p[0] and q[1]<p[1]),
                sorted(q for q in opened if q[0]>p[0])]
        for group in groups:
            if group:
                goal=self.rng.choice(group)
                return goal,[p,goal],False
        self.refresh_retreat()
        candidates=sorted(self.retreat-{p})
        if candidates:
            routes=[self.graph.path(p,q) for q in candidates]
            route,_=min(routes,key=lambda pair:(pair[1],pair[0][-1]))
            return route[-1],route,True
        others=[q for q in self.graph.nodes if q!=p and self.graph.is_open(q)]
        if others:
            raise ValueError(f'Open graph but no retreat nodes: {others[:5]}')
        self.graph.nodes[p].state='Cl'
        return None,None,False

    def detect_holes(self,goal):
        candidates={p for p in self.graph.nodes if self.graph.is_open(p)}-{self.current,goal}
        checked,holes=set(),set()
        for start in sorted(set(self.graph.edges[self.current]) & candidates):
            if start in checked:
                continue
            comp,stack={start},[start]
            while stack:
                p=stack.pop()
                for q in self.graph.edges[p]:
                    if q in candidates and q not in comp:
                        comp.add(q);stack.append(q)
            checked.update(comp)
            if not any(self.map.unknown_adjacent(p) for p in comp):
                holes.update(comp)
        return holes

    def densify(self,holes,goal):
        points=set(holes)|{self.current,goal}
        additions=set()
        for p in points:
            for q in self.graph.edges[p]:
                if p[0]==q[0] and q in points:
                    additions.update(lap_points(p,q))
        new=additions-set(self.graph.nodes)
        for p in sorted(new):
            self.graph.insert(p,'tsp')
        self.graph.expand(new)
        return points|additions

    def cover_holes(self,holes,goal):
        start=self.current
        points=self.densify(holes,goal)
        open_outside=lambda p:any(self.graph.is_open(q) and q not in points for q in self.graph.edges[p])
        retain_start=self.graph.is_open(start) and open_outside(start)
        if open_outside(goal) or self.map.unknown_adjacent(goal):
            end,case=goal,1
        elif open_outside(start):
            end,case=start,2
        else:
            end,case=None,3
        paths,costs={},{}
        for a in sorted(points):
            for b in sorted(points):
                if (a,b) in paths:
                    continue
                path,cost=self.graph.path(a,b)
                paths[a,b]=path;paths[b,a]=path[::-1]
                costs[a,b]=costs[b,a]=cost
        order,before,after=optimize_tsp(points,start,end,costs)
        self.events.append(dict(type='tsp',step=len(self.path)-1,case=case,
                               targets=len(points),nn_length=before,opt_length=after,
                               hole_nodes=sorted(holes),dense_nodes=sorted(points),order=order))
        for a,b in zip(order,order[1:]):
            route=paths[a,b]
            self.navigate(route,'tsp')
        for p in points:
            self.graph.nodes[p].state='Cl'
        # Do not erase unresolved lap obligations at the entry and exit.
        # The exit has been reached but not yet processed by Algorithm 2.
        if retain_start:
            self.graph.nodes[start].state='Op'
        self.graph.nodes[self.current].state='Op'
        self.refresh_retreat()

    def snapshot(self,iteration):
        self.history.append(dict(iteration=iteration,step=len(self.path)-1,
                                 nodes=[[p[0],p[1],n.state,n.kind,n.reason] for p,n in sorted(self.graph.nodes.items())],
                                 edges=[[p,q] for p in sorted(self.graph.edges) for q in sorted(self.graph.edges[p]) if p<q],
                                 known=len(self.map.free),retreat=len(self.retreat)))

    def run(self,max_iterations=5000):
        try:
            for i in range(max_iterations):
                new=self.graph.sample_front()
                self.register_new_retreats(new)
                self.graph.prune(self.current)
                self.graph.validate(self.current)
                self.refresh_retreat()
                self.snapshot(i)
                goal,route,is_retreat=self.select_goal()
                if goal is None:
                    self.status='graph_exhausted'
                    break
                self.graph.update_state(self.current,goal)
                if self.graph.is_open(self.current):
                    self.keep_open_count+=1
                holes=self.detect_holes(goal) if self.holes_enabled else set()
                if holes:
                    self.cover_holes(holes,goal)
                else:
                    if is_retreat:
                        self.retreat_count+=1
                        self.events.append(dict(type='retreat',step=len(self.path)-1,goal=goal))
                    # link insertion might split the originally selected edge.
                    if not is_retreat and goal not in self.graph.edges[self.current]:
                        route,_=self.graph.path(self.current,goal)
                    self.navigate(route,'retreat' if is_retreat else 'sweep')
            else:
                self.status='iteration_limit'
        except (ValueError,AssertionError) as error:
            import traceback
            self.status='invariant_failure'
            self.error=traceback.format_exc()
        return self
