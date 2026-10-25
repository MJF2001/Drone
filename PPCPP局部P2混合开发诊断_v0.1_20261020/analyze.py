"""Independent full/window/capture audits; no planner calls."""
import csv,statistics
from collections import defaultdict,Counter
from support import *
A=load('hybrid_independent_analysis',H/'audit.py')
METHODS=('PPCPP','LOCAL_P2','P2_MULTI')
def stats(xs):
 if not xs:return dict(N=0)
 a=sorted(xs);z=(len(a)-1)*.95;i=int(z)
 return dict(N=len(a),mean=statistics.mean(a),median=statistics.median(a),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i),max=max(a))
def summary(calls):
 groups=defaultdict(dict)
 for x in calls:groups[x['id'],x['repetition']][x['method']]=x
 counts={m:dict(N=len(xs),valid=sum(x['valid'] for x in xs),timely=sum(x['timely'] for x in xs),late=sum(x['late'] for x in xs),no_route=sum(not x['has_route'] for x in xs),status=dict(Counter(x['status'] for x in xs)),sources=dict(Counter(str(x['source']) for x in xs)),entry=stats([x['entry_seconds'] for x in xs]),external_audit=stats([x['external_audit_seconds'] for x in xs]),max_overrun=max(x['overrun'] for x in xs),overrun_gt_10ms=sum(x['overrun']>.01 for x in xs)) for m in METHODS for xs in [[x for x in calls if x['method']==m]]}
 pairs=[]
 for ref in ('PPCPP','P2_MULTI'):
  for view in ('timely','valid'):
   pp=[]
   for (ident,rep),g in groups.items():
    x=g.get('LOCAL_P2');y=g.get(ref)
    if x and y and x[view] and y[view]:pp.append(dict(id=ident,repetition=rep,local=x['metrics']['length'],reference=y['metrics']['length'],saved=y['metrics']['length']-x['metrics']['length']))
   pairs.append(dict(reference=ref,view=view,N=len(pp),short=sum(x['saved']>0 for x in pp),equal=sum(x['saved']==0 for x in pp),long=sum(x['saved']<0 for x in pp),local_total=sum(x['local'] for x in pp),reference_total=sum(x['reference'] for x in pp),saved=sum(x['saved'] for x in pp),mean_relative=statistics.mean(-x['saved']/x['reference'] for x in pp) if pp else None,pairs=pp))
 return dict(counts=counts,pairs=pairs)
def totals(ms):
 if not ms:return dict(N=0)
 keys=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','initial_credit','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','target_arrivals','duplicate_target_arrivals']
 d=dict(N=len(ms),**{k:sum(m[k] for m in ms) for k in keys});d.update(active_coverage=d['active_covered']/d['active_targets'] if d['active_targets'] else 1,published_coverage=d['published_covered']/d['published_targets'] if d['published_targets'] else 1,overlap_ratio=d['duplicate_target_arrivals']/d['target_arrivals'] if d['target_arrivals'] else None);return d
def compute():
 assert read(H/'completion.json')['entries']==324;protocol=read(H/'protocol.json');items={i['id']:i for i in protocol['inputs']};seal=read(H/'environment_seal.json');calls=[];raws={};p0_pairs=0
 for row in read(H/'formal_order.json'):
  path=next((H/'execution').glob(f'{row["sequence"]:03d}__*.json'));x=read(path);assert not x.get('technical_failure');j=x['job'];assert all(j[k]==row[k] for k in row);assert sha(j['input'])==j['input_sha256']==items[row['id']]['sha256'];assert x['runtime_reads']==[str(Path(j['input']).resolve())];assert j['environment_sha256']==sha(H/'environment_seal.json')
  for p,h in x['production_hashes'].items():assert seal['files'][p]==h
  env=read(j['input']);a=time.perf_counter();details=A.check(env,x,row['method']);external=time.perf_counter()-a;r=x['raw'];valid=bool(details.get('metrics',{}).get('complete_legal'));cfg=r.get('window');p0=r.get('P0');patch=r.get('local');raws[row['id'],row['repetition'],row['method']]=r
  calls.append(dict(**row,kind=items[row['id']]['kind'],pair=items[row['id']]['pair'],base_id=items[row['id']]['base_id'],family=items[row['id']]['family'],size=items[row['id']]['size'],progress=items[row['id']]['progress'],output=str(path.relative_to(H)),status=r['status'],has_route=bool(r['route']),valid=valid,timely=valid and x['entry_seconds']<20,late=valid and x['entry_seconds']>=20,source=r.get('selected',r.get('source','PPCPP')),entry_seconds=x['entry_seconds'],external_audit_seconds=external,overrun=max(0,x['entry_seconds']-20),phases=x['phase_seconds'],metrics=details.get('metrics'),audit=details,window=cfg,local_source=patch.get('source') if patch else None,local_status=patch.get('status') if patch else None,local_steps=len(patch['route'])-1 if patch and patch['route'] else None,original_patch_steps=len(cfg['original_patch'])-1 if cfg and not cfg['empty'] else None,internal_calls=r.get('internal_calls',dict(PPCPP=1 if row['method']=='PPCPP' else 0,global_P2=1 if row['method']=='P2_MULTI' else 0))))
 for ident in items:
  for rep in range(3):
   a=raws[ident,rep,'PPCPP'];b=raws[ident,rep,'LOCAL_P2']['P0']
   if a['status']==b['status']=='core_complete':
    for k in ('route','trace','status','seed','predator','initial_previous','weights'):assert a[k]==b[k]
    p0_pairs+=1
 states=[]
 for item in protocol['inputs']:
  rr=[x for x in calls if x['id']==item['id']];methods={}
  for method in METHODS:
   xs=[x for x in rr if x['method']==method];lengths=[x['metrics']['length'] if x['valid'] else None for x in xs];routes=[raws[item['id'],r,method]['route'] for r in range(3)]
   methods[method]=dict(lengths=lengths,mean=statistics.mean(lengths) if all(v is not None for v in lengths) else None,min=min(v for v in lengths if v is not None) if any(v is not None for v in lengths) else None,max=max(v for v in lengths if v is not None) if any(v is not None for v in lengths) else None,timely=sum(x['timely'] for x in xs),stable_route=routes[0]==routes[1]==routes[2],times=[x['entry_seconds'] for x in xs])
  hybrids=[x for x in rr if x['method']=='LOCAL_P2'];state=dict(**{k:item[k] for k in ('id','pair','kind','family','size','progress','base_id')},methods=methods,window=hybrids[0]['window'],selected=[x['source'] for x in hybrids],local_sources=[x['local_source'] for x in hybrids],saved=methods['PPCPP']['mean']-methods['LOCAL_P2']['mean'] if methods['LOCAL_P2']['mean'] is not None and methods['PPCPP']['mean'] is not None else None)
  states.append(state)
 strata=[dict(factor=f,value=v,kind=kind,summary=summary([c for c in calls if c['kind']==kind and c[f]==v])) for f in ('family','size','progress') for v in sorted({c[f] for c in calls}) for kind in ('event','control')]
 improved=[s for s in states if s['kind']=='event' and s['saved'] is not None and s['saved']>0 and s['methods']['LOCAL_P2']['timely']==3 and s['methods']['PPCPP']['timely']==3];baseids=sorted({s['base_id'] for s in improved});families=sorted({s['family'] for s in improved});stable=all(s['methods']['LOCAL_P2']['stable_route'] for s in improved)
 summaries={kind:summary([c for c in calls if c['kind']==kind]) for kind in ('event','control')}
 metric_totals=[dict(kind=kind,method=m,view=view,totals=totals([c['metrics'] for c in calls if c['kind']==kind and c['method']==m and c[view]])) for kind in ('event','control') for m in METHODS for view in ('timely','valid')]
 return norm(dict(calls=calls,states=states,summary=summaries,strata=strata,metric_totals=metric_totals,P0_pairs=p0_pairs,continue_signal=dict(passed=len(baseids)>=4 and len(families)>=2 and stable,base_ids=baseids,families=families,stable=stable),internal_calls={key:sum(c['internal_calls'].get(key,0) for c in calls) for key in ('PPCPP','local_P2','global_P2')}))
def csvout(name,rows):
 with (H/name).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def main():
 d=compute();save(H/'analysis.json',d)
 csvout('324调用完整指标.csv',[{**{k:v for k,v in c.items() if k not in ('metrics','window','audit','internal_calls','phases')},'phases':json.dumps(c['phases']),'internal_calls':json.dumps(c['internal_calls']),**{('metric_'+k):v for k,v in (c['metrics'] or {}).items()}} for c in d['calls']])
 csvout('36状态三种子与窗口.csv',[{**{k:s[k] for k in ('id','pair','kind','family','size','progress','base_id','saved')},'methods':json.dumps(s['methods']),'window':json.dumps(s['window']),'selected':json.dumps(s['selected'])} for s in d['states']])
 csvout('双视图配对.csv',[dict(kind=k,**{key:v for key,v in p.items() if key!='pairs'}) for k,s in d['summary'].items() for p in s['pairs']])
 print(json.dumps({k:d[k] for k in ('summary','continue_signal','P0_pairs','internal_calls')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
