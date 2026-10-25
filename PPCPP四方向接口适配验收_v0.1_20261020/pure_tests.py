import math
from common_orient import *
from transform import *
import entry
def run():
 inputs=[read(i['input']) for i in read(H/'protocol.json')['inputs']];biased=norm(inputs[0])
 for key in SETS:biased[key]=[[x-17,y+23] for x,y in biased[key]]
 for key in POINTS:
  if biased[key] is not None:biased[key]=[biased[key][0]-17,biased[key][1]+23]
 biased['previous']=None;empty=norm(biased)
 for key in SETS:empty[key]=[]
 inputs += [biased,empty];checks=0
 for c in inputs:
  raw=norm(c)
  for _ in range(4):
   for key in SETS:raw[key]=[list(rotate(p,1)) for p in raw[key]]
   for key in POINTS:
    if raw[key] is not None:raw[key]=list(rotate(raw[key],1))
  assert raw==c
  for k in range(4):
   r,m=transform(c,k);assert inverse_input(r,m)==c
   for field in SETS:assert len(r[field])==len(c[field])
   oldpath=c['old_route'];newpath=r['old_route'];assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==abs(x[0]-y[0])+abs(x[1]-y[1]) for a,b,x,y in zip(oldpath,oldpath[1:],newpath,newpath[1:]))
   if c['free']:
    def dims(f):return (max(x for x,y in f)-min(x for x,y in f)+1,max(y for x,y in f)-min(y for x,y in f)+1)
    assert dims(r['free'])==(dims(c['free'])[::-1] if k%2 else dims(c['free']))
   checks+=1
 # Pure predicates show strict rectangle boundary/hole rejection, not predator-not-in-F.
 contracts=[];f={(x,y) for x in range(4) for y in range(3)}-{(1,1)}
 for p,expected in [((-1,1),True),((4,1),True),((1,-1),True),((1,3),True),((-1,-1),True),((0,0),False),((1,1),False),((3,2),False)]:
  ok=p[0]<0 or p[0]>3 or p[1]<0 or p[1]>2;assert ok==expected;contracts.append(dict(point=p,new_allowed=ok,old_allowed=p[0]<0 or p[0]>3,in_F=p in f))
 # Original empty-domain contract is unchanged; call check_contract, not solve.
 for module in (entry.old,entry.new):
  try:module.check_contract(entry.snapshot(empty),set(),20)
  except ValueError:pass
  else:raise AssertionError('empty domain must fail original contract')
 c=read(H/'fixtures/left_new.json');c['targets']=[[1,0]];c['published_targets']=[[1,0]];c['initial_targets']=[[1,0]];c['old_route']=[[0,0],[1,0],[0,0]];payload=json.dumps(c)
 def stub(s,initial,budget,seed,predator,previous,**kw):return dict(version='TIMING_STUB',method='PPCPP_INDEPENDENT',status='core_complete',route=s.old_route,trace=[],predator=predator,initial_previous=previous,weights=(2.,.5),seconds=0,budget=budget,seed=seed,seed_used=False,accepted_seconds=0,fallback_selected=False,overrun_gt_10ms=False,reason=None)
 stages=['decoded','transform_before','transform_after','inverse_before','inverse_after','check_before','check_after','encode_before','encode_after']+[f'candidate_{k}_{s}' for k in range(4) for s in ('before','core_before','core_after','after')]
 deadlines=[]
 for stage in stages:
  off=[0];hit=[]
  def clock():return time.perf_counter()+off[0]
  def hook(s):
   if s==stage:off[0]=30;hit.append(s)
  x=entry.run(payload,'COMBO',20,solver=stub,clock=clock,hook=hook);assert hit and x['status']=='deadline' and not x['raw']['route'];deadlines.append(stage)
 # Pure native-body timing stubs: fake geometry (no BFS/A*) verifies loop/connector tick.
 kernel=[]
 for where in ('loop','connection'):
  cc=norm(c)
  if where=='connection':cc['targets']=[[2,0]];cc['published_targets']=[[2,0]];cc['initial_targets']=[[2,0]]
  s=entry.snapshot(cc);off=[0];oldreward=entry.new.core.reward_options
  def clock():return time.perf_counter()+off[0]
  class FakeGeometry:
   def __init__(self,*a,**kw):pass
   def precheck(self):return None
   def distance(self,a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
   def path(self,a,b):off[0]=30;return [a,b]
  def reward(*a,**kw):
   result=oldreward(*a,**kw)
   if where=='loop':off[0]=30
   return result
  try:
   entry.new.core.reward_options=reward;r=entry.new.solve(s,pts(cc['initial_targets']),20,0,(-1,0),None,_clock=clock,_geometry=FakeGeometry)
  finally:entry.new.core.reward_options=oldreward
  assert r['status']=='deadline' and not r['route'];kernel.append(where)
 result=dict(passed=True,transform_cases=len(inputs),transform_checks=checks,contracts=contracts,deadline_stubs=deadlines,native_body_fake_geometry_stubs=kernel,real_solver_calls=0,notes='Two native.solve body tests use fake geometry/reward-clock hooks, counted only as stubs, no real path planning. No production file modified.')
 save(H/'pure_tests.json',result);print('PURE TRANSFORM/CONTRACT/CUTOFF PASS',checks,len(stages),'real solves0')
if __name__=='__main__':run()
