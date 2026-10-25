from pathlib import Path
import json,hashlib,collections,math
H=Path(__file__).resolve().parent;O=H/'前方未飞覆盖路段受阻展示_v0.1_20261024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pts(a):return set(map(tuple,a))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 d=read(O/'results.json');p=read(O/'protocol.json');assert d['protocol']==p;checks=[]
 for f,v in p['sources'].items():assert sha(f)==v
 for c in p['cases']:
  prefix=list(map(tuple,c['prefix']));old=list(map(tuple,c['old_plan']));s=read(c['input']);assert s==json.loads(json.dumps(c['snapshot'])) and sha(c['input'])==c['input_sha256'];assert sha(c['prefix_source'])==c['prefix_source_sha256'];pr=read(c['prefix_source']);assert pr['raw']['route'][:len(prefix)]==c['prefix'] and pr['raw']['route']==c['old_plan']
  B=pts(c['marker']);assert len(B)==1 and not B&set(prefix);assert tuple(old[len(prefix)]) in B
  assert s['old_route']==c['old_plan'][len(prefix)-1:] and s['current']==c['prefix'][-1] and s['previous']==c['prefix'][-2]
  assert pts(s['covered'])==set(prefix)&pts(c['initial']['targets']);assert pts(s['free'])==pts(c['initial']['free'])-B
  assert pts(old[len(prefix)+1:])&pts(c['initial']['targets'])-set(prefix)-B
  F=pts(s['free']);reach={tuple(s['current'])};q=collections.deque(reach)
  while q:
   x,y=q.popleft()
   for n in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
    if n in F and n not in reach:reach.add(n);q.append(n)
  assert pts(s['targets'])|{tuple(s['base'])}<=reach
  def check(route):
   r=list(map(tuple,route));assert r[0]==tuple(s['current']) and r[-1]==tuple(s['base']);assert set(r)<=F
   assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]));assert pts(s['targets'])<=set(r)|pts(s['covered']);assert len(r)-1<=s['distance_budget']
  records={r['method']:r for r in d['records'] if r['case']==c['id']};assert len(records)==8
  for method,r in records.items():
   assert sha(r['source'])==r['source_sha256'];saved=read(r['source']);x=saved.get('result',saved);assert saved['job']['input_sha256']==c['input_sha256'] and saved['job']['method']==method;assert x['raw']['route']==r['route'];assert x['entry_seconds']==r['seconds'];check(r['route'])
   if method=='LOCAL_P2':assert x['raw']['P0']['route']==records['PPCPP']['route'];assert len(r['route'])<=len(records['PPCPP']['route'])
   if method=='ORIENT4':
    raw=x['raw'];assert raw['candidates'][0]['inverse']['route']==records['PPCPP']['route']
    for a in raw['candidates']:check(a['inverse']['route'])
    assert r['route']==next(a['inverse']['route'] for a in raw['candidates'] if a['degree']==raw['selected_degree'])
    assert len(r['route'])==min(len(a['inverse']['route']) for a in raw['candidates'])
   checks.append(dict(case=c['id'],method=method,remaining_steps=len(r['route'])-1,seconds=r['seconds'],timely=r['timely'],passed=True))
 assert len(read(O/'call_ledger.json'))==d['actual_entries']==24
 out=dict(passed=True,checks=checks,front_obstacle_all_next_step=True,actual_entries=24,new_verifier_calls=0,results_sha256=sha(O/'results.json'))
 (O/'independent_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print('PASS',len(checks),'real next-step obstacle cases',len(p['cases']))
if __name__=='__main__':main()
