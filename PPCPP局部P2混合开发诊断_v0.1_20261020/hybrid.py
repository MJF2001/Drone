"""One fixed radius2 first-capture envelope; literal prefix and suffix."""
from dataclasses import replace
from support import *
from runtime import native,DeadlineExceeded,snapshot,validate
from range_p2_engine_20261015 import solve as local_engine
VERSION='PPCPP_LOCAL_P2_v0.1'
class InvalidCandidate(Exception):pass
def window(c,path,marker,tick=lambda _:None):
 route=list(map(tuple,path));t=pts(c['targets']);done=pts(c['covered']);first={}
 for i,q in enumerate(route):
  tick('window_scan')
  if q in t and q not in done:done.add(q);first[q]=i
 pending=t-pts(c['covered'])-{tuple(c['current'])};B=pts(marker)
 seeds={q for q in pending if B and min(abs(q[0]-b[0])+abs(q[1]-b[1]) for b in B)<=2}
 if not seeds:return dict(empty=True,seeds=[],first_indices=[dict(cell=q,index=i) for q,i in sorted(first.items())])
 l=max(0,min(first[q] for q in seeds)-1);r=min(len(route)-1,max(first[q] for q in seeds)+1)
 prefix=route[:l+1];suffix=route[r:];h=pts(c['covered'])|(set(prefix)&t);required={q for q,i in first.items() if l<i<=r}
 assert not required&h
 return dict(empty=False,left=l,right=r,entry=route[l],exit=route[r],seeds=sorted(seeds),required=sorted(required),local_H=sorted(h),prefix=prefix,suffix=suffix,original_patch=route[l:r+1],pending=len(pending),task_fraction=len(required)/len(pending) if pending else 0,step_fraction=(r-l)/(len(route)-1) if len(route)>1 else 0,first_indices=[dict(cell=q,index=i) for q,i in sorted(first.items())])
def combine(cfg,patch):return tuple(map(tuple,cfg['prefix'][:-1]))+tuple(map(tuple,patch))+tuple(map(tuple,cfg['suffix'][1:]))
def run(payload,budget,seed,*,clock=time.perf_counter,hook=None,baseline=None,engine=None):
 begin=clock();deadline=begin+budget;raw=dict(version=VERSION,status='not_started',route=(),selected=None,P0=None,window=None,local=None,assembled_route=(),internal_calls=dict(PPCPP=0,local_P2=0));phases={}
 def tick(stage):
  if hook:hook(stage)
  if clock()>=deadline:raise DeadlineExceeded()
 try:
  env=json.loads(payload);c=env['state'];marker=env['marker'];validate(c);s=snapshot(c);tick('p0_before');a=clock();raw['internal_calls']['PPCPP']=1
  p0=(baseline or native.solve)(s,pts(c['initial_targets']),deadline-clock(),seed,tuple(c['predator']),tuple(c['previous']) if c['previous'] else None,_clock=clock)
  raw['P0']=p0;phases['p0']=clock()-a;tick('p0_after')
  if p0['status']!='core_complete':raw.update(status='p0_failed',reason=p0.get('reason'))
  else:
   a=clock();tick('window_before');cfg=window(c,p0['route'],marker,tick);raw['window']=cfg;phases['window']=clock()-a;chosen=tuple(p0['route']);selected='P0'
   if not cfg['empty']:
    local=replace(s,name=s.name+'_fixed_local',targets=frozenset(pts(cfg['required'])),covered=frozenset(pts(cfg['local_H'])),current=tuple(cfg['entry']),base=tuple(cfg['exit']),old_route=tuple(map(tuple,cfg['original_patch'])),distance_budget=s.distance_budget-cfg['left']-(len(p0['route'])-1-cfg['right']))
    def accept(patch,label):
     tick('local_offer');checked=native.single_cell_audit(local,tuple(patch))
     if not checked['valid']:raise InvalidCandidate(dict(stage='local',source=label,errors=checked['errors'],patch=patch))
     full=combine(cfg,patch);checked=native.single_cell_audit(s,full);tick('splice_check')
     if not checked['valid']:raise InvalidCandidate(dict(stage='full',source=label,errors=checked['errors'],patch=patch))
     return True
    tick('local_before');a=clock();raw['internal_calls']['local_P2']=1
    er=(engine or local_engine)(local,deadline-clock(),'multi',seed,accept=accept);raw['local']=er;phases['local_P2']=clock()-a;tick('local_after')
    if not er['route']:raise InvalidCandidate('local engine returned no accepted route; no silent P0 rescue')
    a=clock();accept(tuple(map(tuple,er['route'])),'returned');full=combine(cfg,er['route']);raw['assembled_route']=full
    if len(full)<len(chosen):chosen=full;selected='LOCAL_P2'
    phases['splice']=clock()-a
   tick('final_check');checked=native.single_cell_audit(s,chosen)
   if not checked['valid']:raise InvalidCandidate(checked)
   raw.update(status='core_complete',route=chosen,selected=selected)
  tick('encode_before');a=clock();wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':'));phases['encoding']=clock()-a;tick('encode_after')
 except DeadlineExceeded:raw.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 except Exception as exc:raw.update(status='candidate_invalid' if isinstance(exc,InvalidCandidate) else 'exception',route=(),selected=None,reason=repr(exc))
 elapsed=clock()-begin
 if elapsed>=budget:raw.update(status='deadline',route=(),selected=None,reason='shared_entry_deadline')
 return dict(raw=raw,budget=budget,seed=seed,entry_seconds=elapsed,phase_seconds=phases,eligible=raw['status']=='core_complete' and elapsed<budget)
