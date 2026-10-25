from pathlib import Path
import json,math,hashlib
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
H=Path(__file__).resolve().parent;O=H/'直达ILZ紧邻三障碍展示_v0.1_20261024'
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def ps(x):return set(map(tuple,x))
def length(p):return sum(math.dist(a,b) for a,b in zip(p,p[1:]))
def firstcell(a,b):
 t=min(.5/abs(b[k]-a[k]) for k in (0,1) if b[k]!=a[k]);t+=min(1e-8,(1-t)*.001)
 return tuple(math.floor(a[k]+t*(b[k]-a[k])+.5) for k in (0,1))
def main():
 worlds=read(O/'worlds.json');checks=[];partial=[]
 for w in worlds:
  P=ps(w['initial']['published_targets']);base=w['initial']['base'];assert base in w['initial']['targets'] and not w['initial']['covered']
  for a in w['agents']:
   if a['status']!='complete':partial.append(dict(world=w['name'],view=a['view'],events=len(a['events']),reason='no eligible next-segment event; partial summary metrics excluded'));continue
   assert len(a['events'])==3;route=a['full_path'];assert route[0]==base and route[-1]==base
   assert abs(length(route)-a['length'])<1e-8;HH=set();F=ps(w['initial']['free']);expectedroute=[];cost=0;expectedcredits=[]
   for j,ph in enumerate(a['phases']):
    out=read(O/'outputs'/(ph['source']+'.json'));assert out['passed'] and out['independent']['passed'];assert ps(out['input']['free'])==F and ps(out['input']['covered'])==HH;assert out['views'][a['view']]['path']==ph['plan'];cost+=out['timing']['raw_common_end_to_end' if a['view'] in ('A','C0') else 'combined_end_to_end']
    if j<3:
     e=a['events'][j];k=e['prefix_count']-1-(a['events'][j-1]['prefix_count']-1 if j else 0);prefix=ph['plan'][:k+1];assert prefix[-1]==e['current'];assert ph['plan'][k:]==e['old'];assert abs(length(prefix)+ph['start_distance']-e['distance'])<1e-8
    else:prefix=ph['plan']
    expectedroute+=prefix if not expectedroute else prefix[1:]
    for ev in out['views'][a['view']]['events']:
     if ev.get('new') and (ev['kind']=='collect_here' or ev['edge']<len(prefix)-1):
      HH.add(tuple(ev['cell']))
      if ev['kind']=='collect_here':cd=ph['start_distance']
      else:
       ei=ev['edge'];qt=ev['evidence']['witness']['t'];cd=ph['start_distance']+length(ph['plan'][:ei+1])+math.dist(ph['plan'][ei],ph['plan'][ei+1])*qt['n']/qt['d']
      expectedcredits.append([ev['cell'],cd])
    if j<3:
     b=tuple(e['block']);assert b==firstcell(e['current'],e['next_endpoint']);assert max(abs(b[k]-e['current'][k]) for k in (0,1))==1
     assert not crossed(expectedroute,b) and crossed([e['current'],e['next_endpoint']],b);assert b not in HH and b in P&F
     assert ps(e['history'])==HH and abs(len(HH&F)/len(P&F)-e['ratio'])<1e-12 and e['ratio']>=e['threshold']-1e-12
     F.remove(b);seen={tuple(e['current'])};todo=list(seen)
     for x,y in todo:
      for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
       if q in F and q not in seen:seen.add(q);todo.append(q)
     assert (P&F)|{tuple(base)}<=seen
   assert expectedroute==route and HH==P&F and HH==ps(a['final_H']);assert {tuple(q) for q,t in a['credits']}==HH and len(a['credits'])==len(HH)
   assert len(expectedcredits)==len(a['credits']) and all(x[0]==y[0] and abs(x[1]-y[1])<1e-8 for x,y in zip(expectedcredits,a['credits']));assert abs(cost-a['seconds'])<1e-9;checks.append(dict(world=w['name'],view=a['view'],passed=True))
 for f,h in read(O/'source_guards.json').items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
 result=dict(passed=True,checks=checks,partial_exclusions=partial,worlds_sha256=hashlib.sha256((O/'worlds.json').read_bytes()).hexdigest());(O/'independent_verify.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(len(checks),'complete sessions;',len(partial),'qualification exclusions')
if __name__=='__main__':main()