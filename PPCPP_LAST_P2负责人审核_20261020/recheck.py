import json
from pathlib import Path
from collections import defaultdict
H=Path(__file__).resolve().parent
S=H.parent/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
groups=defaultdict(dict)
for p in (S/'execution').glob('*.json'):
 x=read(p);j=x['job'];c=read(Path(j['input']));r=list(map(tuple,x['raw']['route']))
 assert r and r[0]==tuple(c['current']) and r[-1]==tuple(c['base'])
 assert set(r)<=set(map(tuple,c['free']))
 assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]))
 assert set(map(tuple,c['targets']))<=set(map(tuple,c['covered']))|set(r)
 groups[j['budget'],j['case_id'],j['seed']][j['method']]=(len(r)-1,x['entry_seconds'])
assert len(groups)==324
out={}
for budget in (1,20):
 pairs=[v for (b,c,s),v in groups.items() if b==budget]
 assert len(pairs)==162
 late=sum(v['P2_MULTI'][1]>=budget for v in pairs)
 stats={}
 for view in ('returned','timely'):
  rows=[v for v in pairs if view=='returned' or (v['LAST_V2'][1]<budget and v['P2_MULTI'][1]<budget)]
  stats[view]=dict(N=len(rows),short=sum(v['LAST_V2'][0]<v['P2_MULTI'][0] for v in rows),equal=sum(v['LAST_V2'][0]==v['P2_MULTI'][0] for v in rows),long=sum(v['LAST_V2'][0]>v['P2_MULTI'][0] for v in rows),LAST=sum(v['LAST_V2'][0] for v in rows),P2=sum(v['P2_MULTI'][0] for v in rows))
 out[str(budget)]=dict(P2_late=late,comparisons=stats)
assert out['20']['comparisons']['timely']==dict(N=162,short=0,equal=38,long=124,LAST=16428,P2=13180)
assert out['1']['P2_late']==37 and out['1']['comparisons']['timely']['N']==125
(H/'recheck_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
