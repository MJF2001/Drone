from collections import deque
def rect(x,y,w,h):return {(a,b) for a in range(x,x+w) for b in range(y,y+h)}
def geometry(scale,shape,event=None,current=None):
 w=1 if scale=='s1' else 2
 f=rect(0,0,7 if w==1 else 8,6);t=rect(1,1,4,w)
 if shape=='L':t|=rect(5-w,1+w,w,2)
 blocked=set()
 if event=='straight':t|=rect(5,1,2,w) if shape=='I' else rect(5-w,3+w,w,2 if w==1 else 1)
 elif event=='corner':t|=rect(5-w,1+w,w,2) if shape=='I' else rect(3-w,1+w,w,2)
 elif event=='obstacle':
  b=next(q for q in ((3,1),(4,1)) if q!=current);blocked={b};f-=blocked
 return f,t,blocked
def case(name,f,pub,h,cur,initial,prev,old):
 return dict(name=name,free=sorted(f),targets=sorted(pub&f),published_targets=sorted(pub),covered=sorted(h),deferred_targets=sorted(pub-f-h),current=cur,base=(0,0),initial_targets=sorted(initial),previous=prev,predator=(-1,0),old_route=old,distance_budget=1000000)
def witness(f,t,h,cur,base=(0,0)):
 route=[cur];todo=t-h-{cur}
 for goal in sorted(todo)+[base]:
  if goal!=base and goal not in todo:continue
  parents={route[-1]:None};q=deque([route[-1]])
  while q and goal not in parents:
   x,y=q.popleft()
   for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if z in f and z not in parents:parents[z]=(x,y);q.append(z)
  assert goal in parents
  seg=[goal]
  while parents[seg[-1]] is not None:seg.append(parents[seg[-1]])
  route+=seg[::-1][1:];todo-=set(seg)
 assert not todo;return route
