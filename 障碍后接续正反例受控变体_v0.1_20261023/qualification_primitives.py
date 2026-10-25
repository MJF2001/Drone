from common import *
from fractions import Fraction as Q
from collections import deque,Counter
def near(a,b):return sum(abs(x-y) for x,y in zip(a,b))==1
def slab(a,b,cell):
 lo,hi=Q(0),Q(1)
 for v,w,c in zip(a,b,cell):
  d=w-v;left=Q(2*c-1,2);right=Q(2*c+1,2)
  if d==0:
   if not left<=v<=right:return None
  else:
   l,u=sorted(((left-v)/d,(right-v)/d));lo=max(lo,l);hi=min(hi,u)
   if lo>hi:return None
 mid=(lo+hi)/2;point=[Q(a[z])+mid*(b[z]-a[z]) for z in (0,1)]
 strict=lo<hi and all(abs(point[z]-cell[z])<Q(1,2) for z in (0,1))
 rat=lambda x:dict(n=x.numerator,d=x.denominator)
 return dict(lower=rat(lo),upper=rat(hi),midpoint=rat(mid),point=[rat(x) for x in point],strict_interior=strict)
def reachable(F,S,deadline,counts):
 counts['BFS_calls']+=1;parents={S:None};d={S:0};q=deque([S])
 while q:
  assert time.perf_counter()<deadline,'qualification_deadline'
  x,y=q.popleft();counts['BFS_popped']+=1
  for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   counts['BFS_neighbors']+=1
   if p in F and p not in d:d[p]=d[x,y]+1;parents[p]=(x,y);q.append(p)
 return d,parents
