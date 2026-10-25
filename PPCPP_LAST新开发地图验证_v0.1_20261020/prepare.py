from common import *
from spec import *
from call import call
from input_audit import audit_all
def main():
 protect();assert read(H/'preflight.json')['passed'];p=read(H/'protocol.json');defs={d['base_id']:d for d in p['definitions']}
 for name,d in defs.items():
  dest=H/'prep/inputs'/f'{name}.json'
  if not dest.exists():
   f,t=before(d);save(dest,case(name+'_initial',f,t,set(),(0,0),t,None,[(0,0)]))
  result=call(dest,H/'prep/results'/f'{name}.json','PPCPP',name,'preparation');assert not result.get('technical_failure'),name
  if result['eligible']:pa.audit(read(dest),result['raw']['branches']['P0'])
  print('prepared',name,result['raw']['status'],flush=True)
 for s in p['slots']:
  result=read(H/'prep/results'/f"{s['base_id']}.json")
  if not result['eligible']:continue
  dest=H/'inputs'/f"{s['id']}.json"
  if dest.exists():continue
  d=defs[s['base_id']];_,old=before(d);route=list(map(tuple,result['raw']['route']));goal=(len(old)*s['progress']+99)//100;h=set()
  for cut,q in enumerate(route):
   if q in old:h.add(q)
   if len(h)>=goal:break
  prefix=route[:cut+1];f,pub,b,choice,valid=after(d,s['event'],prefix[-1]);c=case(s['id'],f,pub,h,prefix[-1],old,prefix[-2],route[cut:]);wit=feasible(c) if valid else None
  save(dest,c);save(H/'witnesses'/f"{s['id']}.json",dict(history=prefix,cut=cut,blocked=sorted(b),obstacle_choice=choice,valid=valid and wit is not None,feasible_route=wit))
 rows=audit_all();save(H/'input_audit.json',rows)
 print('generated/audited',len(rows),'slots; no formal performance calls yet',flush=True)
if __name__=='__main__':main()
