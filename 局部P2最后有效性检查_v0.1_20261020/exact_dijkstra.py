"""Separate state encoding: position plus frozenset of remaining tasks."""
import heapq,itertools,json,sys,time
def solve(c):
 started=time.perf_counter();F=frozenset(tuple(p) for p in c['free']);s=tuple(c['entry']);z=tuple(c['exit']);todo=frozenset(map(tuple,c['required']))-frozenset(map(tuple,c['local_H']))-{s};root=(s,todo);ticket=itertools.count();heap=[(0,next(ticket),root)];cost={root:0};prev={};closed=set();goal=None
 if len(F)*(1<<len(set(map(tuple,c['required']))-set(map(tuple,c['local_H']))))>2000000:return {'status':'unresolved','reason':'state_bound'}
 while heap:
  if time.perf_counter()-started>=60:return {'status':'unresolved','reason':'time','visited':len(cost)}
  value,_,state=heapq.heappop(heap)
  if state in closed or cost[state]!=value:continue
  closed.add(state);point,remaining=state
  if point==z and not remaining:goal=state;break
  for delta in ((0,-1),(-1,0),(0,1),(1,0)):
   q=(point[0]+delta[0],point[1]+delta[1])
   if q not in F:continue
   new=(q,remaining-{q});candidate=value+1
   if candidate<cost.get(new,float('inf')):cost[new]=candidate;prev[new]=state;heapq.heappush(heap,(candidate,next(ticket),new))
 if goal is None:return {'status':'infeasible','visited':len(cost)}
 path=[goal[0]];state=goal
 while state!=root:state=prev[state];path.append(state[0])
 path.reverse();return {'status':'optimal','length':cost[goal],'route':path,'visited':len(cost),'settled':len(closed),'seconds':time.perf_counter()-started,'proof':'Dijkstra settled accepting state at minimum queue cost; no shared search or planner routines.'}
if __name__=='__main__':
 with open(sys.argv[1],encoding='utf-8') as f:data=json.load(f)
 result=solve(data)
 with open(sys.argv[2],'x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
