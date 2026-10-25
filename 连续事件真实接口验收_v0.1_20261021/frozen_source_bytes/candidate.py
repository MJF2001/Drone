"""Only new policy: one input-selected last target; private F-e then restore F."""
import json,hashlib
from dataclasses import replace
from runtime import native,DeadlineExceeded,NoPath
VERSION='PPCPP_LAST_RESERVE_v0.2'
def append_segment(route,pending,segment,mark):
 assert segment[0]==route[-1]
 for q in segment[1:]:mark('alternative_move');route.append(q);pending.discard(q)
def solve(s,initial,mode,seed,predator,previous,begin,deadline,phases,mark,clock,geometry):
 assert mode in ('PPCPP','ONE','LAST')
 out=dict(version=VERSION,mode=mode,status='not_started',route=(),trace=[],selected=None,e=None,branches={},reason=None)
 try:
  mark('p0_before');a=clock();p0=native.solve(s,initial,deadline-clock(),seed,predator,previous,_clock=clock,_geometry=geometry);phases['p0']=clock()-a;out['branches']['P0']=p0
  mark('p0_done')
  if p0['status']!='core_complete':out.update(status=p0['status'],reason='original_branch_failed');return out
  pristine=json.dumps(p0,sort_keys=True);chosen=p0;out['selected']='P0'
  u=set(s.targets)-set(s.covered)-{s.current}
  if mode=='LAST' and u:
   a=clock();mark('candidate_before');full=geometry(s,deadline)
   def dist(q):mark('candidate_distance');return full.distance(s.base,q)
   e=min(u,key=lambda q:(dist(q),q));out['e']=e;phases['candidate']=clock()-a
   branch=dict(status='building',route=(),diagnostic_route=[s.current],trace=[],reserved=e,work_free_count=len(s.free)-1,cache_scopes=['original_full','alternative_full','alternative_work'],phase1_end=None,accepted_seconds=None)
   out['branches']['P1']=branch;route=[s.current];trace=branch['trace'];pending=set(u)-{e};a=clock()
   def move(segment):
    append_segment(route,pending,segment,mark)
   try:
    if pending:
     work_snapshot=replace(s,free=frozenset(set(s.free)-{e}),targets=frozenset(pending))
     work=geometry(work_snapshot,deadline)
     assert work.cache is not full.cache and work.distance_rows is not full.distance_rows
     # No work.precheck(): the base may be absent/unreachable until reservation release.
     missing=pending-work.reachable;mark('phase1_precheck')
     if missing:branch.update(status='reservation_infeasible',unreachable=sorted(missing))
     else:
      while pending:
       mark('phase1');cur=route[-1];prev=route[-2] if len(route)>1 else previous
       opts=native.core.reward_options(cur,prev,pending,work_snapshot.free,predator,(2.,.5))
       event=dict(phase='work',index=len(route)-1,current=cur,previous=prev,pending_count=len(pending))
       if opts:goal=native.core.choose_neighbor(opts);segment=(cur,goal);event.update(kind='local',goal=goal,options=opts)
       else:goal=min(pending,key=lambda q:(work.distance(cur,q),q));segment=work.path(cur,goal);event.update(kind='recovery',goal=goal)
       trace.append(event);move(segment)
    if branch['status']!='reservation_infeasible':
     branch['phase1_end']=len(route)-1;mark('release')
     trace.append(dict(phase='released',kind='reserved',index=len(route)-1,current=route[-1],goal=e,pending_count=1));move(full.path(route[-1],e))
     mark('return');trace.append(dict(phase='released',kind='return',index=len(route)-1,current=route[-1],goal=s.base,pending_count=0));move(full.path(route[-1],s.base))
     mark('p1_audit_before');checked=native.single_cell_audit(s,tuple(route));mark('p1_audit_after')
     branch.update(status='core_complete' if checked['valid'] else 'core_invalid',route=tuple(route) if checked['valid'] else (),errors=checked['errors'],accepted_seconds=clock()-begin if checked['valid'] else None)
   except NoPath as ex:branch.update(status='planning_failure',reason=str(ex))
   finally:branch['diagnostic_route']=tuple(route);phases['p1']=clock()-a
   assert json.dumps(p0,sort_keys=True)==pristine,'P0 was mutated'
   if branch['status']=='core_complete' and len(branch['route'])<len(p0['route']):chosen=branch;out['selected']='P1'
  elif mode=='LAST':out['no_tasks']=True
  mark('final_audit_before');a=clock();checked=native.single_cell_audit(s,tuple(chosen['route']));phases['final_audit']=clock()-a;mark('final_audit_after')
  out.update(status='core_complete' if checked['valid'] else 'core_invalid',route=tuple(chosen['route']) if checked['valid'] else (),trace=chosen['trace'],reason=checked['errors'] or None)
 except DeadlineExceeded:
  out.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 return out
