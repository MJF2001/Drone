"""Unit-edge BFS on the entire free graph; optional last-first-acquisition constraint."""
import time,gzip,json
from collections import deque
VERSION='GRID_MASK_BFS_v0.1'
def solve(free,start,base,targets,last=None,seconds=60,max_states=800000,clock=time.perf_counter,certificate=None):
 begin=clock();cells=sorted(free);ids={p:i for i,p in enumerate(cells)};n=len(cells);ts=sorted(targets);bits={p:1<<i for i,p in enumerate(ts)};full=(1<<len(ts))-1
 assert start in ids and base in ids and (last is None or last in targets)
 adj=[]
 for x,y in cells:adj.append([ids[z] for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if z in ids])
 initial=bits.get(start,0);lastbit=bits.get(last,0)
 invalid=last is not None and start==last and initial!=full
 key=initial*n+ids[start];records=[[key,-1,0]];seen={key:0};queue=deque([0]);expanded=0;peak=1;goal=None;reason='exhausted';status='infeasible'
 if invalid:queue.clear();reason='last_at_start_before_other_targets'
 while queue:
  if clock()-begin>=seconds:status='unresolved';reason='time_limit';break
  i=queue.popleft();state,_,d=records[i];mask,pos=divmod(state,n)
  if mask==full and cells[pos]==base:goal=i;status='optimal';reason='first_goal_dequeued';break
  expanded+=1
  for dest in adj[pos]:
   bit=bits.get(cells[dest],0)
   if lastbit and bit==lastbit and not mask&lastbit and (mask|lastbit)!=full:continue
   nxt=(mask|bit)*n+dest
   if nxt in seen:continue
   if len(records)>=max_states:status='unresolved';reason='state_limit';break
   seen[nxt]=len(records);records.append([nxt,i,d+1]);queue.append(len(records)-1)
  peak=max(peak,len(queue))
  if reason=='state_limit':break
 route=[]
 if goal is not None:
  k=goal
  while k!=-1:route.append(cells[records[k][0]%n]);k=records[k][1]
  route.reverse()
 result=dict(version=VERSION,status=status,reason=reason,length=len(route)-1 if route else None,route=route,discovered=len(records),expanded=expanded,queue_peak=peak,seconds=clock()-begin,limits=dict(seconds=seconds,states=max_states),start=start,base=base,targets=ts,last=last)
 if certificate:
  with gzip.open(certificate,'xt',encoding='utf-8') as f:json.dump(dict(cells=cells,records=records,expanded=expanded,goal=goal,invalid_start=invalid),f,separators=(',',':'))
 return result
