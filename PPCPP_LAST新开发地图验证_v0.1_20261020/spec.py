"""Deterministic public domains and continuous nonbranching road bands."""
from collections import deque
SIZES={'small':(6,2),'medium':(12,3),'large':(24,4)}
def rect(x,y,w,h):return {(a,b) for a in range(x,x+w) for b in range(y,y+h)}
def definition(size,family):
 L,w=SIZES[size];d=L//2;m=3
 initial=[(m,m,L,w)]
 if family in ('L','Z'):initial.append((m+L-w,m+w,w,L))
 if family=='Z':initial.append((m+L,m+L,L,w))
 if family=='I':straight=(m+L,m,d,w);corner=(m+L-w,m+w,w,d);domain=(m+L+d+m,m+w+d+m)
 elif family=='L':straight=(m+L-w,m+w+L,w,d);corner=(m+L,m+L,d,w);domain=(m+L+d+m,m+w+L+d+m)
 else:straight=(m+2*L,m+L,d,w);corner=(m+2*L-w,m+L+w,w,d);domain=(m+2*L+d+m,m+L+w+d+m)
 k=max(1,L//6);h=max(1,w//2);obstacles=[(m+L//2,m,k,h),(m+L//2,m+w-h,k,h)]
 return dict(size=size,family=family,L=L,w=w,extension_length=d,margin=m,domain=domain,initial_rectangles=initial,straight_rectangle=straight,corner_rectangle=corner,obstacle_rectangles=obstacles,Z_between_corner_straight=L-w if family=='Z' else None)
def union(rs):return set().union(*(rect(*r) for r in rs))
def before(d):return rect(0,0,*d['domain']),union(d['initial_rectangles'])
def after(d,event,current):
 f,t=before(d);b=set();chosen=None;valid=True
 if event=='obstacle':
  for i,r in enumerate(d['obstacle_rectangles']):
   block=rect(*r)
   if current not in block and (0,0) not in block and block<=t&f:b=block;chosen=i;break
  else:valid=False
  f-=b
 else:t|=rect(*d[event+'_rectangle'])
 return f,t,b,chosen,valid
def case(name,f,t,h,cur,initial,prev,old):return dict(name=name,free=sorted(f),targets=sorted(t&f),covered=sorted(h),published_targets=sorted(t),deferred_targets=sorted(t-f-h),current=cur,base=(0,0),previous=prev,predator=(-1,0),initial_targets=sorted(initial),old_route=old,distance_budget=1000000)
def feasible(c):
 f=set(map(tuple,c['free']));todo=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])};route=[tuple(c['current'])];base=tuple(c['base'])
 for goal in sorted(todo,key=lambda q:(q[1],q[0]))+[base]:
  if goal!=base and goal not in todo:continue
  if abs(route[-1][0]-goal[0])+abs(route[-1][1]-goal[1])==1:seg=[route[-1],goal]
  else:
   parent={route[-1]:None};q=deque([route[-1]])
   while q and goal not in parent:
    x,y=q.popleft()
    for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
     if z in f and z not in parent:parent[z]=(x,y);q.append(z)
   if goal not in parent:return None
   seg=[goal]
   while parent[seg[-1]] is not None:seg.append(parent[seg[-1]])
   seg.reverse()
  route+=seg[1:];todo-=set(seg)
 return route if not todo else None
