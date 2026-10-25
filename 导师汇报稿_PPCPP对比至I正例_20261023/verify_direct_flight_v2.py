from pathlib import Path
import json,math,hashlib,collections
H=Path(__file__).resolve().parent;O=H/'直达区域入口起飞展示_v0.2_20261024'
def read(p):return json.loads(p.read_text('utf-8'))
def ps(a):return set(map(tuple,a))
def length(p):return sum(math.dist(a,b) for a,b in zip(p,p[1:]))
def crossed(p,q):
 # Independent boundary partition: positive-length intersection with open cell.
 for a,b in zip(p,p[1:]):
  ts={0.,1.}
  for k in (0,1):
   if a[k]!=b[k]:
    for side in (-.5,.5):
     u=(q[k]+side-a[k])/(b[k]-a[k])
     if 0<u<1:ts.add(u)
  ts=sorted(ts)
  for lo,hi in zip(ts,ts[1:]):
   u=(lo+hi)/2
   if all(abs(a[k]+u*(b[k]-a[k])-q[k])<.5-1e-12 for k in (0,1)):return True
 return False
W=read(O/'worlds.json');records=[]
for w in W:
 assert w['status']=='complete';ini=w['initial'];P=ps(ini['published_targets']);q=tuple(w['obstacle']);F=ps(ini['free'])-{q};assert not ini['covered']
 for a in w['agents']:
  d=read(O/'outputs'/(a['initial']+'.json'));z=d['views'][a['view']];path=z['path'];prefix=a['path'];assert prefix==path[:len(prefix)] and prefix[0]==ini['base']
  assert not crossed(prefix,q) and crossed(a['old'],q) and len(a['H'])>=math.ceil(len(P)*.3) and len(a['H'])<len(P)
  k=len(prefix)-1;hh=set()
  for e in z['events']:
   if e.get('new') and (e['kind']=='collect_here' or e['edge']<k):hh.add(tuple(e['cell']))
  assert hh==ps(a['H'])
  nxt=read(O/'outputs'/(a['response']+'.json'));assert nxt['passed'] and nxt['independent']['passed'];assert ps(nxt['input']['covered'])==hh
  assert abs(length(prefix)-a['cut_distance'])<1e-8;assert a['full_path']==prefix+nxt['views'][a['view']]['path'][1:];assert not crossed(nxt['views'][a['view']]['path'],q)
  assert abs(length(a['full_path'])-a['length'])<1e-8 and ps(a['final_H'])==P-{q}
  assert {tuple(c) for c,t in a['credits']}==P-{q};assert a['full_path'][-1]==ini['base']
  # Independent connected component on remaining free cells.
  seen={tuple(prefix[-1])}; todo=list(seen)
  for x,y in todo:
   for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if n in F and n not in seen:seen.add(n);todo.append(n)
  assert (P-{q})|{tuple(ini['base'])}<=seen
  original=d['timing']['raw_common_end_to_end' if a['view'] in ['A','C0'] else 'combined_end_to_end'];later=nxt['timing']['raw_common_end_to_end' if a['view'] in ['A','C0'] else 'combined_end_to_end'];assert abs(a['seconds']-original-later)<1e-10
  records.append(dict(size=w['size'],view=a['view'],passed=True))
for path,digest in read(O/'source_guards.json').items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
receipt=dict(passed=True,sessions=len(records),records=records,worlds_sha256=hashlib.sha256((O/'worlds.json').read_bytes()).hexdigest(),ledger=read(O/'ledger.json'))
(O/'independent_verify.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print('12 full flights independently verified')
