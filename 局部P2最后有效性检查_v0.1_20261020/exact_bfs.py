"""Independent grid x task-bitmask BFS; no planner or Dijkstra imports."""
import json,sys,time
from collections import deque,Counter
def solve(c):
 begin=time.perf_counter();free=set(map(tuple,c['free']));tasks=sorted(set(map(tuple,c['required']))-set(map(tuple,c['local_H'])));idx={q:1<<i for i,q in enumerate(tasks)};full=(1<<len(tasks))-1;start=tuple(c['entry']);end=tuple(c['exit']);root=(start,idx.get(start,0));queue=deque([root]);dist={root:0};parent={root:None};layers=Counter();goal=None
 if len(free)*2**len(tasks)>c['state_limit']:return dict(status='unresolved',reason='state_bound')
 while queue:
  if time.perf_counter()-begin>=60:return dict(status='unresolved',reason='time',visited=len(dist))
  node=queue.popleft();p,mask=node;depth=dist[node];layers[depth]+=1
  if p==end and mask==full:goal=node;break
  x,y=p
  for q in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
   if q not in free:continue
   nxt=(q,mask|idx.get(q,0))
   if nxt not in dist:dist[nxt]=depth+1;parent[nxt]=node;queue.append(nxt)
 if goal is None:return dict(status='infeasible',visited=len(dist))
 route=[];node=goal
 while node is not None:route.append(node[0]);node=parent[node]
 route.reverse();return dict(status='optimal',length=dist[goal],route=route,visited=len(dist),popped=sum(layers.values()),depth_counts=dict(layers),frontier_min_depth=dist[queue[0]] if queue else None,seconds=time.perf_counter()-begin,proof='Unit-edge BFS first all-tasks-at-exit dequeue; all lower layers exhausted.')
if __name__=='__main__':
 c=json.loads(open(sys.argv[1],encoding='utf-8').read());r=solve(c)
 with open(sys.argv[2],'x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
