"""Diagnostic 8-neighbour motion; not the frozen common four-neighbour model."""
import heapq,math
from common_geometry import NoPath
def length(path):return sum(math.hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(path,path[1:]))
def legal_step(a,b,free):
    dx=b[0]-a[0];dy=b[1]-a[1]
    return a in free and b in free and max(abs(dx),abs(dy))==1 and (not(dx and dy) or ((a[0],b[1]) in free and (b[0],a[1]) in free))
class DiagonalMetric:
    def __init__(self,free,checkpoint=None):self.free=frozenset(free);self.check=checkpoint or (lambda _:None);self.cache={}
    def path(self,a,b):
        self.check('diagonal_path');a,b=tuple(a),tuple(b)
        if a not in self.free or b not in self.free:raise NoPath('diagonal endpoint')
        if a==b:return (a,)
        lo,hi=sorted((a,b));key=lo,hi
        if key not in self.cache:
            direct=None
            if lo[0]==hi[0] or lo[1]==hi[1]:
                dx=(hi[0]>lo[0])-(hi[0]<lo[0]);dy=(hi[1]>lo[1])-(hi[1]<lo[1]);n=abs(hi[0]-lo[0])+abs(hi[1]-lo[1]);seq=[]
                for i in range(n+1):
                    self.check('diagonal_direct');p=lo[0]+dx*i,lo[1]+dy*i
                    if p not in self.free:break
                    seq.append(p)
                if len(seq)==n+1:direct=tuple(seq)
            elif legal_step(lo,hi,self.free):
                self.check('diagonal_direct');direct=(lo,hi)
            if direct is None:
                costs={lo:0.};parent={};queue=[(0.,lo)]
                while queue:
                    self.check('diagonal_search');d,p=heapq.heappop(queue)
                    if d!=costs[p]:continue
                    if p==hi:break
                    for dx in (-1,0,1):
                        for dy in (-1,0,1):
                            q=p[0]+dx,p[1]+dy
                            if legal_step(p,q,self.free):
                                nd=d+math.hypot(dx,dy)
                                if nd<costs.get(q,math.inf):costs[q]=nd;parent[q]=p;heapq.heappush(queue,(nd,q))
                else:raise NoPath('diagonal disconnected')
                reverse=[hi]
                while reverse[-1]!=lo:self.check('diagonal_reconstruct');reverse.append(parent[reverse[-1]])
                direct=tuple(reversed(reverse))
            self.cache[key]=direct
        path=self.cache[key];return path if a==lo else path[::-1]
