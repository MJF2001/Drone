"""Persistent RCG: III-B2/3 expansion, essential rules and link nodes."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import heapq
import math
from geometry import dist,lap_points

@dataclass
class Node:
    state: str = 'Op'
    kind: str = 'frontier'
    reason: str = ''

class RCG:
    def __init__(self,known):
        self.map=known
        self.nodes={}
        self.edges={}
        self.sampled=set()
        self.processed=set()
        self.total_added=0
        self.total_pruned=0
        self.link_count=0

    def insert(self,p,kind='frontier',state='Op'):
        if p in self.nodes:
            return
        self.nodes[p]=Node(state,kind)
        self.edges[p]={}
        self.sampled.add(p)
        self.total_added+=1
        if kind=='link':
            self.link_count+=1

    def connect(self,a,b):
        if a!=b and self.map.feasible(a,b):
            self.edges[a][b]=self.edges[b][a]=dist(a,b)

    def remove_edge(self,a,b):
        self.edges[a].pop(b,None)
        self.edges[b].pop(a,None)

    def expand(self,new):
        """Only affected columns and edges incident to new nodes are expanded."""
        new=set(new)
        columns={p[0] for p in new}
        by_col=defaultdict(list)
        for p in self.nodes:
            if p[0] in columns:
                by_col[p[0]].append(p)
        for nodes in by_col.values():
            nodes.sort(key=lambda p:p[1])
            # Split old long vertical edge when a new node lies inside it.
            for p in nodes:
                for q in list(self.edges[p]):
                    if p[0]==q[0]:
                        self.remove_edge(p,q)
            for a,b in zip(nodes,nodes[1:]):
                self.connect(a,b)
        for p in sorted(new):
            for dx in (-1,1):
                for dy in (-1,0,1):
                    q=(p[0]+dx,p[1]+dy)
                    if q in self.nodes:
                        self.connect(p,q)

    def sample_front(self,start=None):
        # Sample positions are a w-spaced integer lattice, anchored at p0.
        # Iterating all candidates is equivalent to the minimum integer delta.
        new={p for p in self.map.new_free if p not in self.sampled and self.map.frontier(p)}
        if start is not None:
            new.add(start)
        for p in sorted(new):
            self.insert(p)
        # Discovery may bridge two old partial laps even if the newly exposed
        # interior candidates are not frontier samples. Re-evaluate those laps.
        changed_columns={p[0] for p in self.map.new_free}
        affected=new|{p for p in self.nodes if p[0] in changed_columns}
        self.expand(affected)
        self.processed.update(self.map.new_free)
        self.map.new_free.clear()
        return new

    def essential(self):
        ends={p for p in self.nodes if self.map.endpoint(p)}
        reasons={p:('unknown' if self.map.unknown_adjacent(p) else 'lap_end')
                 for p in self.nodes if p in ends or self.map.unknown_adjacent(p)}
        transitions=set()
        for p in sorted(ends):
            groups=defaultdict(list)
            for q in self.edges[p]:
                if p[0]!=q[0]:
                    groups[q[0]].append(q)
            for candidates in groups.values():
                end_neighbors=[q for q in candidates if q in ends]
                if end_neighbors:
                    chosen=end_neighbors  # III.9 2a
                elif len(candidates)==1:
                    chosen=candidates    # III.8 3a / III.9 2b-i
                else:
                    chosen=[min(candidates,key=lambda q:self.map.clearance_score(p,q))]
                for q in chosen:
                    reasons.setdefault(q,'end_connector')
                    transitions.add(tuple(sorted((p,q))))
        return reasons,transitions

    def prune(self,current):
        """Def. III.8/9, retaining current and open link nodes as execution anchors.

        Full classification pass is intentional: reference implementation does
        not claim the paper's frontier-local complexity. Graph is not rebuilt.
        """
        reasons,transitions=self.essential()
        reasons[current]='current_anchor'
        for p,n in self.nodes.items():
            if n.kind in ('link','tsp') and n.state=='Op':
                reasons.setdefault(p,n.kind)
        for p in sorted(set(self.nodes)-set(reasons)):
            vertical=[q for q in self.edges[p] if q[0]==p[0]]
            if len(vertical)==2:
                self.connect(*vertical)
            for q in list(self.edges[p]):
                self.remove_edge(p,q)
            del self.nodes[p],self.edges[p]
            self.total_pruned+=1
        for p in self.nodes:
            self.nodes[p].reason=reasons[p]
        for p in sorted(self.nodes):
            for q in list(self.edges[p]):
                if p[0]!=q[0] and tuple(sorted((p,q))) not in transitions:
                    # Preserve execution-anchor edges during the current action.
                    protected=lambda n:self.nodes[n].kind in ('link','tsp') and self.is_open(n)
                    if p!=current and q!=current and not protected(p) and not protected(q):
                        self.remove_edge(p,q)

    def vertical(self,p):
        up=next((q for q in self.edges[p] if q[0]==p[0] and q[1]>p[1]),None)
        down=next((q for q in self.edges[p] if q[0]==p[0] and q[1]<p[1]),None)
        return up,down

    def is_open(self,p):
        return p in self.nodes and self.nodes[p].state=='Op'

    def update_state(self,current,goal):
        """Alg.2 with explicit interpretation of missing vertical neighbors.

        prose: close unless both vertical neighbors are Op (III-B4b, Lemma IV.6).
        literal: line 2, absent neighbor treated Closed, otherwise unchanged.
        For the binary state domain these two forms agree.
        """
        up,down=self.vertical(current)
        if not (self.is_open(up) and self.is_open(down)):
            self.nodes[current].state='Cl'
        if goal[0]<current[0] and not self.is_open(current):
            new=[]
            for q in (up,down):
                if self.is_open(q):
                    p=(current[0],current[1]+(1 if q[1]>current[1] else -1))
                    if p not in self.nodes:
                        self.insert(p,'link')
                        new.append(p)
                    else:
                        # An existing sample at exactly w is the same link
                        # anchor; do not let the next pruning pass erase it.
                        self.nodes[p].kind='link'
            self.expand(new)

    def path(self,start,goal):
        """Euclidean A* on the actual RCG, not an occupancy-grid fallback."""
        queue=[(dist(start,goal),0.,start)]
        costs,parent={start:0.},{}
        while queue:
            _,g,p=heapq.heappop(queue)
            if g>costs[p]+1e-9:
                continue
            if p==goal:
                result=[p]
                while p!=start:
                    p=parent[p]
                    result.append(p)
                return result[::-1],costs[goal]
            for q,w in sorted(self.edges[p].items()):
                ng=g+w
                if ng<costs.get(q,math.inf)-1e-9:
                    costs[q],parent[q]=ng,p
                    heapq.heappush(queue,(ng+dist(q,goal),ng,q))
        raise ValueError(f'RCG disconnected: {start} -> {goal}')

    def validate(self,current):
        assert current in self.nodes
        seen,todo={current},[current]
        while todo:
            p=todo.pop()
            assert p not in self.edges[p]
            for q,w in self.edges[p].items():
                assert q in self.nodes and self.edges[q].get(p)==w
                assert self.map.feasible(p,q),f'Invalid edge {p,q}'
                if q not in seen:
                    seen.add(q);todo.append(q)
        if seen!=set(self.nodes):
            raise ValueError(f'RCG lost connectivity: {len(seen)}/{len(self.nodes)}; isolated {sorted(set(self.nodes)-seen)[:8]}')
