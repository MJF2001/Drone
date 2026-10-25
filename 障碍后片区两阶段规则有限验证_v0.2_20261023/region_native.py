"""Independent candidate, original reward on full Q then allowed-set filtering."""
import time,math
import frozen_reference as original
from region_rule import Priority

def solve(s,initial,budget,seed,predator,previous,*,labels,enabled,_clock=time.perf_counter):
 # OFF goes directly to the unchanged algorithm; no rule object or distance rows.
 if not enabled:return original.solve(s,initial,budget,seed,predator,previous)
 begin=_clock();deadline=begin+budget;route=[];trace=[];status='not_started';reason=None;accepted=None;g=None
 def tick():
  if _clock()>=deadline:raise original.DeadlineExceeded()
 rule=Priority(labels,s.free,s.base,tick)
 def move(segment,Q):
  assert segment[0]==route[-1]
  for p in segment[1:]:
   tick();route.append(p);Q.discard(p);rule.moved(Q,len(route)-1)
   if len(route)-1>4096:raise ValueError('raw edge cap')
 try:
  original.check_contract(s,initial,budget)
  if not math.isfinite(budget):raise ValueError('finite budget')
  if len(predator)!=2 or not all(math.isfinite(v) for v in predator):raise ValueError('finite predator')
  if s.free and not(predator[0]<min(x for x,y in s.free) or predator[0]>max(x for x,y in s.free)):raise ValueError('predator outside x')
  if previous is not None and sum(abs(a-b) for a,b in zip(previous,s.current))!=1:raise ValueError('heading')
  tick();g=original.UnifiedGeometry(s,deadline);reason=g.precheck();tick()
  if reason:status='environment_infeasible'
  else:
   Q=set(s.targets)-set(s.covered)-{s.current};route=[s.current]
   while Q:
    tick();cur=route[-1];prev=route[-2] if len(route)>1 else previous
    opts=original.core.reward_options(cur,prev,Q,s.free,predator,(2.,.5));tick()
    # Only the first ORIGINAL recovery can trigger the one opportunity.
    if not opts and not rule.checked:
     q0=min(Q,key=lambda q:(g.distance(cur,q),q));rule.inspect(Q,cur,q0,len(route)-1);tick()
    allowed=rule.filter(opts,Q);E=rule.allowed(Q)
    event={'index':len(route)-1,'current':cur,'previous':prev,'pending_count':len(Q),'phase':rule.phase,'Q':sorted(Q),'allowed':sorted(E),'original_options':opts}
    if allowed:
     goal=original.core.choose_neighbor(allowed);segment=(cur,goal);event.update(kind='local',options=allowed,goal=goal)
     rule.counts['local_changes']+=int(goal!=original.core.choose_neighbor(opts))
    else:
     goal=min(E,key=lambda q:(g.distance(cur,q),q));segment=g.path(cur,goal);event.update(kind='recovery',goal=goal)
     default=original.core.choose_neighbor(opts) if opts else min(Q,key=lambda q:(g.distance(cur,q),q))
     rule.counts['recovery_changes']+=int(bool(opts) or goal!=default)
    trace.append(event);move(segment,Q)
   tick();trace.append({'kind':'return','index':len(route)-1,'current':route[-1],'goal':s.base,'pending_count':0});move(g.path(route[-1],s.base),Q)
   checked=original.single_cell_audit(s,tuple(route));tick()
   if checked['valid']:accepted=_clock()-begin;tick();status='core_complete'
   else:status='core_invalid';reason=checked['errors']
 except original.DeadlineExceeded:status='deadline'
 except original.NoPath as e:status='planning_failure';reason=str(e)
 seconds=_clock()-begin
 return {'version':'PPCPP_REGION_TAIL_V1','method':'PPCPP_REGION_TAIL_V1','route':tuple(route) if status=='core_complete' else (), 'trace':trace,'status':status,'reason':reason,'seconds':seconds,'budget':budget,'seed':seed,'seed_used':False,'predator':predator,'initial_previous':previous,'weights':(2.,.5),'accepted_seconds':accepted,'fallback_selected':False,'overrun_gt_10ms':seconds>budget+.01,'rule':rule.export(),'geometry_counts':{'native_BFS_rows':getattr(g,'bfs_rows_built',None),'native_path_searches':getattr(g,'searches',None),'node_expansions':None}}
