"""Fixed gates. No exact coverage solver; all audits outside entry timing."""
import time,sys,types
from common import *
from isolation import run,sources,select
from semantics import compare,p0_semantic,norm,semantic,last_capture
from runtime import native,snapshot,DeadlineExceeded
adapter=load('speed_gate_audit_adapter',H/'audit_adapter.py')
def main():
 protect();protocol=read(H/'protocol.json');records=[];paired=0;goldens=0
 assert sha(H/'runtime.py')==sha(R/'PPCPP_LAST新开发地图验证_v0.1_20261020/runtime.py')
 assert sha(H/'candidate_v1.py')==sha(R/'PPCPP_LAST新开发地图验证_v0.1_20261020/candidate.py')
 a=(H/'candidate_v1.py').read_bytes();b=(H/'candidate_v2.py').read_bytes()
 assert b.replace(b"VERSION='PPCPP_LAST_RESERVE_v0.2'",b"VERSION='PPCPP_LAST_RESERVE_v0.1'").replace(b'full.distance(s.base,q)',b'full.distance(q,s.base)')==a
 cache_gate=adapter.gate()
 def record(kind,name,c,method,x,auditor):
  checked=auditor.check(x);p=H/'gates'/f'{len(records):04d}.json'
  save(p,dict(kind=kind,name=name,input=c,method=method,result=norm(x),audit=norm(checked),last_capture=last_capture(c,x['raw']['route']) if x['eligible'] else None,production_sources=sources(method)))
  records.append(dict(kind=kind,name=name,method=method,path=str(p.relative_to(H))))
 for i,item in enumerate(protocol['inputs']):
  c=read(H/item['input']);payload=(H/item['input']).read_bytes();auditor=adapter.Audit(c);pair={};golden=read(R/item['golden']);seed=golden['job']['seed']
  for m in ('LAST_V1','LAST_V2'):
   x=run(payload,m,seed=seed);record('regression',item['id'],c,m,x,auditor);pair[m]=x
   if x['eligible'] and golden['eligible']:
    compare(x,golden);goldens+=1
    assert p0_semantic(x['raw']['branches']['P0'])==p0_semantic(read(R/item['golden_p0'])['raw']['branches']['P0'])
  paired+=compare(pair['LAST_V1'],pair['LAST_V2'])=='equal_complete'
  if (i+1)%12==0:print('regression',i+1,'/114',flush=True)
 for item in protocol['fixtures']:
  c=read(H/item['input']);auditor=adapter.Audit(c);pair={}
  for m in ('LAST_V1','LAST_V2'):
   x=run((H/item['input']).read_bytes(),m,seed=0);assert x['eligible'];record('fixture',item['id'],c,m,x,auditor);pair[m]=x
   if item['golden']:compare(x,read(R/item['golden'])['result'])
  compare(pair['LAST_V1'],pair['LAST_V2'])
  assert norm(last_capture(c,pair['LAST_V1']['raw']['route']))==norm(last_capture(c,pair['LAST_V2']['raw']['route']))
  p1=pair['LAST_V2']['raw']['branches'].get('P1')
  if item['id']=='mandatory_reserved':assert p1['status']=='reservation_infeasible'
  if item['id']=='base_removed_but_work_ok':assert p1['status']=='core_complete' and tuple(pair['LAST_V2']['raw']['e'])==tuple(c['base'])
 # Independently show that this fixture can expose a direction-sensitive connector.
 c=read(H/protocol['fixtures'][-1]['input']);s=snapshot(c);a=(1,0);b=(1,3)
 from model import Geometry
 raw_forward=Geometry(s,time.perf_counter()+20).path(a,b);raw_back=tuple(reversed(Geometry(s,time.perf_counter()+20).path(b,a)))
 assert raw_forward!=raw_back and len(raw_forward)==len(raw_back)==6
 g1=native.UnifiedGeometry(s,time.perf_counter()+20);g2=native.UnifiedGeometry(s,time.perf_counter()+20)
 d1=g1.distance(b,a);d2=g2.distance(a,b);q1=g1.path(b,a);q2=g2.path(b,a)
 assert d1==d2==5 and q1==q2
 direction=dict(raw_forward=raw_forward,raw_reverse_back=raw_back,unified_return=q1,distance=d1,first_v1=g1.first_direction,first_v2=g2.first_direction)
 direction['first_v1']=[dict(pair=k,value=v) for k,v in g1.first_direction.items()];direction['first_v2']=[dict(pair=k,value=v) for k,v in g2.first_direction.items()]
 save(H/'path_direction_gate.json',direction)
 # Actual collector: intermediate pending cells must be credited.
 for m in ('LAST_V1','LAST_V2'):
  mod=select(m);route=[(0,0)];pending={(1,0),(3,0)};mod.append_segment(route,pending,[(0,0),(1,0),(2,0),(3,0)],lambda _:None);assert not pending
 spies=[];c=read(H/'fixtures/incidental_collection.json')
 for m in ('LAST_V1','LAST_V2'):
  objects=[]
  class Spy(native.UnifiedGeometry):
   def __init__(self,*args,**kw):super().__init__(*args,**kw);objects.append(self)
  x=run(json.dumps(c),m,geometry=Spy);assert x['eligible'];record('cache_spy',m,c,m,x,adapter.Audit(c))
  assert len(objects)==3 and len({id(g.cache) for g in objects})==3 and len({id(g.distance_rows) for g in objects})==3
  assert objects[0].s.free==objects[1].s.free and objects[2].s.free==objects[0].s.free-{tuple(x['raw']['e'])}
  spies.append(dict(method=m,cache_objects=3,distinct=True,rows=[g.bfs_rows_built for g in objects]))
 save(H/'cache_gate.json',dict(spies=spies,collector=True,offline_audit_gate=cache_gate))
 for stage in protocol['deadline_stages']:
  offset=[0];hit=[]
  def clock():return time.perf_counter()+offset[0]
  def hook(k):
   if k==stage:hit.append(k);offset[0]=30
  x=run(json.dumps(c),'LAST_V2',hook=hook,clock=clock)
  assert hit and not x['eligible'] and x['raw']['status']=='deadline' and not x['raw']['route'] and x['raw']['selected'] is None
  assert x['raw']['branches']['P0']['status']=='core_complete'
  record('deadline_injection',stage,c,'LAST_V2',x,adapter.Audit(c))
 # Fixed-clock injection reaches real BFSMetricGeometry.distance's internal loop.
 geom=native.UnifiedGeometry(snapshot(c),time.perf_counter()+20);model=sys.modules['model'];original_time=model.time;checks=[]
 def fixed_clock():
  value=0 if len(checks)<2 else 2;checks.append(value);return value
 geom.deadline=1;raised=False
 try:
  model.time=types.SimpleNamespace(perf_counter=fixed_clock)
  try:geom.distance((0,0),(3,1))
  except DeadlineExceeded:raised=True
 finally:model.time=original_time
 assert raised and checks==[0,0,2] and geom.bfs_rows_built==0 and not geom.distance_rows
 save(H/'bfs_internal_deadline.json',dict(passed=True,checks=checks,deadline=1,exception='DeadlineExceeded',stored_rows=geom.bfs_rows_built,scope='actual distance entry plus real BFS inner check_time; no production file changed'))
 # Primary distance-only diagnostics: two fresh graphs, original set traversal order.
 diagnostics=[]
 for item in protocol['inputs'][:54]:
  c=read(H/item['input']);s=snapshot(c);u=set(s.targets)-set(s.covered)-{s.current};v1=native.UnifiedGeometry(s,time.perf_counter()+20);v2=native.UnifiedGeometry(s,time.perf_counter()+20)
  d1={q:v1.distance(q,s.base) for q in u};d2={q:v2.distance(s.base,q) for q in u};assert d1==d2
  e1=min(u,key=lambda q:(d1[q],q)) if u else None;e2=min(u,key=lambda q:(d2[q],q)) if u else None;assert e1==e2
  diagnostics.append(dict(id=item['id'],pending=len(u),current_is_base=s.current==s.base,base_in_pending=s.base in u,zero_distances=sum(v==0 for v in d1.values()),v1_rows=v1.bfs_rows_built,v2_rows=v2.bfs_rows_built,e=e1,distances=[dict(q=q,distance=d1[q]) for q in sorted(u)]))
 save(H/'distance_diagnostics.json',diagnostics)
 protect();assert len(records)==259
 save(H/'gate_index.json',dict(passed=True,calls=len(records),regression_pairs_complete=paired,golden_comparisons=goldens,fixture_pairs=10,deadline_injections=9,cache_spy_calls=2,geometry_diagnostics=54,exact_calls=0,index=records))
 seal={str(p.relative_to(H)):sha(p) for p in H.glob('*.py')}
 for n in ('protocol.json','formal_order.json','input_seal.json','预登记.md','minimal_candidate.diff','gate_index.json','bfs_internal_deadline.json','cache_gate.json','path_direction_gate.json','distance_diagnostics.json'):seal[n]=sha(H/n)
 save(H/'source_seal.json',dict(files=seal,phase='all fixed gates passed before any formal call',actual_sources={m:sources(m) for m in protocol['methods']}))
 print('ALL GATES PASSED',len(records),'planner calls;',paired,'fresh complete pairs;',goldens,'old golden checks',flush=True)
if __name__=='__main__':main()
