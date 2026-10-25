from common import *
from geometry import geometry,case,witness
def main():
 protect();p=read(H/'protocol.json')
 assert read(H/'tests/results.json')['passed']
 for scale in ('s1','s2'):
  for shape in ('I','L'):
   name=f'{scale}_{shape}';dest=H/'prep'/f'{name}.json'
   if dest.exists():continue
   f,t,_=geometry(scale,shape);c=case(name,f,t,set(),(0,0),t,None,[(0,0)])
   result=solve_payload(json.dumps(c));assert result['eligible'];pa.audit(c,result['raw'])
   save(dest,dict(input=c,result=result));print('prepared',name,flush=True)
 for slot in p['cases']:
  dest=H/'inputs'/f"{slot['id']}.json"
  if dest.exists():continue
  prep=read(H/'prep'/f"{slot['base_id']}.json");c0=prep['input'];t0=points(c0['targets']);route=list(map(tuple,prep['result']['raw']['route']))
  goal=(len(t0)*slot['progress']+99)//100;h=set()
  for cut,q in enumerate(route):
   if q in t0:h.add(q)
   if len(h)>=goal:break
  prefix=route[:cut+1];f,pub,blocked=geometry(slot['scale'],slot['shape'],slot['event'],prefix[-1])
  c=case(slot['id'],f,pub,h,prefix[-1],t0,prefix[-2] if cut else None,route[cut:]);validation.validate(c)
  valid=len(f)<=48 and len(points(c['targets'])-h-{prefix[-1]})<=14
  w=witness(f,pub&f,h,prefix[-1]) if valid else []
  save(H/'witnesses'/f"{slot['id']}.json",dict(slot=slot,cut=cut,goal=goal,history=prefix,blocked=sorted(blocked),feasible_route=w,input_valid=valid))
  save(dest,c)
 audit_inputs()
 # Gate wrapper equivalence on two existing saved fixed inputs (not new slots).
 gates=[]
 upstream=R/'PPCPP结构候选新开发验证_v0.1_20261020'
 for name in ('small_A_straight_p25','small_B_obstacle_p60'):
  c=read(upstream/'inputs'/f'{name}.json');x=solve_payload(json.dumps(c));pa.audit(c,x['raw'])
  candidates=list((upstream/'execution').rglob('*.json'));gold=None
  for path in candidates:
   obj=read(path)
   if obj.get('job',{}).get('case_id')==name and obj['job'].get('method')=='PPCPP':gold=obj;break
  assert gold is not None
  assert json.loads(json.dumps(x['raw']['route']))==gold['raw']['route'] and json.loads(json.dumps(x['raw']['trace']))==gold['raw']['trace']
  gates.append(dict(name=name,source=str(path.relative_to(R)),source_sha256=sha(path),result=x,route_trace_equal=True))
 save(H/'gates.json',gates)
 save(H/'input_seal.json',{str(f.relative_to(H)):sha(f) for root in ('prep','inputs','witnesses','tests') for f in (H/root).rglob('*') if f.is_file()}|{'gates.json':sha(H/'gates.json'),'protocol.json':sha(H/'protocol.json')})
 print('24 slots audited and input/source sealed; 4 preparation + 2 existing-input wrapper gates',flush=True)
def audit_inputs():
 from independent import audit_route
 p=read(H/'protocol.json');rows=[]
 for s in p['cases']:
  c=read(H/'inputs'/f"{s['id']}.json");w=read(H/'witnesses'/f"{s['id']}.json");prep=read(H/'prep'/f"{s['base_id']}.json")
  # Independent footprint reconstruction (no generator geometry calls here).
  width=1 if s['scale']=='s1' else 2;W=7 if width==1 else 8
  f0={(x,y) for x in range(W) for y in range(6)}
  old={(x,y) for x,y in f0 if 1<=x<5 and 1<=y<1+width}
  if s['shape']=='L':old|={(x,y) for x,y in f0 if 5-width<=x<5 and 1+width<=y<3+width}
  assert points(prep['input']['free'])==f0 and points(prep['input']['targets'])==old and not prep['input']['covered']
  pa.audit(prep['input'],prep['result']['raw']);cut=w['cut'];route=prep['result']['raw']['route'];prefix=route[:cut+1];h=points(prefix)&old
  assert w['history']==prefix and len(h)==(len(old)*s['progress']+99)//100 and len(points(prefix[:-1])&old)<len(h)
  assert points(c['covered'])==h and c['current']==prefix[-1] and c['previous']==prefix[-2] and c['old_route']==route[cut:]
  pub=set(old);b=set()
  if s['event']=='obstacle':b={next(q for q in ((3,1),(4,1)) if list(q)!=c['current'])}
  elif s['event']=='straight':
   if s['shape']=='I':pub|={(x,y) for x,y in f0 if 5<=x<7 and 1<=y<1+width}
   else:pub|={(x,y) for x,y in f0 if 5-width<=x<5 and 3+width<=y<(5+width if width==1 else 4+width)}
  elif s['shape']=='I':pub|={(x,y) for x,y in f0 if 5-width<=x<5 and 1+width<=y<3+width}
  else:pub|={(x,y) for x,y in f0 if 3-width<=x<3 and 1+width<=y<3+width}
  assert points(c['free'])==f0-b and points(c['published_targets'])==pub and points(c['targets'])==pub-b
  assert points(c['deferred_targets'])==pub-(f0-b)-h and points(c['initial_targets'])==old and points(w['blocked'])==b
  assert c['base']==[0,0] and c['predator']==[-1,0] and c['distance_budget']==1000000
  validation.validate(c);assert len(c['free'])<=48 and len(points(c['targets'])-h-{tuple(c['current'])})<=14
  audit_route(points(c['free']),tuple(c['current']),(0,0),points(c['targets'])-h,w['feasible_route'])
  assert metric(c,w['feasible_route'])==cross(c,w['feasible_route'])
  rows.append(s['id'])
 return rows
if __name__=='__main__':main()
