from pathlib import Path
import json,hashlib,math,collections
H=Path(__file__).resolve().parent;O=H/'各自进度前方障碍展示_v0.1_20261024'
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def pts(x):return set(map(tuple,x))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reachable(F,s):
 seen={tuple(s)};q=list(seen)
 for x,y in q:
  for a in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
   if a in F and a not in seen:seen.add(a);q.append(a)
 return seen

def main():
 d=read(O/'results.json');receipts=[]
 for w in d['worlds']:
  for s in w['sessions']:
   assert s['status']=='complete'
   route=s['route'];assert route[0]==w['initial']['base'] and route[-1]==w['initial']['base']
   assert all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(route,route[1:]))
   Hc=set();phase=0
   for i,p in enumerate(route):
    while phase+1<len(s['phases']) and s['phases'][phase+1]['start_step']<=i:phase+=1
    pp=s['phases'][phase];assert tuple(p) in pts(pp['free']);Hc|={tuple(p)}&pts(pp['published'])
   assert Hc==pts(s['covered']);assert pts(s['phases'][-1]['published'])-pts(s['phases'][-1]['free'])-Hc==pts(s['deferred'])
   assert pts(s['phases'][-1]['published'])&pts(s['phases'][-1]['free'])<=Hc
   for j,e in enumerate(s['events']):
    prev=s['phases'][j];nxt=s['phases'][j+1];step=e['step'];source=read(prev['source']);raw=source.get('result',source)['raw'];plan=raw['route'];cut=step-prev['start_step'];assert route[prev['start_step']:step+1]==plan[:cut+1] and e['old_route']==plan[cut:]
    HH=pts(route[:step+1])&pts(prev['published']);assert HH==pts(e['actual_history']);ratio=len(HH&pts(prev['free']))/len(pts(prev['published'])&pts(prev['free']));assert abs(ratio-e['ratio'])<1e-12 and ratio>=e['threshold']-1e-12
    if e['remove']:
     b=tuple(e['remove'][0]);assert len(e['remove'])==1 and b==tuple(plan[cut+1]) and b not in pts(route[:step+1]);assert b not in HH
     F=pts(prev['free'])-{b};assert (pts(prev['published'])&F)|{tuple(w['initial']['base'])}<=reachable(F,route[step]);assert pts(plan[cut+2:])&pts(prev['published'])-HH-{b}
    out=read(nxt['source']);job=out['job'];inp=read(job['input']);assert pts(inp['covered'])==HH and inp['current']==route[step] and inp['previous']==route[step-1];assert pts(inp['free'])==pts(nxt['free'])
   for p in s['phases']:assert sha(p['source'])==p['sha256']
   receipts.append(dict(world=w['id'],method=s['method'],passed=True,triggers=[{'threshold':e['threshold'],'actual':e['ratio'],'wait_steps':e['wait_steps'],'block':e['remove']} for e in s['events']]))
 for f,h in read(O/'protocol.json')['sources'].items():assert sha(f)==h
 (O/'independent_verify.json').write_text(json.dumps(dict(passed=True,receipts=receipts,results_sha256=sha(O/'results.json')),ensure_ascii=False,indent=2),encoding='utf-8');print('independent full replay and event checks passed',len(receipts))
if __name__=='__main__':main()
