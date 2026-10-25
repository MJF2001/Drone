from common import *
from prepare import audit_inputs
from independent import certificate_audit
from run import checkpoints
def verify():
 protect();assert read(H/'tests/results.json')['passed'];assert len(audit_inputs())==24
 for g in read(H/'gates.json'):
  assert sha(R/g['source'])==g['source_sha256'];gold=read(R/g['source'])
  assert g['result']['raw']['route']==gold['raw']['route'] and g['result']['raw']['trace']==gold['raw']['trace']
 results=[];nq=0
 for slot in read(H/'protocol.json')['cases']:
  c=read(H/'inputs'/f"{slot['id']}.json");x=read(H/'execution'/f"{slot['id']}.json");qs={}
  for path in sorted((H/'exact'/slot['id']).glob('*.json')):
   if path.name=='mapping.json' or path.name.endswith('.request.json'):continue
   r=read(path);req=read(path.with_suffix('.request.json'));assert req['input_sha256']==sha(H/'inputs'/f"{slot['id']}.json") and req['implementation_sha256']==sha(H/'exact.py')
   for k in ('start','base','targets','last'):assert r[k]==req['request'][k]
   assert req['request']['free']==sorted(c['free']);certificate_audit(points(c['free']),r,path.with_suffix('.certificate.json.gz'));qs[path.stem]=r;nq+=1
  assert len(qs)<=5
  row=dict(**slot,ppcpp_status=x['raw']['status'],eligible=x['eligible'],global_status=qs['global']['status'],query_statuses={k:r['status'] for k,r in qs.items()},checkpoints=[])
  if not x['eligible']:results.append(row);continue
  pa.audit(c,x['raw']);raw=x['raw'];route=list(map(tuple,raw['route']));m=metric(c,route);assert m==cross(c,route);row['ppcpp_metrics']=m
  t=points(c['targets'])-points(c['covered']);glob=qs['global'];assert glob['start']==c['current'] and points(glob['targets'])==t and glob['last'] is None
  if glob['status']=='optimal':
   row.update(Lp=m['length'],Lstar=glob['length'],G=m['length']-glob['length'],relative_gap=(m['length']-glob['length'])/glob['length'] if glob['length'] else None,optimal_metrics=metric(c,glob['route']))
   assert row['G']>=0 and row['optimal_metrics']==cross(c,glob['route'])
  mapping=read(H/'exact'/slot['id']/'mapping.json');assert [dict(name=q['name'],index=q['index']) for q in mapping['checkpoints']]==checkpoints(raw)
  previous_D=-1
  for cp in mapping['checkpoints']:
   item=dict(cp);i=cp['index']
   if i is not None:
    q=qs[cp['query']];assert q['start']==list(route[i]) and points(q['targets'])==t-set(route[:i+1]) and q['last'] is None
    item['status']=q['status']
    if q['status']=='optimal' and glob['status']=='optimal':
     C=i+q['length'];D=C-glob['length'];rr=m['length']-C
     assert D>=0 and rr>=0 and D>=previous_D and D+rr==row['G'];previous_D=D;item.update(C=C,D=D,R=rr)
   row['checkpoints'].append(item)
  unseen=set(t);last=None
  for q in route:
   if q in unseen:unseen.remove(q);last=q
  assert mapping['last']==(list(last) if last else None)
  if last is not None:
   e=qs['fixed_last'];assert e['start']==c['current'] and points(e['targets'])==t and e['last']==list(last)
   if e['status']=='optimal' and glob['status']=='optimal':
    assert glob['length']<=e['length']<=m['length'];row.update(Le=e['length'],ending_cost=e['length']-glob['length'],same_ending_saving=m['length']-e['length'],fixed_last_metrics=metric(c,e['route']))
    assert row['fixed_last_metrics']==cross(c,e['route'])
  results.append(row)
 assert nq<=120
 if (H/'analysis.json').exists():assert read(H/'analysis.json')['states']==results
 if (H/'manifest.json').exists():
  for path,h in read(H/'manifest.json').items():assert sha(H/path)==h,path
 return dict(verified=True,states=results,exact_queries=nq,preparation_calls=4,official_ppcpp_calls=24,wrapper_gate_calls=2,source_sealed=True,manifest_sealed=(H/'manifest.json').exists())
if __name__=='__main__':
 x=verify();x.pop('states');print(json.dumps(x,ensure_ascii=False))
