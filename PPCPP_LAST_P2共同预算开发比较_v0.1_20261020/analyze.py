"""Offline dual-view audit; zero planner invocations."""
import csv,itertools,statistics
from collections import Counter,defaultdict
from support import *
import common
adapter=load('comparison_last_audit',H/'audit_adapter.py')
METHODS=['PPCPP','LAST_V2','P2_MULTI'];PAIRS=[('LAST_V2','PPCPP'),('LAST_V2','P2_MULTI'),('PPCPP','P2_MULTI')]
def stats(v):
 a=sorted(v)
 if not a:return dict(N=0)
 z=(len(a)-1)*.95;i=int(z)
 return dict(N=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i),max=max(a))
def paired(calls,a,b,view):
 groups=defaultdict(dict)
 for x in calls:groups[x['case_id'],x['repetition']][x['method']]=x
 rr=[]
 for key,g in groups.items():
  x,y=g.get(a),g.get(b)
  if x and y and x[view] and y[view]:rr.append(dict(case_id=key[0],repetition=key[1],a=x['metrics']['length'],b=y['metrics']['length'],delta=x['metrics']['length']-y['metrics']['length'],relative=(x['metrics']['length']-y['metrics']['length'])/y['metrics']['length'] if y['metrics']['length'] else None,a_seconds=x['entry_seconds'],b_seconds=y['entry_seconds'],a_late=x['late_valid'],b_late=y['late_valid']))
 return dict(a=a,b=b,view=view,N=len(rr),short=sum(r['delta']<0 for r in rr),equal=sum(r['delta']==0 for r in rr),long=sum(r['delta']>0 for r in rr),a_total=sum(r['a'] for r in rr),b_total=sum(r['b'] for r in rr),delta=sum(r['delta'] for r in rr),mean_relative=statistics.mean(r['relative'] for r in rr if r['relative'] is not None) if rr else None,pairs=rr)
def summaries(calls):
 out={}
 for b in (1,20):
  cc=[x for x in calls if x['budget']==b]
  counts={}
  for m in METHODS:
   xs=[x for x in cc if x['method']==m]
   counts[m]=dict(N=len(xs),valid=sum(x['route_valid'] for x in xs),timely=sum(x['timely_valid'] for x in xs),late=sum(x['late_valid'] for x in xs),no_route=sum(not x['has_returned_route'] for x in xs),invalid=sum(x['has_returned_route'] and not x['route_valid'] for x in xs),native_status=dict(Counter(x['native_status'] for x in xs)),sources=dict(Counter(str(x['route_source']) for x in xs)),overrun_gt_10ms=sum(x['overrun_seconds']>.01 for x in xs),overrun=stats([x['overrun_seconds'] for x in xs]),entry=stats([x['entry_seconds'] for x in xs]),external_audit=stats([x['external_audit_seconds'] for x in xs]),native_seconds=stats([x['native_seconds'] for x in xs if x['native_seconds'] is not None]))
  out[str(b)]=dict(counts=counts,comparisons=[paired(cc,a,z,v) for a,z in PAIRS for v in ('timely_valid','route_valid')])
 return out
def compute():
 assert read(H/'completion.json')['completed'];protocol=read(H/'protocol.json');inputs={i['id']:i for i in protocol['inputs']};auditors={};calls=[];p0pairs=0;groups=defaultdict(dict);seal=read(H/'environment_seal.json')['files']
 for row in read(H/'formal_order.json'):
  path=next((H/'execution').glob(f'{row["sequence"]:04d}__*.json'));x=read(path);assert not x.get('technical_failure');j=x['job'];assert all(row[k]==j[k] for k in row)
  assert sha(j['input'])==j['input_sha256']==inputs[j['case_id']]['sha256'];assert x['runtime_reads']==[str(Path(j['input']).resolve())]
  assert j['environment_seal_sha256']==sha(H/'environment_seal.json')
  for p,h in x['production_hashes'].items():assert seal[p]==h
  assert not any(Path(p).resolve()==H/'analyze.py' or Path(p).name=='exact.py' for p in x['imported_modules'])
  c=read(j['input']);raw=x['raw'];route=raw['route'];t=time.perf_counter();metrics=None;error=None
  if j['method']!='P2_MULTI':
   if j['case_id'] not in auditors:auditors[j['case_id']]=adapter.Audit(c)
   auditors[j['case_id']].check(x)
  if route:
   try:
    metrics=common.metric(c,route);assert metrics==common.cross(c,route)
   except Exception as exc:error=repr(exc)
  valid=bool(metrics and metrics['complete_legal']);elapsed=time.perf_counter()-t
  if j['method']=='P2_MULTI' and route:
   assert raw['improvements'] and raw['source']==raw['improvements'][-1]['source'] and len(route)-1==raw['improvements'][-1]['steps']
   assert all(a['steps']>b['steps'] for a,b in zip(raw['improvements'],raw['improvements'][1:]));assert all(e.get('status') in ('completed','deadline',None) for e in raw['events'])
   assert raw['fallback_selected']==(raw['source'] in ('old_suffix','common_fallback','common_old_suffix','common_GD_adapter'))
  rec=dict(**row,output=str(path.relative_to(H)),native_status=raw['status'],has_returned_route=bool(route),route_valid=valid,timely_valid=valid and x['entry_seconds']<j['budget'],late_valid=valid and x['entry_seconds']>=j['budget'],entry_seconds=x['entry_seconds'],native_seconds=raw.get('seconds',raw.get('branches',{}).get('P0',{}).get('seconds')),external_audit_seconds=elapsed,overrun_seconds=max(0,x['entry_seconds']-j['budget']),route_source=raw.get('source',raw.get('selected')),fallback_selected=raw.get('fallback_selected',False),metrics=metrics,metric_error=error,phases=x['phase_seconds'],native_accept_seconds=raw.get('improvements',[])[-1]['seconds'] if raw.get('improvements') else None)
  calls.append(rec);groups[j['case_id'],j['budget'],j['repetition']][j['method']]=x
 for key,g in groups.items():
  a=g['PPCPP']['raw']['branches'].get('P0');b=g['LAST_V2']['raw']['branches'].get('P0')
  if a and b and a['status']==b['status']=='core_complete':
   for f in ('route','trace','status'):assert a[f]==b[f]
   p0pairs+=1
 states=[]
 for i in protocol['inputs']:
  for budget in (1,20):
   for m in METHODS:
    xs=[x for x in calls if x['case_id']==i['id'] and x['budget']==budget and x['method']==m];lengths=[x['metrics']['length'] if x['route_valid'] else None for x in xs];routes=[groups[i['id'],budget,r][m]['raw']['route'] for r in range(3)]
    traces=[groups[i['id'],budget,r][m]['raw'].get('trace') for r in range(3)]
    states.append(dict(case_id=i['id'],size=i['size'],family=i['family'],event=i['event'],progress=i['progress'],budget=budget,method=m,lengths=lengths,mean=statistics.mean(lengths) if all(v is not None for v in lengths) else None,min=min(v for v in lengths if v is not None) if any(v is not None for v in lengths) else None,max=max(v for v in lengths if v is not None) if any(v is not None for v in lengths) else None,timely=sum(x['timely_valid'] for x in xs),stable_route=all(r==routes[0] for r in routes),stable_trace=all(t==traces[0] for t in traces),entry_times=[x['entry_seconds'] for x in xs]))
 strata=[]
 for factor in ('size','family','event','progress'):
  for value in sorted({i[factor] for i in protocol['inputs']}):
   ids={i['id'] for i in protocol['inputs'] if i[factor]==value};strata.append(dict(factor=factor,value=value,states=len(ids),summary=summaries([x for x in calls if x['case_id'] in ids])))
 totals=[]
 for b in (1,20):
  for view in ('timely_valid','route_valid'):
   for m in METHODS:
    xs=[x['metrics'] for x in calls if x['method']==m and x['budget']==b and x[view]];keys=[k for k,v in xs[0].items() if isinstance(v,(float,int)) and not isinstance(v,bool) and v is not None] if xs else []
    totals.append(dict(budget=b,view=view,method=m,N=len(xs),totals={k:sum(x[k] for x in xs) for k in keys if all(x[k] is not None for x in xs)}))
 return norm(dict(calls=calls,states=states,summary=summaries(calls),strata=strata,metric_totals=totals,P0_pairs=p0pairs))
def csvout(name,rows):
 with (H/name).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)
def main():
 d=compute();save(H/'analysis.json',d)
 csvout('972调用与完整指标.csv',[dict(**{k:v for k,v in x.items() if k not in ('metrics','phases')},phases=json.dumps(x['phases']),**{('metric_'+k):v for k,v in (x['metrics'] or {}).items()}) for x in d['calls']])
 csvout('324状态预算方法三种子.csv',[dict(**r,lengths=json.dumps(r['lengths']),entry_times=json.dumps(r['entry_times'])) for r in d['states']])
 csvout('双视图配对.csv',[dict(budget=b,**{k:v for k,v in c.items() if k!='pairs'}) for b,s in d['summary'].items() for c in s['comparisons']])
 save(H/'failures.json',dict(technical_failures=0,gate_failures=0,formal_calls=972,gate_calls=49,deadline_and_late='See every native_status/route_valid/timely_valid/late_valid in analysis; native deadline is NOT synonymous with no route.',environment_scope_correction='Initial import discovery retained as environment_discovery_v01.json; audit/input/config scope completed and resealed as final9381 files before any49 gate calls. No post-run supplementation.',invalid=[x for x in d['calls'] if x['has_returned_route'] and not x['route_valid']]))
 print(json.dumps(dict(summary=d['summary'],P0_pairs=d['P0_pairs']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
