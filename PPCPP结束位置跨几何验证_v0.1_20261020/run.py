from common import *
from exact import solve
def query_map(e0,emin,has_tasks):return dict(A='A',B='B' if has_tasks else None,C=('B' if e0==emin else 'C') if has_tasks else None)
def query(c,label,t,last):
 path=H/'exact'/c['name']/f'{label}.json'
 if path.exists():return read(path)
 path.parent.mkdir(parents=True,exist_ok=True)
 request=dict(free=c['free'],start=c['current'],base=c['base'],targets=sorted(t),last=last)
 save(path.with_suffix('.request.json'),dict(request=request,input_sha256=sha(H/'inputs'/f"{c['name']}.json"),source_sha256=sha(H/'exact.py')))
 r=solve(points(c['free']),tuple(c['current']),tuple(c['base']),t,last,certificate=path.with_suffix('.certificate.json.gz'));save(path,r)
 print(c['name'],label,r['status'],r['length'],r['discovered'],flush=True);return r
def main():
 protect();assert (H/'input_seal.json').exists()
 for s in read(H/'protocol.json')['slots']:
  c=read(H/'inputs'/f"{s['id']}.json");w=read(H/'witnesses'/f"{s['id']}.json")
  if not w['valid']:continue
  dest=H/'execution'/f"{s['id']}.json"
  if not dest.exists():save(dest,solve_payload(json.dumps(c)))
  out=read(dest);t=points(c['targets'])-points(c['covered']);query(c,'A',t,None)
  if not out['eligible']:continue
  pa.audit(c,out['raw']);pending=set(t);e0=None
  for p in map(tuple,out['raw']['route']):
   if p in pending:pending.remove(p);e0=p
  u=t-{tuple(c['current'])};e0=e0 if u else None;near=read(H/'candidates'/f"{s['id']}.json");emin=tuple(near['emin']) if near['emin'] else None
  mp=query_map(e0,emin,bool(u))
  if u:
   b=query(c,'B',t,e0);assert b['status']!='infeasible','B contradicted original legal route; STOP'
   if mp['C']=='C':query(c,'C',t,emin)
  dest=H/'exact'/c['name']/'mapping.json'
  if not dest.exists():save(dest,dict(mapping=mp,e0=e0,emin=emin))
 protect();print('fixed matrix complete; STOP',flush=True)
if __name__=='__main__':main()
