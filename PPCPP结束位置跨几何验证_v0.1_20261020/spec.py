"""Explicit disjoint new rectangles extending a continuous, unbranched band."""
from collections import deque
def rect(x,y,w,h):return {(a,b) for a in range(x,x+w) for b in range(y,y+h)}
def plans():
 return [dict(base_id=f'{scale}_{family}',scale=scale,family=family) for family in ('I','L','Z') for scale in ('narrow','wide')]
def definition(scale,family):
 narrow=scale=='narrow'
 if narrow:
  initial={'I':[(1,2,3,1)],'L':[(1,2,3,1),(3,3,1,2)],'Z':[(1,1,2,1),(2,2,1,2),(3,3,2,1)]}[family]
  straight={'I':[(4,2,2,1)],'L':[(3,5,1,1)],'Z':[(5,3,2,1)]}[family]
  corner={'I':[(3,3,1,2)],'L':[(4,4,2,1)],'Z':[(4,4,1,2)]}[family]
  obstacles={'I':[(2,2),(3,2)],'L':[(3,3),(3,4)],'Z':[(2,2),(3,3)]}[family]
 else:
  initial={'I':[(1,1,3,2)],'L':[(1,1,3,2),(2,3,2,1)],'Z':[(1,1,3,2),(2,3,2,1),(4,2,2,2)]}[family]
  straight={'I':[(4,1,2,2)],'L':[(2,4,2,2)],'Z':[(6,2,1,2)]}[family]
  corner={'I':[(2,3,2,2)],'L':[(4,2,2,2)],'Z':[(4,4,2,2)]}[family]
  obstacles={'I':[(2,1),(3,2)],'L':[(2,3),(3,3)],'Z':[(3,3),(4,3)]}[family]
 return dict(domain=(7 if narrow else 8,6),width=1 if narrow else 2,initial_rectangles=initial,straight_rectangles=straight,corner_rectangles=corner,obstacle_candidates=obstacles)
def cells(rectangles):return set().union(*(rect(*r) for r in rectangles))
def before(scale,family):
 d=definition(scale,family);return rect(0,0,*d['domain']),cells(d['initial_rectangles'])
def after(scale,family,event,current):
 d=definition(scale,family);f,t=before(scale,family);b=set();valid=True
 if event=='obstacle':
  eligible=[tuple(q) for q in d['obstacle_candidates'] if tuple(q)!=current and tuple(q)!=(0,0) and tuple(q) in f&t]
  if eligible:b={eligible[0]};f-=b
  else:valid=False
 else:t|=cells(d[event+'_rectangles'])
 return f,t,b,valid
def make_case(name,f,pub,h,cur,initial,prev,old):
 return dict(name=name,free=sorted(f),targets=sorted(pub&f),published_targets=sorted(pub),covered=sorted(h),deferred_targets=sorted(pub-f-h),current=cur,base=(0,0),initial_targets=sorted(initial),previous=prev,predator=(-1,0),old_route=old,distance_budget=1000000)
def distances(f,base):
 d={base:0};q=deque([base])
 while q:
  x,y=q.popleft()
  for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   if z in f and z not in d:d[z]=d[x,y]+1;q.append(z)
 return d
def nearest(c):
 f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])};d=distances(f,tuple(c['base']))
 if not t:return dict(emin=None,distances={})
 if not t<=d.keys():return dict(emin=None,reason='unreachable_pending',distances={str(q):d.get(q) for q in sorted(t)})
 e=min(t,key=lambda q:(d[q],q));return dict(emin=e,distances={str(q):d[q] for q in sorted(t)})
def feasible(c):
 f=set(map(tuple,c['free']));todo=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])};route=[tuple(c['current'])]
 for goal in sorted(todo)+[tuple(c['base'])]:
  if goal!=tuple(c['base']) and goal not in todo:continue
  parent={route[-1]:None};q=deque([route[-1]])
  while q and goal not in parent:
   x,y=q.popleft()
   for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if z in f and z not in parent:parent[z]=(x,y);q.append(z)
  if goal not in parent:return None
  segment=[goal]
  while parent[segment[-1]] is not None:segment.append(parent[segment[-1]])
  route+=segment[::-1][1:];todo-=set(segment)
 return route if not todo else None
