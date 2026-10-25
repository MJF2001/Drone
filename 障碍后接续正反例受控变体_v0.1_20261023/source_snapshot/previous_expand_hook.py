"""One prefix-only old-order alternative; never consumes a future route/result."""
from collections import Counter
import time
from common import norm,ps
def select(pending,default,old):
 seen=set();ordered=[];ranks={}
 for i,v in enumerate(old):
  q=tuple(v)
  if q not in seen:seen.add(q);ordered.append(q);ranks[q]=i
 current=[q for q in ordered if q in pending]
 alt=next((q for q in current if q!=default),None)
 first=current[0] if current else None
 return alt,{'q0_is_first_pending_in_old_order':default==first,'q0_old_rank':ranks.get(default),'q1_old_rank':ranks.get(alt),
  'identity_class':'default_not_in_old_order' if default not in ranks else 'default_already_prioritizes_old_order' if default==first else 'alternative_precedes_default',
  'first_pending_in_old_order':norm(first)}
def packet(record,index,current,previous,pending,default,old):
 alt,tags=select(pending,default,old)
 return dict(trace_record=record,route_index=index,current=norm(current),previous=norm(previous),pending=norm(sorted(pending)),default_goal=norm(default),alternative_goal=norm(alt),tags=tags,status='applicable' if alt is not None else 'no_distinct_old_candidate')
def scan_ref(events,prefix_stream,U,old,deadline):
 pending=set(U);cursor=-1;calls=0;one=False;found=None
 for i,e in enumerate(events):
  assert time.perf_counter()<deadline,'selector_deadline'
  while cursor<e['index']:
   cursor,p=next(prefix_stream);pending.discard(tuple(p));calls+=1
  assert len(pending)==e['pending_count']
  if e['kind']=='recovery':
   one=True
   if len(pending)>=2:
    found=packet(i,e['index'],e['current'],e['previous'],pending,tuple(e['goal']),old);break
 return {'trigger':found,'status':found['status'] if found else 'singleton_recovery' if one else 'no_recovery','counts':{'prefix_vertices':calls}}
class Diagnostic:
 def __init__(self,old,enabled):
  self.old=old;self.enabled=enabled;self.examined=False;self.trigger=None;self.records=[];self.seconds=0.;self.counts=Counter({k:0 for k in ['recovery_hook_calls','decision_records','matched','applied','explanatory_distance_queries','pending_cells_logged','old_order_cells_scanned']})
 def choose(self,trace,route,current,previous,pending,default,geometry):
  start=time.perf_counter()
  try:
   self.counts['recovery_hook_calls']+=1
   if self.examined or len(pending)<2:return default
   self.examined=True;self.counts['old_order_cells_scanned']+=len(self.old)
   t=packet(len(trace),len(route)-1,current,previous,pending,default,self.old);self.trigger=t
   if t['alternative_goal'] is None:return default
   alt=tuple(t['alternative_goal']);assert alt in pending and alt in geometry.s.free and alt in geometry.reachable,'candidate_unavailable_contract_error'
   d0=geometry.distance(current,default);d1=geometry.distance(current,alt);self.counts['explanatory_distance_queries']+=2
   assert d1>=d0
   t.update(default_distance=d0,alternative_distance=d1,chosen_goal=norm(alt if self.enabled else default),replacement_enabled=self.enabled)
   self.counts['matched']+=1;self.counts['applied']+=int(self.enabled)
   return alt if self.enabled else default
  finally:self.seconds+=time.perf_counter()-start
 def record(self,trace,event,pending,route,segment):
  start=time.perf_counter();self.records.append(dict(trace_record=len(trace),event=norm(event),pending=norm(sorted(pending)),segment=norm(segment)))
  self.counts['decision_records']+=1;self.counts['pending_cells_logged']+=len(pending)
  if self.trigger and self.trigger['trace_record']==len(trace):self.trigger['actual_recovery_path']=norm(segment)
  self.seconds+=time.perf_counter()-start
 def export(self):return dict(target_intervention_enabled=self.enabled,core_detail_profile_enabled=False,trigger=self.trigger,decision_states=self.records,counts=dict(self.counts),diagnostic_hook_seconds=self.seconds)
