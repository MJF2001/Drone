"""Independent original reward/BFS replay and independent old-order trigger check.
No imports of native planner, hook, reward function or geometry implementation.
"""
import math,time
from collections import Counter,deque
from common import norm,ps
def audit(c,raw,old,arm,diag,scanner=None):
 start=time.perf_counter();deadline=start+150;counts=Counter();receipts=[];trigger=None;examined=False
 path=list(map(tuple,raw['route']));events=raw['trace'];F=ps(c['free']);T=ps(c['targets']);HH=ps(c['covered']);pending=T-HH-{tuple(c['current'])};cursor=0;applied=0
 assert len(path)-1<=4096 and len(events)<=4097
 assert path[0]==tuple(c['current']) and path[-1]==tuple(c['base']) and set(path)<=F and T<=HH|set(path)
 assert len(path)-1<=c['distance_budget'] and raw['status']=='core_complete' and raw['accepted_seconds']<raw['budget'] and not raw['fallback_selected']
 def bfs(a):
  counts['BFS_calls']+=1;d={a:0};q=deque([a])
  while q:
   assert time.perf_counter()<deadline,'independent_deadline'
   x,y=q.popleft();counts['BFS_popped']+=1
   for b in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    counts['BFS_neighbors']+=1
    if b in F and b not in d:d[b]=d[x,y]+1;q.append(b)
  return d
 for a,b in zip(path,path[1:]):assert sum(abs(x-y) for x,y in zip(a,b))==1;counts['unit_edges']+=1
 for i,e in enumerate(events):
  assert time.perf_counter()<deadline,'independent_deadline'
  counts['decisions']+=1;x,y=path[cursor];prev=path[cursor-1] if cursor else (tuple(c['previous']) if c['previous'] is not None else None)
  assert e['index']==cursor and tuple(e['current'])==(x,y) and e['pending_count']==len(pending)
  if e['kind']!='return':assert (tuple(e['previous']) if e['previous'] is not None else None)==prev
  goal=tuple(e['goal']);end=events[i+1]['index'] if i+1<len(events) else len(path)-1
  assert cursor<=end<len(path);segment=path[cursor:end+1];assert segment[-1]==goal
  opts=sorted(q for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if q in pending and q in F);default=None
  if diag is not None and e['kind']!='return':
   row=diag['decision_states'][i];assert row['trace_record']==i and row['event']==norm(e) and ps(row['pending'])==pending and row['segment']==norm(segment)
   counts['pending_state_checks']+=1
  if e['kind']=='local':
   assert opts and end==cursor+1;ds=[math.dist(q,c['predator']) for q in opts];lo,hi=min(ds),max(ds);rows=[]
   for q,d in zip(opts,ds):
    rd=(d-lo)/(hi-lo) if hi>lo else 0;rs=0 if prev is None else math.acos(max(-1,min(1,(prev[0]-x)*(q[0]-x)+(prev[1]-y)*(q[1]-y))))/math.pi
    rb=1-sum(p in pending and p in F for p in ((q[0]-1,q[1]),(q[0]+1,q[1]),(q[0],q[1]-1),(q[0],q[1]+1)))/4
    rows.append(dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,score=rd+2*rs+.5*rb));counts['local_option_rows']+=1
   assert len(rows)==len(e['options'])
   for a,b in zip(rows,e['options']):
    assert a['cell']==tuple(b['cell'])
    for k in ('distance_reward','straight_reward','boundary_reward','score'):assert abs(a[k]-b[k])<1e-12
   assert goal==min(rows,key=lambda z:(-z['score'],z['cell']))['cell']
  elif e['kind']=='recovery':
   assert not opts and pending;d=bfs((x,y));assert pending<=set(d);default=min(pending,key=lambda q:(d[q],q));expected=default
   if arm!='history' and not examined and len(pending)>=2:
    examined=True;seq=[]
    for q in map(tuple,old):
     if q not in seq:seq.append(q)
    candidate=next((q for q in seq if q in pending and q!=default),None)
    trigger=dict(trace_record=i,route_index=cursor,current=[x,y],previous=norm(prev),pending=norm(sorted(pending)),default_goal=norm(default),alternative_goal=norm(candidate),default_distance=d[default],alternative_distance=d[candidate] if candidate is not None else None)
    if arm=='ALT1':assert candidate is not None and candidate in d;expected=candidate;applied+=1
    target=diag['trigger'] if diag is not None else (scanner or {}).get('trigger')
    assert target is not None
    for k in ('trace_record','route_index','current','previous','pending','default_goal','alternative_goal'):assert target[k]==trigger[k],('trigger',k)
    if diag is not None:
     assert target['default_distance']==d[default] and target['alternative_distance']==d[candidate]
     assert target['chosen_goal']==norm(expected) and target['actual_recovery_path']==norm(segment)
     assert target['tags']['q0_old_rank']==(seq.index(default) if default in seq else None)
     assert target['tags']['q1_old_rank']==(seq.index(candidate) if candidate in seq else None)
     assert target['tags']['q0_is_first_pending_in_old_order']==(next((q for q in seq if q in pending),None)==default)
   assert goal==expected and end-cursor==d[goal],'unauthorized choice or nonshortest recovery'
  else:
   assert e['kind']=='return' and not pending and goal==tuple(c['base']) and end-cursor==bfs((x,y))[goal]
  receipts.append(dict(trace_record=i,route_index=cursor,route_end=end,kind=e['kind'],previous=norm(prev),current=[x,y],pending_before=norm(sorted(pending)),default_goal=norm(default),actual_goal=norm(goal),segment_new_tasks=norm(sorted(pending&set(segment))),authorized_exception=arm=='ALT1' and trigger is not None and i==trigger['trace_record']))
  pending-=set(segment);cursor=end
 assert not pending and cursor==len(path)-1 and applied==int(arm=='ALT1')
 if diag is not None:
  assert diag['core_detail_profile_enabled'] is False and diag['counts']['applied']==applied and diag['counts']['matched']==1 and len(diag['decision_states'])==len(events)-1
 elif arm=='REF':assert (scanner['trigger'] is None)==(trigger is None)
 return dict(passed=True,counts=dict(counts),authorized_exceptions=applied,trigger=trigger,decisions=receipts,seconds=time.perf_counter()-start,path_tie_scope='original function/object bound by source, independent shortestness not a second tie function')
