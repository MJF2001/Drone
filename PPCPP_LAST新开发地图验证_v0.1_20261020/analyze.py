from common import *
from audit_adapter import Audit
from statistics import mean,median
from collections import Counter
def fingerprint(r):
 keys=('route','trace','e','selected','status');d={k:r.get(k) for k in keys}
 for name,b in r.get('branches',{}).items():d[name]={k:b.get(k) for k in ('route','trace','status','phase1_end','diagnostic_route')}
 return json.dumps(d,sort_keys=True,separators=(',',':'))
def timing(xs):
 if not xs:return dict(N=0)
 a=sorted(xs);z=(len(a)-1)*.95;i=int(z)
 return dict(N=len(xs),mean=mean(xs),median=median(xs),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i),max=max(xs))
def summarize(rows):
 pairs=[r for r in rows if r.get('paired')];alt=[r for r in rows if 'P1_metrics' in r and 'P0_metrics' in r]
 out=dict(slots=len(rows),valid=sum(r['input_status']=='valid' for r in rows),paired=len(pairs),short=sum(r['saved']>0 for r in pairs),equal=sum(r['saved']==0 for r in pairs),long=sum(r['saved']<0 for r in pairs),PPCPP=sum(r['PPCPP_metrics']['length'] for r in pairs),LAST=sum(r['LAST_metrics']['length'] for r in pairs),saved=sum(r['saved'] for r in pairs),mean_relative_change=mean([-r['saved']/r['PPCPP_metrics']['length'] for r in pairs if r['PPCPP_metrics']['length']]) if pairs else None,shape_groups=len({r['shape_group'] for r in rows if 'shape_group' in r}),improved_groups=len({r['shape_group'] for r in pairs if r['saved']>0}),P1_short=sum(r['P1_metrics']['length']<r['P0_metrics']['length'] for r in alt),P1_equal=sum(r['P1_metrics']['length']==r['P0_metrics']['length'] for r in alt),P1_long=sum(r['P1_metrics']['length']>r['P0_metrics']['length'] for r in alt),selected_P1=sum(r.get('selected')=='P1' for r in rows),P1_state_statuses=dict(Counter(r.get('P1_status','unavailable') for r in rows)),extra_work_steps=sum(r.get('audit',{}).get('extra_work_connection_steps',0) for r in rows))
 return out
def compute():
 protect();assert read(H/'completion.json')['completed'];novel=read(H/'novelty.json');nd={r['id']:r for r in novel['new']};inputs={r['id']:r for r in read(H/'input_audit.json')};rows=[];calls=[];p0_pairs=0
 for slot in read(H/'protocol.json')['slots']:
  ident=slot['id'];row=dict(**slot,input_status=inputs[ident]['status'],paired=False)
  if row['input_status']!='valid':rows.append(row);continue
  row.update(nd[ident]);c=read(H/'inputs'/f'{ident}.json');auditor=Audit(c);results={};details={};infos={}
  for rep in range(5):
   for method in ('PPCPP','LAST'):
    name=f'{ident}__r{rep}__{method}';path=H/'execution'/f'{name}.json';x=read(path);assert not x.get('technical_failure'),path
    j=x['job'];assert j['input_sha256']==sha(j['input']) and j['method']==method and j['repetition']==rep
    assert x['runtime_reads']==[str(Path(j['input']).resolve())] and not any(Path(f).name in ('exact.py','independent.py','analyze.py') for f in x['imported_modules'])
    for file,h in j['production_hashes'].items():assert sha(H/file)==h
    audit=auditor.check(x);details[method,rep]=audit;results[method,rep]=x
    status=x['raw']['status'];legal=False
    if x['raw']['route']:legal=metric(c,x['raw']['route'])['complete_legal'];assert metric(c,x['raw']['route'])==cross(c,x['raw']['route'])
    calls.append(dict(id=name,case_id=ident,method=method,repetition=rep,status=status,eligible=x['eligible'],legal=legal,entry_seconds=x['entry_seconds'],overrun=max(0,x['entry_seconds']-20),phases=x['phase_seconds'],audit=audit))
   a=results['PPCPP',rep]['raw']['branches'].get('P0');b=results['LAST',rep]['raw']['branches'].get('P0')
   if a and b and a['status']==b['status']=='core_complete':
    for key in ('route','trace'):assert a[key]==b[key],(ident,rep,key)
    p0_pairs+=1
  for method in ('PPCPP','LAST'):
   rr=[results[method,k] for k in range(5)];stable=len({fingerprint(x['raw']) for x in rr})==1;good=sum(x['eligible'] for x in rr)
   infos[method]=dict(successes=good,stable=stable,statuses=dict(Counter(x['raw']['status'] for x in rr)),entry_times=[x['entry_seconds'] for x in rr])
   if stable and good==5:row[method+'_metrics']=metric(c,rr[0]['raw']['route'])
  row['methods']=infos;row['paired']=all(infos[m]['successes']==5 and infos[m]['stable'] for m in infos)
  last=[results['LAST',k]['raw'] for k in range(5)];p0=[x['branches'].get('P0') for x in last];p1=[x['branches'].get('P1') for x in last]
  row['candidate_call_statuses']=dict(Counter(x['status'] if x else 'empty_U' for x in p1))
  if all(x and x['status']=='core_complete' for x in p0) and len({json.dumps([x['route'],x['trace']],sort_keys=True) for x in p0})==1:row['P0_metrics']=metric(c,p0[0]['route'])
  if len(row['candidate_call_statuses'])==1:row['P1_status']=next(iter(row['candidate_call_statuses']))
  else:row['P1_status']='mixed'
  if all(x and x['status']=='core_complete' for x in p1) and len({json.dumps([x['route'],x['trace']],sort_keys=True) for x in p1})==1:row['P1_metrics']=metric(c,p1[0]['route'])
  if infos['LAST']['stable']:
   row.update(selected=last[0].get('selected'),e=last[0].get('e'),audit=details['LAST',0])
  if row['paired']:
   row['saved']=row['PPCPP_metrics']['length']-row['LAST_metrics']['length'];row['relative_saved']=row['saved']/row['PPCPP_metrics']['length'] if row['PPCPP_metrics']['length'] else None
   assert row['saved']>=0
  rows.append(row)
 # Preserve protocol execution ordering in the call table.
 order={j['id']:i for i,j in enumerate(read(H/'completion.json')['jobs'])};calls.sort(key=lambda c:order[c['id']])
 return json.loads(json.dumps(rows)),calls,p0_pairs
def metrics_totals(rows):
 out={}
 for method in ('PPCPP','LAST','P1'):
  ms=[r[method+'_metrics'] for r in rows if method+'_metrics' in r]
  if not ms:continue
  keys=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','initial_credit','target_arrivals','duplicate_target_arrivals']
  t=dict(N=len(ms),**{k:sum(m[k] for m in ms) for k in keys});t.update(active_coverage=t['active_covered']/t['active_targets'],published_coverage=t['published_covered']/t['published_targets'],overlap=t['duplicate_target_arrivals']/t['target_arrivals'] if t['target_arrivals'] else None);out[method]=t
 return out
def selected_figures(rows):
 choices={'max_absolute':sorted([r for r in rows if r.get('saved',0)>0],key=lambda r:(-r['saved'],r['id'])),'max_relative':sorted([r for r in rows if r.get('saved',0)>0],key=lambda r:(-r['relative_saved'],r['id'])),'no_improvement':sorted([r for r in rows if r.get('saved')==0],key=lambda r:r['id']),'P1_longer':sorted([r for r in rows if 'P1_metrics' in r and 'P0_metrics' in r and r['P1_metrics']['length']>r['P0_metrics']['length']],key=lambda r:r['id']),'reservation_infeasible':sorted([r for r in rows if r.get('P1_status')=='reservation_infeasible'],key=lambda r:r['id']),'late_or_failed':sorted([r for r in rows if r.get('methods') and any(v['successes']<5 for v in r['methods'].values())],key=lambda r:r['id'])}
 return {k:v[0]['id'] if v else None for k,v in choices.items()}
def main():
 rows,calls,pairs=compute();strata={key:{str(v):summarize([r for r in rows if r[key]==v]) for v in sorted({r[key] for r in rows})} for key in ('family','size','event','progress','shape_group')}
 stratum_copy={'exclude_old_state_copies':summarize([r for r in rows if not r.get('old_copy')]),'exclude_old_state_and_shape_copies':summarize([r for r in rows if not r.get('old_copy') and not r.get('old_shape_copy')])}
 support=[r for r in rows if r.get('saved',0)>0 and not r.get('old_copy') and not r.get('old_shape_copy')];family_support={f:sorted({r['shape_group'] for r in support if r['family']==f}) for f in ('I','L','Z')};cross=any(x['family']!=y['family'] and x['shape_group']!=y['shape_group'] for x in support for y in support)
 times={m:timing([c['entry_seconds'] for c in calls if c['method']==m]) for m in ('PPCPP','LAST')};phases={m:{k:mean([c['phases'].get(k,0) for c in calls if c['method']==m]) for k in ('p0','candidate','p1','final_audit','encoding')} for m in times}
 stats={m:dict(calls=len(xs),eligible=sum(x['eligible'] for x in xs),legal=sum(x['legal'] for x in xs),statuses=dict(Counter(x['status'] for x in xs)),overruns_gt_10ms=sum(x['overrun']>.01 for x in xs),max_overrun=max(x['overrun'] for x in xs),stable_success_states=sum(r.get('methods',{}).get(m,{}).get('successes')==5 and r['methods'][m]['stable'] for r in rows)) for m in times for xs in [[x for x in calls if x['method']==m]]}
 summ=summarize(rows);best=max((r.get('saved',0) for r in rows),default=0)
 save(H/'analysis.json',dict(states=rows,calls=calls,summary=summ,strata=strata,copy_exclusions=stratum_copy,family_support=family_support,cross_shape_preservation=cross,timing=times,phase_timing=phases,call_stats=stats,metric_totals=metrics_totals(rows),selected=selected_figures(rows),largest_single_saving=best,largest_single_share=best/summ['saved'] if summ['saved'] else None,P0_pairs=pairs,review_status='执行完成，待负责人审核'))
 save(H/'formal_call_ledger.json',dict(preparation_calls=len(list((H/'prep/results').glob('*.json'))),new_input_gate_calls=read(H/'gate_index.json')['calls'],formal_calls=len(calls),by_method=stats,exact_calls=0))
 print(json.dumps(dict(summary=summ,copy_exclusions=stratum_copy,family_support=family_support,cross_shape_preservation=cross,timing=times,call_stats=stats,selected=selected_figures(rows)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
