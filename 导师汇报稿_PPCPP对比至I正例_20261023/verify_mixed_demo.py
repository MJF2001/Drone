"""Independent saved-trajectory replay, no planner imports or calls."""
from pathlib import Path
import json,hashlib,math
H=Path(__file__).resolve().parent;R=H.parent;O=H/'六算法综合连续事件演示_v0.2'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pts(a):return set(map(tuple,a))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=read(O/'results.json');p=read(O/'protocol.json');assert d['protocol']==p
 for f,h in p['sources'].items():assert sha(R/f)==h
 assert sha(R/'七算法共同预算比较_v0.3_Cstar07_20261020/worker.py')==p['worker_sha256']
 checks=[]
 for s in d['sessions']:
  F=pts(p['initial']['free']);P=pts(p['initial']['published']);P0=set(P);prior=set(P);hist=set();actual=[tuple(p['initial']['base'])];previous_plan=None;previous_cut=0;times=[]
  assert len(s['phases'])==6 and len(s['events'])==5 and s['status']=='complete'
  for i,phase in enumerate(s['phases']):
   inp=read(O/'inputs'/(phase['result_id']+'.json'));res=read(O/'results'/(phase['result_id']+'.json'));plan=list(map(tuple,res['route']))
   assert pts(inp['covered'])==hist and pts(inp['free'])==F and pts(inp['published_targets'])==P
   assert pts(inp['initial_targets'])==prior and hist<=prior
   assert pts(inp['targets'])==P&F and pts(inp['deferred_targets'])==P-F-hist
   assert tuple(inp['current'])==actual[-1] and inp['previous']==(list(actual[-2]) if len(actual)>1 else None)
   assert inp['distance_budget']==p['initial']['distance_budget']-len(actual)+1
   assert inp['old_route']==([] if i==0 else [list(x) for x in previous_plan[previous_cut:]])
   assert plan[0]==actual[-1] and plan[-1]==tuple(p['initial']['base']) and set(plan)<=F
   assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(plan,plan[1:]))
   assert P&F<=hist|set(plan) and len(plan)-1<=inp['distance_budget']
   assert phase['plan']==res['route'] and phase['start_step']==len(actual)-1
   assert res['job']['method']==s['method'] and res['job']['seed']==p['seed']
   assert res['job']['input_sha256']==sha(O/'inputs'/(phase['result_id']+'.json'))
   cut=len(plan)-1
   for j,x in enumerate(plan):
    if x in P:hist.add(x)
    if j:actual.append(x)
    if i<5 and len(hist&P0)>=p['events'][i]['threshold']:
     cut=j;break
   assert phase['end_step']==len(actual)-1 and pts(phase['free'])==F and pts(phase['published'])==P
   times.append(res['entry_seconds']);assert math.isclose(phase['seconds'],times[-1],abs_tol=1e-12)
   if i<5:
    e=p['events'][i];obs=s['events'][i]
    assert obs['step']==len(actual)-1 and obs['initial_collected']==e['threshold'] and pts(obs['history'])==hist
    prior=set(P);P|=pts(e['add_targets']);F|=pts(e['add_free']);F-=pts(e['remove']);assert actual[-1] in F
   previous_plan=plan;previous_cut=cut
  assert [list(x) for x in actual]==s['route'] and pts(s['completed'])==hist and pts(s['deferred'])==P-F-hist
  assert hist|(P-F-hist)==P and actual[-1]==tuple(p['initial']['base']) and s['steps']==len(actual)-1
  assert math.isclose(s['total_seconds'],sum(times),abs_tol=1e-12) and s['timely']==all(t<=20.010 for t in times)
  vec=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(actual,actual[1:])];dots=[a[0]*b[0]+a[1]*b[1] for a,b in zip(vec,vec[1:])]
  assert s['turn90']==dots.count(0) and s['turn180']==dots.count(-1)
  checks.append(dict(method=s['method'],steps=s['steps'],seconds=sum(times),completed=len(hist),deferred=len(P-F-hist),events=[e['step'] for e in s['events']],passed=True))
 ledger=read(O/'call_ledger.json');assert len(ledger)==36 and sum(e['reused'] for e in ledger)==2
 out=dict(passed=True,checks=checks,successful_entries=36,actual_entries_including_prior_failed=37,verifier_planner_calls=0,results_sha256=sha(O/'results.json'),protocol_sha256=sha(O/'protocol.json'))
 (O/'independent_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
