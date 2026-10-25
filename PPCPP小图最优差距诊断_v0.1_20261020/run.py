from common import *
from exact import solve,VERSION
def checkpoints(raw):
 rec=[i for i,e in enumerate(raw['trace']) if e['kind']=='recovery'];out=[]
 for name,k,after in [('first_recovery_before',0,False),('first_recovery_after',0,True),('second_recovery_before',1,False)]:
  idx=None
  if len(rec)>k:
   j=rec[k];idx=raw['trace'][j+1]['index'] if after else raw['trace'][j]['index']
  out.append(dict(name=name,index=idx))
 return out
def query(c,label,start,t,last=None):
 dest=H/'exact'/c['name']/f'{label}.json'
 if dest.exists():return read(dest)
 dest.parent.mkdir(parents=True,exist_ok=True)
 req=dict(free=sorted(points(c['free'])),start=start,base=c['base'],targets=sorted(t),last=last)
 save(dest.with_suffix('.request.json'),dict(input_sha256=sha(H/'inputs'/f"{c['name']}.json"),implementation_sha256=sha(H/'exact.py'),request=req))
 r=solve(points(c['free']),tuple(start),tuple(c['base']),t,last,certificate=dest.with_suffix('.certificate.json.gz'))
 save(dest,r);print(c['name'],label,r['status'],r['length'],r['discovered'],flush=True);return r
def main():
 protect();assert read(H/'tests/results.json')['passed'] and (H/'input_seal.json').exists()
 for slot in read(H/'protocol.json')['cases']:
  c=read(H/'inputs'/f"{slot['id']}.json");w=read(H/'witnesses'/f"{slot['id']}.json")
  if not w['input_valid']:continue
  dest=H/'execution'/f"{slot['id']}.json"
  if not dest.exists():save(dest,solve_payload(json.dumps(c)))
  x=read(dest);t=points(c['targets'])-points(c['covered']);query(c,'global',c['current'],t)
  if not x['eligible']:continue
  pa.audit(c,x['raw']);route=list(map(tuple,x['raw']['route']));cache={};mapping=[]
  for cp in checkpoints(x['raw']):
   i=cp['index']
   if i is None:cp['query']=None
   elif i in cache:cp['query']=cache[i]
   else:
    label=cp['name'];query(c,label,route[i],t-set(route[:i+1]));cache[i]=label;cp['query']=label
   mapping.append(cp)
  unseen=set(t);last=None
  for q in route:
   if q in unseen:unseen.remove(q);last=q
  if last is not None:query(c,'fixed_last',c['current'],t,last)
  mp=H/'exact'/c['name']/'mapping.json'
  if not mp.exists():save(mp,dict(checkpoints=mapping,last=last))
 protect();print('fixed matrix finished; no next experiment',flush=True)
if __name__=='__main__':main()
