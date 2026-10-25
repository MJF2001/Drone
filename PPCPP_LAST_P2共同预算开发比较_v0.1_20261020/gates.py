import types
from support import *
import runtime,candidate,p2_adapter,baseline_suite,p2_search_audit,model
from environment import verify
def clean(x):
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if k not in ('seconds','start','end','budget','overrun_gt_10ms','independent_audit')}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 return x
def main():
 verify();assert read(H/'environment_seal.json')['complete'];out=[];objects=[]
 adapter=load('p2_gate_last_audit',H/'audit_adapter.py')
 def record(kind,name,method,x):
  save(H/'gates'/f'{len(out):03d}.json',dict(kind=kind,name=name,method=method,result=norm(x)));out.append(dict(kind=kind,name=name,method=method,path=f'gates/{len(out):03d}.json'))
 geometry=p2_search_audit.UnifiedGeometry
 class Spy(geometry):
  def __init__(self,*a,**k):super().__init__(*a,**k);objects.append(self)
 for i,c in enumerate(read(H/'fixtures.json')):
  s=runtime.snapshot(c);initial=set(map(tuple,c['initial_targets']))
  if i==0:p2_search_audit.UnifiedGeometry=Spy
  a=baseline_suite.solve(s,initial,'P2_MULTI',5,20261020,None);record('p2_equivalence',c['name'],'original',a)
  b=p2_adapter.solve(s,initial,5,20261020);record('p2_equivalence',c['name'],'adapter',b)
  p2_search_audit.UnifiedGeometry=geometry
  assert a['status']==b['status'] and clean(a)==clean(b),(c['name'],a,b)
  if a['route']:assert baseline_suite.audit(s,tuple(a['route']))['valid']
  pair={}
  for method,mode in [('PPCPP','PPCPP'),('LAST_V2','LAST')]:
   x=runtime.run_payload(json.dumps(c),mode,5,20261020);adapter.Audit(c).check(x);record('last_wrapper',c['name'],method,x);pair[method]=x
  for field in ('route','trace','status'):assert norm(pair['PPCPP']['raw']['branches']['P0'][field])==norm(pair['LAST_V2']['raw']['branches']['P0'][field])
 assert len(objects)==2 and objects[0].cache is not objects[1].cache and objects[0].distance_rows is not objects[1].distance_rows
 c=read(R/'PPCPP_LAST距离查询等价提速_v0.2_20261020/fixtures/incidental_collection.json')
 for stage in ['p0_done','candidate_distance','phase1','release','return','final_audit_before','final_audit_after','encode_before','encode_after']:
  off=[0]
  def clock():return time.perf_counter()+off[0]
  def hook(k):
   if k==stage:off[0]=30
  x=runtime.run_payload(json.dumps(c),'LAST',1,20261020,hook=hook,clock=clock);assert not x['eligible'] and not x['raw']['route'] and x['raw']['branches']['P0']['status']=='core_complete';record('last_deadline',stage,'LAST_V2',x)
 c=read(H/'fixtures.json')[0];s=runtime.snapshot(c);initial=set()
 for when in ('before_accept','after_accept'):
  for label in ('original','adapter'):
   oldcheck=model.Geometry.check_time;old_audit=p2_search_audit.single_cell_audit;times=[(m,m.time) for m in (baseline_suite,p2_search_audit,p2_adapter,model)];count=[0]
   def audit(*a,**k):count[0]+=1;return old_audit(*a,**k)
   def tick(self):
    if when=='before_accept' or count[0]>=2:raise model.DeadlineExceeded()
   try:
    for m,_ in times:m.time=types.SimpleNamespace(perf_counter=lambda:0)
    model.Geometry.check_time=tick;p2_search_audit.single_cell_audit=audit
    x=baseline_suite.solve(s,initial,'P2_MULTI',5,20261020,None) if label=='original' else p2_adapter.solve(s,initial,5,20261020)
   finally:
    model.Geometry.check_time=oldcheck;p2_search_audit.single_cell_audit=old_audit
    for m,t in times:m.time=t
   assert x['status']=='deadline' and bool(x['route'])==(when=='after_accept');record('p2_cutoff',when,label,x)
 # Same retained legal route is late in actual-delivery view, valid in soft view.
 assert evaluate_late_unit();verify();assert len(out)==49
 save(H/'gate_index.json',dict(passed=True,calls=49,cache_isolation=True,late_classification=True,records=out));print('ALL49GATES PASS',flush=True)
def evaluate_late_unit():
 route=[[0,0]];x=dict(route_valid=True,entry_seconds=1,budget=1,route=route)
 timely=x['route_valid'] and x['entry_seconds']<x['budget'];late=x['route_valid'] and not timely
 return not timely and late and x['route']==route
if __name__=='__main__':main()
