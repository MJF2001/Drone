"""Independent scalar/graph audit plus independently implemented A* connector tie."""
import heapq
from common_orient import *
scalar=load('rotation_independent_decision',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
metric=load('rotation_metrics',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py').metrics
cross=load('rotation_cross',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py').calculate
def canonical(f,a,b):
 lo,hi=sorted((a,b));cost={lo:0};parent={};heap=[(abs(lo[0]-hi[0])+abs(lo[1]-hi[1]),0,lo)]
 while heap:
  _,d,p=heapq.heappop(heap)
  if d!=cost[p]:continue
  if p==hi:
   route=[p]
   while route[-1]!=lo:route.append(parent[route[-1]])
   route.reverse();return route if a==lo else list(reversed(route))
  x,y=p
  for q in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
   if q in f and d+1<cost.get(q,float('inf')):cost[q]=d+1;parent[q]=p;heapq.heappush(heap,(d+1+abs(q[0]-hi[0])+abs(q[1]-hi[1]),d+1,q))
 raise AssertionError('no connector')
def semantics(raw):
 r=norm(raw)
 for key in ('version','seconds','budget','accepted_seconds','overrun_gt_10ms'):r.pop(key,None)
 return r
def check(c,x):
 checked=[]
 for rec in x['raw']['candidates']:
  tc=rec['transformed_input'];r=rec['raw']
  if r['status']!='core_complete':continue
  cache={};old_bfs=scalar.bfs
  def bfs(f,a):
   if a not in cache:cache[a]=old_bfs(f,a)
   return cache[a]
  try:scalar.bfs=bfs;scalar.audit(tc,r)
  finally:scalar.bfs=old_bfs
  route=list(map(tuple,r['route']));f=pts(tc['free'])
  for i,ev in enumerate(r['trace']):
   if ev['kind'] in ('recovery','return'):
    start=ev['index'];end=r['trace'][i+1]['index'] if i+1<len(r['trace']) else len(route)-1;assert route[start:end+1]==canonical(f,route[start],tuple(ev['goal']))
  back=rec['inverse'];m=metric(c,back['route']);assert m==cross(c,back['route']) and m['complete_legal'];checked.append(dict(degree=rec['degree'],metrics=m,decisions=len(r['trace'])))
 if x['eligible']:
  rr=x['raw']['candidates'];best=min(range(len(rr)),key=lambda i:(len(rr[i]['inverse']['route']),i));assert x['raw']['selected_degree']==rr[best]['degree'] and x['raw']['route']==rr[best]['inverse']['route'] and x['entry_seconds']<x['budget']
 elif x['status']=='deadline':assert not x['raw']['route'] and x['raw']['selected_degree'] is None
 return checked
