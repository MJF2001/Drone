"""Handwritten fixed synthetic evidence; never generates a planner route."""
from copy import deepcopy
def active():
 Q=[(2,0),(6,0),(7,0)];path=[(4,0),(5,0),(6,0),(7,0),(6,0),(5,0),(4,0),(3,0),(2,0),(1,0),(0,0)];opt=dict(cell=(7,0),distance_reward=0.,straight_reward=1.,boundary_reward=1.,score=2.5)
 trace=[dict(index=0,current=(4,0),previous=(4,1),pending_count=3,phase='OTHER',Q=Q,allowed=[(6,0),(7,0)],original_options=[],kind='recovery',goal=(6,0)),dict(index=2,current=(6,0),previous=(5,0),pending_count=2,phase='OTHER',Q=[(2,0),(7,0)],allowed=[(7,0)],original_options=[opt],options=[opt],kind='local',goal=(7,0)),dict(index=3,current=(7,0),previous=(6,0),pending_count=1,phase='TAIL',Q=[(2,0)],allowed=[(2,0)],original_options=[],kind='recovery',goal=(2,0)),dict(kind='return',index=8,current=(2,0),goal=(0,0),pending_count=0)]
 check=dict(index=0,Q=Q,counts={'S':1,'R':2},q0=(2,0),representatives={'S':(2,0),'R':(6,0)},conditions=[dict(other='R',d_R_B=6,d_R_S=4,d_S_B=2,d_X_R=2,d_X_S=2,on_return=True,detour_strict=True)],activated=True,reason='activated',S='S',S_pending_at_activation=[(2,0)])
 rule=dict(enabled=True,checked=True,check=check,S='S',phase='TAIL',transitions=[dict(index=0,phase='OTHER',Q_S=1,Q_other=2),dict(index=3,phase='TAIL',Q_S=1,Q_other=0)],release_pending=((2,0),),counts=dict(rule_distance_rows=3,rule_BFS_popped=54,rule_distance_lookups=0,local_changes=0,recovery_changes=1),preparation_seconds=0.,detailed_profile=False)
 c=dict(free=[(x,y) for x in range(9) for y in range(2)],targets=Q,covered=[],current=(4,0),base=(0,0),previous=(4,1),predator=(-10,0),distance_budget=1000000,labels={'S':[(2,0)],'R':[(6,0),(7,0)]})
 return deepcopy(c),deepcopy(dict(status='core_complete',route=path,trace=trace,rule=rule))
def unchecked():
 c=dict(free=[(0,0),(1,0)],targets=[(1,0)],covered=[],current=(0,0),base=(0,0),previous=None,predator=(-10,0),distance_budget=1000000,labels={'R':[(1,0)]})
 opt=dict(cell=(1,0),distance_reward=0.,straight_reward=0.,boundary_reward=1.,score=.5)
 r=dict(status='core_complete',route=[(0,0),(1,0),(0,0)],trace=[dict(kind='local',index=0,current=(0,0),goal=(1,0),pending_count=1,previous=None,phase='DEFAULT',Q=[(1,0)],allowed=[(1,0)],original_options=[opt],options=[opt]),dict(kind='return',index=1,current=(1,0),goal=(0,0),pending_count=0)],rule=dict(enabled=True,checked=False,check=None,S=None,phase='DEFAULT',transitions=[],release_pending=None,counts=dict(rule_distance_rows=0,rule_BFS_popped=0,rule_distance_lookups=0,local_changes=0,recovery_changes=0),preparation_seconds=0.,detailed_profile=False))
 return c,r
def memory_variant(x):
 """Source-shaped coordinate tuples, not restoration of lost live objects."""
 single={'current','previous','goal','q0','cell','base','predator','initial_previous'}
 many={'route','free','targets','covered','Q','allowed','release_pending','S_pending_at_activation'}
 def convert(v,key=None):
  if isinstance(v,dict):
   if key in ('representatives','labels'):
    return {k:(tuple(p) if key=='representatives' else [tuple(q) for q in p]) for k,p in v.items()}
   return {k:convert(p,k) for k,p in v.items()}
  if v is not None and key in single:return tuple(v)
  if v is not None and key in many:return [tuple(p) for p in v]
  if isinstance(v,(tuple,list)):return [convert(p) for p in v]
  return v
 return convert(x)
