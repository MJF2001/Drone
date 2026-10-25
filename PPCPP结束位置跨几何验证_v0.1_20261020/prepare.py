from common import *
from spec import plans,before,after,make_case,feasible,nearest
from independent import audit_route
def reconstruct(p,event=None,current=None):
 # Independent direct coordinate predicates, no generator calls.
 narrow=p['scale']=='narrow';family=p['family'];W=7 if narrow else 8;f={(x,y) for x in range(W) for y in range(6)}
 if narrow:
  if family=='I':old={(x,2) for x in (1,2,3)}
  elif family=='L':old={(1,2),(2,2),(3,2),(3,3),(3,4)}
  else:old={(1,1),(2,1),(2,2),(2,3),(3,3),(4,3)}
  extras={'I':dict(straight={(4,2),(5,2)},corner={(3,3),(3,4)}),'L':dict(straight={(3,5)},corner={(4,4),(5,4)}),'Z':dict(straight={(5,3),(6,3)},corner={(4,4),(4,5)})}
  obs={'I':[(2,2),(3,2)],'L':[(3,3),(3,4)],'Z':[(2,2),(3,3)]}[family]
 else:
  old={(x,y) for x in (1,2,3) for y in (1,2)}
  if family in ('L','Z'):old|={(2,3),(3,3)}
  if family=='Z':old|={(x,y) for x in (4,5) for y in (2,3)}
  extras={'I':dict(straight={(x,y) for x in (4,5) for y in (1,2)},corner={(x,y) for x in (2,3) for y in (3,4)}),'L':dict(straight={(x,y) for x in (2,3) for y in (4,5)},corner={(x,y) for x in (4,5) for y in (2,3)}),'Z':dict(straight={(6,2),(6,3)},corner={(x,y) for x in (4,5) for y in (4,5)})}
  obs={'I':[(2,1),(3,2)],'L':[(2,3),(3,3)],'Z':[(3,3),(4,3)]}[family]
 pub=set(old);b=set()
 if event=='obstacle':
  ok=[q for q in obs if q!=current and q!=(0,0) and q in old&f]
  if ok:b={ok[0]};f-=b
 elif event:pub|=extras[family][event]
 return f,old,pub,b
def audit_inputs():
 rows=[]
 for s in read(H/'protocol.json')['slots']:
  c=read(H/'inputs'/f"{s['id']}.json");w=read(H/'witnesses'/f"{s['id']}.json");prep=read(H/'prep'/f"{s['base_id']}.json");initial=prep['input'];validation.validate(initial);pa.audit(initial,prep['result']['raw'])
  f0,old,_,_=reconstruct(s);assert points(initial['free'])==f0 and points(initial['targets'])==old and not initial['covered']
  route=prep['result']['raw']['route'];prefix=route[:w['cut']+1];h=points(prefix)&old;cur=tuple(prefix[-1]);f,_,pub,b=reconstruct(s,s['event'],cur)
  assert w['history']==prefix and len(h)==(len(old)*s['progress']+99)//100 and len(points(prefix[:-1])&old)<len(h)
  assert c['current']==prefix[-1] and c['previous']==prefix[-2] and c['old_route']==route[w['cut']:]
  assert points(c['free'])==f and points(c['published_targets'])==pub and points(c['targets'])==pub&f and points(c['covered'])==h and points(c['initial_targets'])==old
  assert points(c['deferred_targets'])==pub-f-h and points(w['blocked'])==b
  assert c['base']==[0,0] and c['predator']==[-1,0] and c['distance_budget']==1000000;validation.validate(c)
  assert len(f)<=48 and len((pub&f)-h-{cur})<=14
  if s['event']!='obstacle':assert pub-old
  if w['valid']:
   audit_route(f,cur,(0,0),(pub&f)-h,w['feasible_route']);assert metric(c,w['feasible_route'])==cross(c,w['feasible_route'])
  # Independent graph distance via relaxation on all coordinate pairs.
  d={(0,0):0};front={(0,0)}
  while front:
   new={q for q in f-d.keys() if any(abs(q[0]-p[0])+abs(q[1]-p[1])==1 for p in front)}
   for q in new:d[q]=1+min(d[p] for p in front if abs(q[0]-p[0])+abs(q[1]-p[1])==1)
   front=new
  u=(pub&f)-h-{cur};near=read(H/'candidates'/f"{s['id']}.json")
  expected=min(u,key=lambda q:(d[q],q)) if u else None
  assert near['emin']==(list(expected) if expected else None)
  assert near['distances']=={str(q):d[q] for q in sorted(u)}
  rows.append(dict(id=s['id'],valid=w['valid'],pending=len(u),history=len(h),free=len(f),new_targets=len(pub-old),blocked_history=len(b&h),deferred=len(pub-f-h)))
 return rows
def main():
 protect();assert read(H/'tests/new_gates.json')['passed'] and len(read(H/'gates.json'))==2
 for p in plans():
  dest=H/'prep'/f"{p['base_id']}.json"
  if dest.exists():continue
  f,t=before(p['scale'],p['family']);c=make_case(p['base_id'],f,t,set(),(0,0),t,None,[(0,0)]);out=solve_payload(json.dumps(c));assert out['eligible'];pa.audit(c,out['raw']);save(dest,dict(input=c,result=out));print('prepared',p['base_id'],flush=True)
 for s in read(H/'protocol.json')['slots']:
  dest=H/'inputs'/f"{s['id']}.json"
  if dest.exists():continue
  prep=read(H/'prep'/f"{s['base_id']}.json");old=points(prep['input']['targets']);route=list(map(tuple,prep['result']['raw']['route']));h=set();goal=(len(old)*s['progress']+99)//100
  for cut,q in enumerate(route):
   if q in old:h.add(q)
   if len(h)>=goal:break
  prefix=route[:cut+1];f,pub,b,valid=after(s['scale'],s['family'],s['event'],prefix[-1]);c=make_case(s['id'],f,pub,h,prefix[-1],old,prefix[-2],route[cut:])
  validation.validate(c);valid=valid and len(f)<=48 and len(points(c['targets'])-h-{prefix[-1]})<=14 and (s['event']=='obstacle' or bool(pub-old));wit=feasible(c) if valid else None
  valid=valid and wit is not None
  save(dest,c);save(H/'witnesses'/f"{s['id']}.json",dict(cut=cut,history=prefix,goal=goal,blocked=sorted(b),valid=valid,feasible_route=wit));save(H/'candidates'/f"{s['id']}.json",nearest(c))
 rows=audit_inputs();save(H/'input_audit.json',rows)
 save(H/'input_seal.json',{str(p.relative_to(H)):sha(p) for folder in ('prep','inputs','witnesses','candidates','tests') for p in (H/folder).rglob('*') if p.is_file()}|{'gates.json':sha(H/'gates.json'),'protocol.json':sha(H/'protocol.json'),'input_audit.json':sha(H/'input_audit.json')})
 print('inputs/near candidates sealed',len(rows),'valid',sum(r['valid'] for r in rows),flush=True)
if __name__=='__main__':main()
