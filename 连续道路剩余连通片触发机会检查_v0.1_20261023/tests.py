"""Six predeclared cases only; handwritten sets and fixed distance relations."""
from collections import Counter
from copy import deepcopy
import primary as P,independent as I
def run():
 rows=[]
 for n in range(1,7):
  if n==1:
   full={(x,0) for x in range(7)};H={(2,0),(4,0)};Q=full-H
   assert len(P.components(full,Counter()))==1 and P.components(Q,Counter())==I.components(Q,Counter()) and len(P.components(Q,Counter()))==3
   assert not Q&H
  elif n==2:
   q={(2,0),(6,0)};parts=[[(2,0)],[(6,0)]];d=lambda p:{(2,0):2,(6,0):2}
   assert P.judge(q,q,(0,0),(4,0),(2,0),parts,d)['reason']=='minimum_tie'
  elif n==3:
   q={(2,0),(6,0),(7,0)};parts=[[(2,0)],[(6,0),(7,0)]];d=lambda p:{(2,0):5,(6,0):1,(7,0):2}
   assert P.judge(q,q,(0,0),(5,0),(6,0),parts,d)['reason']=='default_already_other'
  elif n==4:
   q={(2,0),(6,0),(7,0)};parts=[[(2,0)],[(6,0),(7,0)]]
   for X,expected in (((4,0),True),((0,0),False)):
    fields={(0,0):{(2,0):2,(6,0):6,(7,0):7},(2,0):{(2,0):0,(6,0):4,(7,0):5},(4,0):{(2,0):2,(6,0):2,(7,0):3}}
    a=P.judge(q,q,(0,0),X,(2,0),parts,lambda p:fields[p]);b=I.judge(q,q,(0,0),X,(2,0),parts,lambda p:fields[p]);assert a==b and a['trigger']==expected
  elif n==5:
   c=dict(free=[[0,0],[1,0]],targets=[[1,0]],covered=[],published_targets=[[1,0]],deferred_targets=[],current=[0,0],previous=None)
   raw=dict(route=[[0,0],[1,0],[0,0]],trace=[dict(index=0,kind='local',current=[0,0],previous=None,pending_count=1),dict(index=1,kind='return',current=[1,0],pending_count=0)])
   assert P.extract(c,raw,{'new_H':[]})==I.extract(c,raw,{'new_H':[]}) and not P.extract(c,raw,{'new_H':[]})['has_recovery']
  elif n==6:
   assert P.points([(1,2),[3,4]])=={(1,2),(3,4)}
   try:P.points([(True,2)])
   except AssertionError:pass
   else:raise AssertionError('bool coordinate accepted')
   c=dict(free=[[0,0],[1,0]],targets=[[1,0]],covered=[[1,0]],published_targets=[[1,0]],deferred_targets=[],current=[0,0],previous=None)
   raw=dict(route=[[0,0]],trace=[dict(index=0,kind='recovery',current=[0,0],previous=None,pending_count=1,goal=[1,0])])
   try:P.extract(c,raw,{'new_H':[]})
   except AssertionError:pass
   else:raise AssertionError('Q/H confusion accepted')
  rows.append(dict(id=n,passed=True))
 return dict(passed=True,cases=rows,real_core=0,post=0,generated_routes=0,fixture_graph_distance_rows=0,scope='handwritten sets/distance facts; no planner imports')
