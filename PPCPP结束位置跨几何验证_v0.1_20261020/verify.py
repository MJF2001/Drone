from common import *
from prepare import audit_inputs
from independent import certificate_audit
from equivalence import signature,exact_equal
def equivalences():
 olddir=R/'PPCPP小图最优差距诊断_v0.2_20261020/inputs';old={p.stem:read(p) for p in olddir.glob('*.json')};cases={p.stem:read(p) for p in (H/'inputs').glob('*.json')}
 signs={k:dict(shape=signature(c),state=signature(c,'state'),translation=signature(c,'state',False)) for k,c in cases.items()};shapes=sorted(set(s['shape'] for s in signs.values()));states=sorted(set(s['state'] for s in signs.values()));out={}
 for k,c in cases.items():
  s=signs[k];out[k]=dict(shape_group='G%02d'%(shapes.index(s['shape'])+1),state_group='S%02d'%(states.index(s['state'])+1),shape_signature=s['shape'],state_signature=s['state'],old_exact=[n for n,x in old.items() if exact_equal(c,x)],old_translation=[n for n,x in old.items() if s['translation']==signature(x,'state',False)],old_state_d4=[n for n,x in old.items() if s['state']==signature(x,'state')],old_shape_d4=[n for n,x in old.items() if s['shape']==signature(x)])
 return out
def verify():
 protect();inp=audit_inputs();assert read(H/'input_audit.json')==inp;eq=equivalences();rows=[];nq=0
 for g in read(H/'gates.json'):
  assert sha(R/g['input'])==g['input_sha256'] and sha(R/g['golden'])==g['golden_sha256']
  for k in ('route','trace'):assert g['result']['raw'][k]==read(R/g['golden'])['raw'][k]
 for slot,ir in zip(read(H/'protocol.json')['slots'],inp):
  name=slot['id'];c=read(H/'inputs'/f'{name}.json');row=dict(**slot,**eq[name],input_audit=ir)
  if not ir['valid']:row['status']='invalid';rows.append(row);continue
  x=read(H/'execution'/f'{name}.json');row.update(ppcpp_status=x['raw']['status'],entry_seconds=x['entry_seconds'],eligible=x['eligible']);queries={}
  t=points(c['targets'])-points(c['covered']);u=t-{tuple(c['current'])}
  for p in sorted((H/'exact'/name).glob('*.json')):
   if p.name.endswith('.request.json') or p.name=='mapping.json':continue
   r=read(p);req=read(p.with_suffix('.request.json'));assert req['input_sha256']==sha(H/'inputs'/f'{name}.json') and req['source_sha256']==sha(H/'exact.py')
   assert req['request']['free']==c['free']
   for k in ('start','base','targets','last'):assert req['request'][k]==r[k]
   assert r['start']==c['current'] and r['base']==c['base'] and points(r['targets'])==t
   certificate_audit(points(c['free']),r,p.with_suffix('.certificate.json.gz'));queries[p.stem]=r;nq+=1
   assert r['limits']==dict(seconds=60,states=800000)
   if r['status']=='optimal':assert r['length']<=1000000
   rc=H/'rechecks'/name/p.name
   if rc.exists():
    rcdata=read(rc);assert rcdata['result_sha256']==sha(p) and rcdata['request_sha256']==sha(p.with_suffix('.request.json'))
    if rcdata['status']=='complete':assert rcdata['length']==r['length']
  assert len(queries)<=3 and queries['A']['last'] is None
  row['query_statuses']={k:r['status'] for k,r in queries.items()}
  if not x['eligible']:rows.append(row);continue
  raw=x['raw'];pa.audit(c,raw);pm=metric(c,raw['route']);assert pm==cross(c,raw['route']);row.update(ppcpp_metrics=pm,has_recovery=any(e['kind']=='recovery' for e in raw['trace']))
  pending=set(t);e0=None
  for p in map(tuple,raw['route']):
   if p in pending:pending.remove(p);e0=p
  e0=e0 if u else None;mp=read(H/'exact'/name/'mapping.json');near=read(H/'candidates'/f'{name}.json');emin=tuple(near['emin']) if near['emin'] else None
  assert mp['e0']==(list(e0) if e0 else None) and mp['emin']==near['emin']
  expected=dict(A='A',B='B' if u else None,C=('B' if e0==emin else 'C') if u else None);assert mp['mapping']==expected
  row.update(mapping=expected,e0=list(e0) if e0 else None,emin=list(emin) if emin else None)
  a=queries['A'];row['Lp']=pm['length']
  if a['status']=='optimal':
   row.update(Lstar=a['length'],G=pm['length']-a['length'],relative_gap=(pm['length']-a['length'])/a['length'] if a['length'] else None,optimal_metrics=metric(c,a['route']));assert row['G']>=0 and row['optimal_metrics']==cross(c,a['route'])
  if u:
   b=queries['B'];q=queries[expected['C']];assert b['last']==list(e0) and q['last']==list(emin) and b['status']!='infeasible'
   row.update(near_status=q['status'],d_e0=near['distances'][str(e0)],d_emin=near['distances'][str(emin)])
   assert row['d_emin']<=row['d_e0']
   if b['status']=='optimal':row.update(L0=b['length'],fixed_original_metrics=metric(c,b['route']));assert row['fixed_original_metrics']==cross(c,b['route'])
   if a['status']=='optimal' and b['status']=='optimal':
    assert a['length']<=b['length']<=pm['length'];E=b['length']-a['length'];rr=pm['length']-b['length'];row.update(E=E,R=rr,E_over_G=E/row['G'] if row['G']>0 else None);assert row['G']==E+rr
   if q['status']=='optimal':
    row.update(Lnear=q['length'],near_minus_Lp=q['length']-pm['length'],fixed_near_metrics=metric(c,q['route']));assert row['fixed_near_metrics']==cross(c,q['route'])
    if 'L0' in row:row['near_minus_L0']=q['length']-row['L0']
    if 'Lstar' in row:row['near_minus_Lstar']=q['length']-row['Lstar'];assert row['near_minus_Lstar']>=0
  else:row['near_status']='not_applicable_empty'
  rows.append(row)
 assert len(rows)==36 and nq<=108
 if (H/'analysis.json').exists():assert read(H/'analysis.json')['states']==rows
 if (H/'manifest.json').exists():
  for f,h in read(H/'manifest.json').items():assert sha(H/f)==h,f
 return dict(states=rows,exact_queries=nq,verified=True,manifest_sealed=(H/'manifest.json').exists())
if __name__=='__main__':
 x=verify();x.pop('states');print(json.dumps(x,ensure_ascii=False))
