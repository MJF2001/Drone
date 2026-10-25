"""Exactly four real local-engine invocations; injected hand P0 is explicitly a stub."""
from diag_common import *
hybrid,runtime=production()
def baseline_for(env):
 def stub(*a,**k):return dict(status='core_complete',route=tuple(map(tuple,env['state']['old_route'])),trace=[],reason=None,version='HAND_P0_STUB_NOT_PPCPP_SOLVE')
 return stub
def main():
 assert read(D/'environment_seal.json')['complete'];records=[]
 for name in ('redundant','optimal'):
  for mode in ('direct_local_with_production_accept','production_splice_with_hand_P0'):
   begin=time.perf_counter();env=read(D/'fixtures'/(name+'.json'));payload=json.dumps(env);stub=baseline_for(env)
   if mode=='direct_local_with_production_accept':
    holder={}
    def capture(s,b,v,seed,accept):
     holder.update(s=s,accept=accept)
     return dict(route=s.old_route,status='capture_stub',source='capture_stub',improvements=[dict(steps=len(s.old_route)-1,source='capture_stub')],events=[])
    extraction=hybrid.run(payload,20,20261020,baseline=stub,engine=capture)
    assert extraction['raw']['status']=='core_complete';s=holder['s'];assert set(s.targets)=={(1,0),(3,0)} and not s.covered and s.current==(0,0) and s.base==(4,0) and len(s.free)==5
    raw=hybrid.local_engine(s,20-(time.perf_counter()-begin),'multi',20261020,accept=holder['accept']);holder['accept'](raw['route'],'final_probe');wire=json.dumps(raw);elapsed=time.perf_counter()-begin
    result=dict(raw=raw,entry_seconds=elapsed,production_accept_reused=True,callback_extraction='pure stub,0 real solves',full_hybrid_tested=False)
   else:
    result=hybrid.run(payload,20,20261020,baseline=stub);assert result['raw']['status']=='core_complete';raw=result['raw']['local'];elapsed=result['entry_seconds'];result.update(full_hybrid_tested=False,note='Original production pipeline after P0 uses injected hand window, no frozen PPCPP core solve.')
   assert elapsed<20 and raw['status']=='finished' and len(raw['route'])-1==4 and raw['route']==tuple((i,0) for i in range(5))
   if name=='redundant':assert raw['source']!='old_suffix'
   else:assert raw['source']=='old_suffix'
   if mode.startswith('production'):assert result['raw']['selected']==('LOCAL_P2' if name=='redundant' else 'P0')
   record=dict(fixture=name,mode=mode,result=norm(result),true_local_engine_calls=1,true_PPCPP_calls=0,hand_distance_lower_bound=4,expected_optimum=4)
   save(D/'positive'/f'{len(records)}_{name}_{mode}.json',record);records.append(record)
 save(D/'positive_index.json',dict(passed=True,entries=4,local_engine_calls=4,PPCPP_calls=0,records=[dict(fixture=x['fixture'],mode=x['mode']) for x in records]));print('4 POSITIVE ENTRIES PASSED; 4 local engines,0 PPCPP')
if __name__=='__main__':main()
