from pathlib import Path
import json,hashlib,collections
H=Path(__file__).resolve().parent;O=H/'分尺度严格受阻与综合展示_v0.3_20261024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pts(a):return set(map(tuple,a))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reach(F,p):
 seen={tuple(p)};q=collections.deque(seen)
 while q:
  x,y=q.popleft()
  for n in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
   if n in F and n not in seen:seen.add(n);q.append(n)
 return seen
def main():
 d=read(O/'results.json');checks=[]
 for f,v in d['protocol']['sources'].items():assert sha(f)==v
 for w in d['worlds']:
  assert w['status']=='complete', (w.get('id'),w['status'])
  if w['kind']=='reuse_single':
   assert sha(w['source'])==w['source_sha256'];v=read(Path(w['source']).parent/'independent_verification.json');assert v['passed'] and v['results_sha256']==w['source_sha256'];continue
  assert len(w['sessions'])==8;expected_events=5 if w['kind']=='mixed' else 1;assert len(w['events'])==expected_events
  for s in w['sessions']:
   assert len(s['phases'])==expected_events+1 and len(s['events'])==expected_events
   actual=[w['initial']['base']];Hdone=set();oldF=pts(w['initial']['free']);oldP=pts(w['initial']['published_targets']);phase_steps=[]
   for k,p in enumerate(s['phases']):
    F=pts(p['free']);P=pts(p['published']);assert p['start_step']==len(actual)-1
    if k:
     e=w['events'][k-1];B=pts(e.get('remove',[]));assert not B&pts(actual)
     previous=s['phases'][k-1];offset=p['start_step']-previous['start_step'];oldroute=previous['plan'][offset:]
     if B:
      assert B<=pts(oldroute);first=next(i for i,q in enumerate(oldroute) if tuple(q) in B);assert pts(oldroute[first+1:])&(oldP-Hdone-B)
      assert ((oldP-B)&F)|{tuple(w['initial']['base'])}<=reach(F,actual[-1])
     if w['kind']=='mixed':assert p['start_step']==e['trigger_step'];assert F==(oldF|pts(e['add_free']))-B;assert P==oldP|pts(e['add_targets'])
     assert s['events'][k-1]['step']==p['start_step']
    route=p['plan'];assert route[0]==actual[-1] and route[-1]==w['initial']['base'];assert pts(route)<=F;assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]));assert P&F<=Hdone|pts(route)
    if p.get('source'):
     assert sha(p['source'])==p['sha256'];r=read(p['source']);x=r.get('result',r);inp=read(r['job']['input']);assert sha(r['job']['input'])==r['job']['input_sha256'];assert x['raw']['route']==route and x['entry_seconds']==p['seconds'];assert pts(inp['covered'])==Hdone and inp['current']==actual[-1] and pts(inp['free'])==F and pts(inp['published_targets'])==P
     if k:assert inp['old_route']==oldroute and inp['previous']==actual[-2]
     assert len(route)-1<=inp['distance_budget']
     if s['method']=='ORIENT4' and k:
      raw=x['raw'];assert route==next(c['inverse']['route'] for c in raw['candidates'] if c['degree']==raw['selected_degree']);assert len(route)==min(len(c['inverse']['route']) for c in raw['candidates'])
    stop=(s['phases'][k+1]['start_step']-p['start_step']) if k+1<len(s['phases']) else len(route)-1
    assert 0<=stop<len(route)
    for i,q in enumerate(route[:stop+1]):
     if tuple(q) in P:Hdone.add(tuple(q))
     if i:actual.append(q)
    oldP=P;oldF=F
   assert actual==s['route'] and len(actual)-1==s['steps'] and Hdone==pts(s['covered']);assert pts(s['deferred'])==oldP-oldF-Hdone;assert Hdone|pts(s['deferred'])==oldP
   checks.append(dict(world=w['id'],method=s['method'],events=expected_events,steps=s['steps'],passed=True))
  assert len({tuple(map(tuple,s['covered'])) for s in w['sessions']})==1
 ledger=read(O/'call_ledger.json');assert len(ledger)==d['entries'];assert sum(not x.get('reused',False) for x in ledger)==d['new_entries']
 out=dict(passed=True,worlds=6,checked_sessions=len(checks),inherited_verified_sessions=8,checks=checks,new_solver_calls=0,results_sha256=sha(O/'results.json'))
 (O/'independent_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print('PASS',len(checks),'+8 inherited')
if __name__=='__main__':main()
