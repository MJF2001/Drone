"""Implementation optimisation: batched exact distances, legacy A* path ties.

    This is not a new coverage algorithm. In unlimited runs every legacy query
    receives the same distance and first-query-direction path as Geometry.
"""
from collections import deque
from model import Geometry,NoPath,adjacent


class BFSMetricGeometry(Geometry):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.distance_rows={}
        self.first_direction={}
        self.bfs_rows_built=0

    def distance(self,a,b):
        self.check_time()
        if a not in self.reachable or b not in self.reachable:
            raise NoPath('endpoint_unreachable')
        if (a,b) in self.cache:
            return len(self.cache[a,b])-1
        pair=(a,b) if a<=b else (b,a)
        self.first_direction.setdefault(pair,(a,b))
        if a==b:return 0
        if a in self.distance_rows:return self.distance_rows[a][b]
        if b in self.distance_rows:return self.distance_rows[b][a]
        ds={a:0};queue=deque([a])
        while queue:
            self.check_time()
            p=queue.popleft()
            for q in adjacent(p):
                if q in self.s.free and q not in ds:
                    ds[q]=ds[p]+1;queue.append(q)
        self.distance_rows[a]=ds
        self.bfs_rows_built+=1
        return ds[b]

    def path(self,a,b):
        self.check_time()
        if (a,b) in self.cache:return super().path(a,b)
        pair=(a,b) if a<=b else (b,a)
        first=self.first_direction.setdefault(pair,(a,b))
        # Legacy distance calls pre-populate symmetric paths. Materialise the
        # same first requested orientation lazily, preserving incidental cover.
        super().path(*first)
        return self.cache[a,b]
