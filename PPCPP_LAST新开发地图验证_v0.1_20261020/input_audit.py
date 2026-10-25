"""Direct coordinate predicates and history replay; no generator footprint imports."""
from common import *
from collections import deque
def reconstruct(slot,current=None,event=None):
 L=slot['L'];w=slot['w'];m=3;d=L//2;family=slot['family']
 W=(2*L if family=='Z' else L)+d+6;Y=(L if family!='I' else 0)+w+d+6
 f0={(x,y) for x in range(W) for y in range(Y)}
 old={(x,y) for x,y in f0 if 3<=x<3+L and 3<=y<3+w}
 if family in ('L','Z'):old|={(x,y) for x,y in f0 if 3+L-w<=x<3+L and 3+w<=y<3+w+L}
 if family=='Z':old|={(x,y) for x,y in f0 if 3+L<=x<3+2*L and 3+L<=y<3+L+w}
 extra=set();blocked=set();chosen=None
 if event=='straight':
  if family=='I':extra={(x,y) for x,y in f0 if 3+L<=x<3+L+d and 3<=y<3+w}
  elif family=='L':extra={(x,y) for x,y in f0 if 3+L-w<=x<3+L and 3+w+L<=y<3+w+L+d}
  else:extra={(x,y) for x,y in f0 if 3+2*L<=x<3+2*L+d and 3+L<=y<3+L+w}
 elif event=='corner':
  if family=='I':extra={(x,y) for x,y in f0 if 3+L-w<=x<3+L and 3+w<=y<3+w+d}
  elif family=='L':extra={(x,y) for x,y in f0 if 3+L<=x<3+L+d and 3+L<=y<3+L+w}
  else:extra={(x,y) for x,y in f0 if 3+2*L-w<=x<3+2*L and 3+L+w<=y<3+L+w+d}
 elif event=='obstacle':
  k=max(1,L//6);h=max(1,w//2);a={(x,y) for x,y in f0 if 3+L//2<=x<3+L//2+k and 3<=y<3+h};b={(x,y) for x,y in f0 if 3+L//2<=x<3+L//2+k and 3+w-h<=y<3+w}
  if current not in a:blocked=a;chosen=0
  elif current not in b:blocked=b;chosen=1
  else:chosen=None
 return f0,old,old|extra,blocked,chosen
def reachable(f,a):
 seen={a};q=deque([a])
 while q:
  x,y=q.popleft()
  for z in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   if z in f and z not in seen:seen.add(z);q.append(z)
 return seen
def check_path(f,path,start,end,targets=None):
 path=list(map(tuple,path));assert path and path[0]==start and path[-1]==end and set(path)<=f
 assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
 if targets is not None:assert targets<=set(path)
def audit_all():
 rows=[]
 for s in read(H/'protocol.json')['slots']:
  prep=read(H/'prep/results'/f"{s['base_id']}.json")
  if prep.get('technical_failure') or not prep.get('eligible'):
   rows.append(dict(**s,status='preparation_failed'));continue
  c0=read(H/'prep/inputs'/f"{s['base_id']}.json");pa.audit(c0,prep['raw']['branches']['P0']);f0,old,_,_,_=reconstruct(s)
  assert points(c0['free'])==f0 and points(c0['targets'])==old and not c0['covered'] and c0['current']==c0['base']==[0,0] and c0['previous'] is None
  c=read(H/'inputs'/f"{s['id']}.json");wtn=read(H/'witnesses'/f"{s['id']}.json");route=prep['raw']['route'];cut=wtn['cut'];prefix=route[:cut+1];h=points(prefix)&old;cur=tuple(prefix[-1]);goal=(len(old)*s['progress']+99)//100
  check_path(f0,prefix,(0,0),cur);assert len(h)==goal and len(points(prefix[:-1])&old)<goal and wtn['history']==prefix
  assert c['current']==prefix[-1] and c['previous']==prefix[-2] and c['old_route']==route[cut:]
  f0,old,pub,b,chosen=reconstruct(s,cur,s['event']);f=f0-b
  assert points(c['free'])==f and points(c['published_targets'])==pub and points(c['targets'])==pub&f and points(c['covered'])==h and points(c['initial_targets'])==old and points(c['deferred_targets'])==pub-f-h
  assert points(wtn['blocked'])==b and wtn['obstacle_choice']==chosen and c['base']==[0,0] and c['predator']==[-1,0] and c['distance_budget']==1000000
  assert len(f)<=10000 and len(pub)<=1500 and cur in f and (0,0) in f
  if s['event']!='obstacle':assert len(pub-old)==Lw(s)//2 and not (pub-old)&old
  assert pub&f<=reachable(f,cur)
  check_path(f,wtn['feasible_route'],cur,(0,0),(pub&f)-h);assert metric(c,wtn['feasible_route'])==cross(c,wtn['feasible_route'])
  rows.append(dict(**s,status='valid',free=len(f),published=len(pub),active=len(pub&f),history_targets=len(h),history_steps=cut,new_targets=len(pub-old),deferred=len(pub-f-h),blocked_completed=len(b&h),obstacle_choice=chosen,witness_steps=len(wtn['feasible_route'])-1))
 return rows
def Lw(s):return s['L']*s['w']
