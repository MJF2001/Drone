"""Offline-only memoization of unchanged independent BFS distances, scoped per input."""
from common import *
core=load('last_newdev_core_audit',H/'audit.py');uncached=core.bfs
class Audit:
 def __init__(self,c):
  self.free=points(c['free']);self.cache={};self.graphs={};self.c=c
 def bfs(self,f,a):
  # This input has exactly the original graph or a single reserved-cell graph.
  n=len(f)
  if n not in self.graphs:self.graphs[n]=frozenset(f)
  assert self.graphs[n]==f,'graph collision in offline audit cache'
  key=n,a
  if key not in self.cache:self.cache[key]=uncached(f,a)
  return self.cache[key]
 def check(self,x):
  core.bfs=self.bfs
  try:return core.check(self.c,x)
  finally:core.bfs=uncached
def gate():
 tested=0
 for f in ({(x,y) for x in range(4) for y in range(4)},{(x,y) for x in range(4) for y in range(4)}-{(1,1),(2,1)}):
  for p in sorted(f):
   for graph in (f,f-{min(f-{p})}):
    a=Audit(dict(free=sorted(f)))
    assert a.bfs(graph,p)==uncached(graph,p);assert a.bfs(graph,p)==uncached(graph,p);tested+=1
 return dict(passed=True,queries=tested,scope='offline distances only; production/core audit bytes unchanged')
