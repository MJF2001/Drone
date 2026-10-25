from support import *
import entry,hybrid
from audit import check,checked_metric
from environment import verify
def stubs():
 c=read(H/'fixtures.json')[2]['state'];env=dict(state=c,marker=[(1,1)]);base_route=[(0,0),(1,0),(2,0),(3,0)];results=[]
 def base(*a,**k):return dict(status='core_complete',route=base_route,trace=[],reason=None)
 def engine(s,b,v,seed,accept):
  assert s.free==frozenset(pts(c['free'])) and s.base==(3,0) and s.current==(0,0) and s.old_route==tuple(base_route)
  accept(s.old_route,'old_suffix');return dict(route=s.old_route,status='finished',source='old_suffix',improvements=[dict(steps=len(s.old_route)-1,source='old_suffix',seconds=0)],events=[])
 payload=json.dumps(env)
 for stage in ['p0_before','p0_after','window_before','window_scan','local_before','local_offer','local_after','splice_check','final_check','encode_before','encode_after']:
  offset=[0];hit=[]
  def clock():return time.perf_counter()+offset[0]
  def hook(k):
   if stage==k:offset[0]=30;hit.append(k)
  x=hybrid.run(payload,20,0,clock=clock,hook=hook,baseline=base,engine=engine);assert hit and x['raw']['status']=='deadline' and not x['raw']['route'];results.append(dict(test=stage,result=x))
 x=hybrid.run(payload,20,0,baseline=base,engine=engine);assert x['raw']['selected']=='P0';results.append(dict(test='tie',result=x))
 def invalid(s,b,v,seed,accept):accept([(0,0),(3,0)],'invalid')
 def error(*a,**k):raise RuntimeError('fixed_stub_exception')
 for label,stub in [('invalid',invalid),('exception',error)]:
  x=hybrid.run(payload,20,0,baseline=base,engine=stub);assert x['raw']['status'] in ('candidate_invalid','exception') and not x['raw']['route'];results.append(dict(test=label,result=x))
 # Same required tasks, valid detour P0, strictly shorter complete patch.
 detour=[(0,0),(1,0),(0,0),(1,0),(2,0),(3,0)]
 def longbase(*a,**k):return dict(status='core_complete',route=detour,trace=[])
 def shorter(s,b,v,seed,accept):
  accept(base_route,'stub_short');return dict(route=base_route,status='finished',source='stub_short',improvements=[dict(steps=3,source='stub_short',seconds=0)],events=[])
 x=hybrid.run(payload,20,0,baseline=longbase,engine=shorter);assert x['raw']['selected']=='LOCAL_P2';results.append(dict(test='strict_shorter',result=x))
 # An explicitly forced patch crosses a future suffix target; suffix remains literal.
 c=norm(read(H/'fixtures.json')[7]['state']);c.update(current=[0,0],base=[3,0],targets=[[0,1],[1,0]],published_targets=[[0,1],[1,0]],initial_targets=[[0,1],[1,0]])
 original=[(0,0),(0,1),(0,2),(1,2),(2,2),(3,2),(3,1),(2,1),(1,1),(1,0),(2,0),(3,0)];patch=[(0,0),(1,0),(1,1),(0,1),(0,2)]
 def forcedbase(*a,**k):return dict(status='core_complete',route=original,trace=[])
 def forced(s,b,v,seed,accept):
  assert s.targets==frozenset({(0,1)}) and s.base==(0,2);accept(patch,'forced_external');return dict(route=patch,status='finished',source='forced_external',improvements=[dict(steps=4,source='forced_external',seconds=0)],events=[])
 x=hybrid.run(json.dumps(dict(state=c,marker=[(-1,1)])),20,0,baseline=forcedbase,engine=forced);assert x['raw']['status']=='core_complete';full=x['raw']['assembled_route'];assert list(map(tuple,full[-len(original[2:])+1:]))==original[3:]
 m=checked_metric(c,full);assert m['repeated_new_target_steps']>=1 and (1,0) in map(tuple,full[:5]);results.append(dict(test='forced_external_capture_literal_suffix',result=x,metrics=m,note='Forced route probe; not a claim every feasible graph path must pass this target. Original valid window itself disproves that topology.'))
 return norm(results)
def main():
 verify();fixtures=read(H/'fixtures.json');index=[]
 for env in fixtures:
  pair={}
  for method in ('PPCPP','LOCAL_P2'):
   x=norm(entry.run(json.dumps(env),method,20,20261020));a=check(env,x,method);dest=H/'gates'/f'{len(index):03d}.json';save(dest,dict(input=env,method=method,result=x,audit=a));index.append(str(dest.relative_to(H)));pair[method]=x
  a=pair['PPCPP']['raw'];b=pair['LOCAL_P2']['raw']['P0']
  for field in ('route','trace','status'):assert a[field]==b[field]
  if env['state']['name']=='resource':assert not pair['LOCAL_P2']['raw']['route']
  else:assert pair['LOCAL_P2']['raw']['status']=='core_complete'
  print('gate',len(index),env['state']['name'],flush=True)
 results=stubs();save(H/'stub_gates.json',results);verify();assert len(index)==24
 save(H/'gate_index.json',dict(passed=True,entries=24,records=index,stub_tests=len(results),internal_calls={key:sum(read(H/p)['result']['raw'].get('internal_calls',{}).get(key,0) for p in index) for key in ('PPCPP','local_P2')}))
 print('ALL24 REAL GATES + STUBS PASS')
if __name__=='__main__':main()
