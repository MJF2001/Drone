"""One offline specified recovery replacement; no coverage rollout or selector."""
import json,time
from collections import Counter
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
KEYS=('recovery_hook_calls','decision_records','matched','applied','explanatory_distance_queries','prefix_decision_checks','pending_cells_logged')
class Diagnostic:
 def __init__(self,spec,enabled,clock=time.perf_counter):
  self.spec=spec;self.enabled=enabled;self.clock=clock;self.counts=Counter({k:0 for k in KEYS});self.records=[];self.trigger=None;self.seconds=0.
 def choose(self,trace,route,current,previous,pending,default,geometry):
  start=self.clock()
  try:
   self.counts['recovery_hook_calls']+=1;i=len(trace);s=self.spec;k=s['trace_record']
   if i!=k:
    if i<k:
     expected=s['original_trace'][i];assert expected['kind']=='recovery' and norm(default)==expected['goal'],'early recovery mismatch'
     assert not (norm(current)==s['current'] and norm(previous)==s['previous'] and set(pending)==set(map(tuple,s['pending']))),'early matching state'
    else:assert self.counts['matched']==1,'specified trigger was missed'
    return default
   assert self.counts['matched']==0,'duplicate trigger'
   assert norm(trace)==s['original_trace'][:k],'semantic prefix mismatch'
   assert norm(route)==s['original_route_prefix'],'route prefix mismatch'
   assert norm(current)==s['current'] and norm(previous)==s['previous'],'state mismatch'
   assert sorted(pending)==sorted(map(tuple,s['pending'])),'full pending mismatch'
   assert norm(default)==s['default_goal'] and s['original_trace'][k]['kind']=='recovery','default target/type mismatch'
   alt=tuple(s['alternative_goal']);assert alt!=tuple(default) and alt in pending and alt in geometry.s.free and alt in geometry.reachable,'alternative not pending/free/reachable'
   # The normal min(pending, distance) has already executed. Only these two
   # explanatory repeat queries are added; both use the same original object.
   dd=geometry.distance(current,default);ad=geometry.distance(current,alt);self.counts['explanatory_distance_queries']+=2
   self.counts['matched']=1;self.counts['applied']=int(self.enabled)
   self.trigger={'trace_record':i,'route_index':len(route)-1,'current':norm(current),'previous':norm(previous),'pending':norm(sorted(pending)),'default_goal':norm(default),'alternative_goal':norm(alt),'default_distance':dd,'alternative_distance':ad,'chosen_goal':norm(alt if self.enabled else default),'replacement_enabled':self.enabled,'original_prefix_checked':True}
   return alt if self.enabled else default
  finally:self.seconds+=self.clock()-start
 def record(self,trace,event,pending,route,segment):
  start=self.clock()
  try:
   i=len(trace);k=self.spec['trace_record'];e=norm(event)
   if i<k:
    assert e==self.spec['original_trace'][i],'pre-trigger full decision differs';self.counts['prefix_decision_checks']+=1
   if i==k:assert self.counts['matched']==1 and e['goal']==self.trigger['chosen_goal'],'missing/incorrect unique hook'
   self.records.append({'trace_record':i,'event':e,'pending':norm(sorted(pending)),'segment':norm(segment)});self.counts['decision_records']+=1;self.counts['pending_cells_logged']+=len(pending)
   if i==k:self.trigger['actual_recovery_path']=norm(segment)
  finally:self.seconds+=self.clock()-start
 def finish(self,raw):
  start=self.clock()
  try:
   assert raw['status']=='core_complete','no complete core output'
   assert self.counts['matched']==1 and self.counts['applied']==int(self.enabled),'trigger missing/repeated'
   assert len(self.records)==len(raw['trace'])-1 and raw['trace'][-1]['kind']=='return','record coverage mismatch'
   assert self.trigger is not None and 'actual_recovery_path' in self.trigger
  finally:self.seconds+=self.clock()-start
 def export(self):return {'target_intervention_enabled':self.enabled,'core_detail_profile_enabled':False,'counts':dict(self.counts),'diagnostic_hook_seconds':self.seconds,'trigger':self.trigger,'decision_states':self.records,'scope':'one full run, same default rule and path object; no internal normal rollout, no target competition, no reset at trigger'}
