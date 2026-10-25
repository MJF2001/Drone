import copy,time
from common import *
from runtime import run_payload,native
audit_module=load('last_policy_independent_audit',H/'audit.py')
check,bfs=audit_module.check,audit_module.bfs
def fixture(name,f,t,current=(0,0),base=(0,0),h=set(),pub=None):
 pub=set(pub) if pub is not None else t|h
 return dict(name=name,free=sorted(f),targets=sorted(t),covered=sorted(h),published_targets=sorted(pub),deferred_targets=sorted(pub-f-h),current=current,base=base,previous=None,predator=(-1,0),initial_targets=sorted(pub),old_route=[current],distance_budget=1000000)
def fixtures():
 line={(x,0) for x in range(4)};square={(x,y) for x in range(4) for y in range(3)}
 return [fixture('empty',square,set(),current=(3,2)),fixture('single',square,{(2,1)}),fixture('current_credit',square,{(0,0),(2,1)}),fixture('tie',square,{(1,0),(0,1),(2,2)}),fixture('mandatory_reserved',line,{(1,0),(3,0)}),fixture('base_removed_but_work_ok',line,{(1,0),(2,0)},current=(3,0),base=(1,0)),fixture('obstacle_graph_distance',square-{(1,0),(1,1)},{(0,2),(2,0)}),fixture('incidental_collection',square,{(1,0),(2,1),(3,1)}),fixture('blocked_history',square-{(1,0)},{(2,1)},h={(1,0)},pub={(1,0),(2,1)})]
def normalize(x):return json.loads(json.dumps(x))
def main():
 protect();root=H/'gates';root.mkdir(exist_ok=True);log=[]
 def record(kind,name,c,mode,x):
  details=check(c,x);item=dict(kind=kind,name=name,input=c,method=mode,result=x,audit=details)
  save(root/f'{len(log):04d}.json',item);log.append(dict(kind=kind,name=name,method=mode,path=f'gates/{len(log):04d}.json'))
 # 180 fresh equivalence calls; the runner never loads exact references here.
 for case in read(H/'protocol.json')['cases']:
  c=read(R/case['input']);pristine=copy.deepcopy(c);outs={}
  for mode in ('PPCPP','ONE','LAST'):
   out=run_payload(json.dumps(c),mode);assert out['eligible'];record('development_equivalence',case['id'],c,mode,out);outs[mode]=out
  for mode in ('ONE','LAST'):
   for k in ('route','trace'):assert normalize(outs[mode]['raw']['branches']['P0'][k])==normalize(outs['PPCPP']['raw']['branches']['P0'][k])
  for k in ('route','trace'):assert normalize(outs['ONE']['raw'][k])==normalize(outs['PPCPP']['raw'][k])
  assert c==pristine
 # Synthetic gates, not added to formal input matrix. Exact tools are offline only.
 exact=load('last_gate_exact',R/'PPCPP小图最优差距诊断_v0.2_20261020/exact.py');bounds=[]
 for c in fixtures():
  outs={}
  for mode in ('PPCPP','ONE','LAST'):
   x=run_payload(json.dumps(c),mode);assert x['eligible'];record('fixture',c['name'],c,mode,x);outs[mode]=x
  x=outs['LAST'];p1=x['raw']['branches'].get('P1');u=points(c['targets'])-points(c['covered'])-{tuple(c['current'])}
  if p1:
   e=tuple(x['raw']['e']);r=exact.solve(points(c['free']),tuple(c['current']),tuple(c['base']),points(c['targets'])-points(c['covered']),e)
   if p1['status']=='core_complete':assert r['status']=='optimal' and len(p1['route'])-1>=r['length']
   bounds.append(dict(name=c['name'],result=r,p1_status=p1['status']))
  if c['name']=='mandatory_reserved':assert p1['status']=='reservation_infeasible' and x['raw']['selected']=='P0'
  if c['name']=='base_removed_but_work_ok':assert p1['status']=='core_complete' and tuple(x['raw']['e'])==tuple(c['base'])
  if c['name']=='tie':assert x['raw']['e']==(0,1)
  if c['name']=='obstacle_graph_distance':assert x['raw']['e']==(0,2)
 save(H/'gate_exact_bounds.json',bounds)
 # Exercise actual per-cell collection helper on a recovery-style segment
 # to a fixed far endpoint. Native nearest recovery cannot pass a nearer
 # pending cell, so this unit probe tests the collector separately.
 from candidate import append_segment
 path=[(0,0)];pending={(1,0),(3,0)};append_segment(path,pending,[(0,0),(1,0),(2,0),(3,0)],lambda _:None);assert not pending and len(path)==4
 # Inspect all full/work geometries and distinct caches, including base removal.
 spy=[]
 class Spy(native.UnifiedGeometry):
  def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);spy.append(self)
 c=fixtures()[7];x=run_payload(json.dumps(c),'LAST',geometry=Spy);assert x['eligible'];record('cache_isolation','spy',c,'LAST',x)
 assert len(spy)==3 and len({id(g.cache) for g in spy})==3 and len({id(g.distance_rows) for g in spy})==3
 assert spy[0].s.free==spy[1].s.free and spy[2].s.free==spy[0].s.free-{tuple(x['raw']['e'])}
 # Shared clock advance at all mandated post-P0 stages; P0 must remain only evidence.
 c=fixtures()[7];injections=[]
 for stage in read(H/'protocol.json')['gates']['deadline_stages']:
  offset=[0];hit=[]
  def clock():return time.perf_counter()+offset[0]
  def hook(k):
   if k==stage:hit.append(k);offset[0]=30
  x=run_payload(json.dumps(c),'LAST',hook=hook,clock=clock);assert hit and not x['eligible'] and x['raw']['status']=='deadline' and not x['raw']['route']
  assert x['raw']['branches']['P0']['status']=='core_complete';record('deadline_injection',stage,c,'LAST',x);injections.append(stage)
 # The baseline itself failing must not cause an alternative fallback.
 bad=copy.deepcopy(c);bad['distance_budget']=0;x=run_payload(json.dumps(bad),'LAST');assert not x['eligible'] and 'P1' not in x['raw']['branches'];record('original_failure','zero_distance_budget',bad,'LAST',x)
 save(H/'gate_index.json',dict(passed=True,calls=len(log),development_calls=180,fixture_calls=27,cache_spy_calls=1,deadline_calls=len(injections),original_failure_calls=1,exact_fixture_calls=len(bounds),collection_helper_probe=True,index=log))
 files={str(p.relative_to(H)):sha(p) for p in H.glob('*.py')}
 files.update({str(p.relative_to(H)):sha(p) for p in root.glob('*.json')});files.update({n:sha(H/n) for n in ('protocol.json','gate_index.json','gate_exact_bounds.json','预登记.md')})
 save(H/'source_seal.json',dict(files=files,phase='all fixed gates passed; before formal calls'));print('all gates passed',len(log),'calls; sources sealed',flush=True)
if __name__=='__main__':main()
