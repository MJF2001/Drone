"""Independent scalar rewards, graph BFS and collection audit; no candidate imports."""
import math
from collections import deque
from common import points,pa,metric,cross
def bfs(f,a):
 d={a:0};q=deque([a])
 while q:
  x,y=q.popleft()
  for z in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
   if z in f and z not in d:d[z]=d[x,y]+1;q.append(z)
 return d
def check(c,x):
 r=x['raw'];f=points(c['free']);t=points(c['targets']);h=points(c['covered']);s=tuple(c['current']);base=tuple(c['base']);u=t-h-{s}
 p0=r['branches'].get('P0');details=dict(extra_work_connection_steps=0,work_segments=[])
 if p0 and p0['route']:pa.audit(c,p0);assert metric(c,p0['route'])==cross(c,p0['route'])
 if 'P1' in r['branches']:
  p1=r['branches']['P1'];e=tuple(r['e']);db=bfs(f,base);assert e==min(u,key=lambda q:(db[q],q));work=f-{e};pending=u-{e};route=list(map(tuple,p1['diagnostic_route']))
  assert route and route[0]==s and set(route)<=f
  assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
  if p1['status']=='reservation_infeasible':
   assert pending-bfs(work,s).keys()==points(p1['unreachable']);assert route==[s] and p1['phase1_end'] is None
  elif p1['status']=='core_complete':
   assert p1['route']==p1['diagnostic_route'];assert route[-1]==base and t<=h|set(route) and len(route)-1<=c['distance_budget']
   end=p1['phase1_end'];assert e not in route[:end+1] and u-{e}<=set(route[:end+1]);cursor=0
   for j,ev in enumerate(p1['trace']):
    assert ev['index']==cursor and tuple(ev['current'])==route[cursor]
    stop=p1['trace'][j+1]['index'] if j+1<len(p1['trace']) else len(route)-1;seg=route[cursor:stop+1];goal=tuple(ev['goal']);assert seg[-1]==goal
    if ev['phase']=='work':
     assert stop<=end and e not in seg and ev['pending_count']==len(pending)
     cur=route[cursor];xx,yy=cur;opts=sorted(q for q in pending if q in work and abs(q[0]-xx)+abs(q[1]-yy)==1)
     prev=route[cursor-1] if cursor else (tuple(c['previous']) if c['previous'] else None)
     assert ev['previous']==(list(prev) if prev else None) or ev['previous']==prev
     if ev['kind']=='local':
      assert opts and stop==cursor+1;pred=c['predator'];ds=[math.dist(q,pred) for q in opts];lo=min(ds);hi=max(ds);rr=[]
      for q,d in zip(opts,ds):
       rd=(d-lo)/(hi-lo) if hi>lo else 0
       rs=0 if prev is None else math.acos(max(-1,min(1,(prev[0]-xx)*(q[0]-xx)+(prev[1]-yy)*(q[1]-yy))))/math.pi
       rb=1-sum(abs(q[0]-z[0])+abs(q[1]-z[1])==1 for z in pending&work)/4
       rr.append(dict(cell=q,distance_reward=rd,straight_reward=rs,boundary_reward=rb,score=rd+2*rs+.5*rb))
      assert goal==min(rr,key=lambda v:(-v['score'],v['cell']))['cell']
      assert len(rr)==len(ev['options'])
      for expected,actual in zip(rr,ev['options']):
       assert tuple(actual['cell'])==expected['cell']
       for k in ('distance_reward','straight_reward','boundary_reward','score'):assert abs(expected[k]-actual[k])<1e-12
     else:
      assert ev['kind']=='recovery' and not opts;d=bfs(work,cur);assert goal==min(pending,key=lambda q:(d[q],q)) and stop-cursor==d[goal]
     delta=(stop-cursor)-bfs(f,cur)[goal];assert delta>=0;details['extra_work_connection_steps']+=delta;details['work_segments'].append(dict(index=cursor,end=stop,goal=goal,steps=stop-cursor,original_distance=bfs(f,cur)[goal],extra=delta))
     pending-=set(seg)
    else:
     assert ev['phase']=='released' and not pending
     if ev['kind']=='reserved':assert cursor==end and goal==e and ev['pending_count']==1
     else:assert ev['kind']=='return' and goal==base and ev['pending_count']==0
     assert stop-cursor==bfs(f,route[cursor])[goal]
    cursor=stop
   assert cursor==len(route)-1
   remain=set(u);last=None
   for q in route:
    if q in remain:remain.remove(q);last=q
   assert not remain and last==e;assert metric(c,route)==cross(c,route)
 if x['eligible']:
  assert r['status']=='core_complete' and x['entry_seconds']<x['budget'] and r['route'];assert metric(c,r['route'])==cross(c,r['route'])
  choices=[('P0',r['branches']['P0'])]+([('P1',r['branches']['P1'])] if r['branches'].get('P1',{}).get('status')=='core_complete' else [])
  chosen=min(choices,key=lambda pair:(len(pair[1]['route']),pair[0]));assert r['selected']==chosen[0]
  assert list(map(tuple,r['route']))==list(map(tuple,chosen[1]['route'])) and r['trace']==chosen[1]['trace']
 else:assert not r['route'] or r['status']!='deadline'
 return details
