from common import *
from statistics import mean,median
from collections import Counter
audit_module=load('last_post_audit',H/'audit.py')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def timing(xs):
 a=sorted(xs);q=(len(a)-1)*.95;i=int(q)
 return dict(N=len(a),mean=mean(a),median=median(a),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(q-i),max=max(a)) if a else dict(N=0)
def reference(case,c,e):
 folder=R/('PPCPP结束位置跨几何验证_v0.1_20261020' if case['batch']=='main36' else 'PPCPP小图最优差距诊断_v0.2_20261020');name=case['name'];src=folder/'inputs'/f'{name}.json'
 assert sha(src)==case['sha256']==sha(R/case['input'])
 a=read(folder/'analysis.json');row=next(x for x in a['states'] if x['id']==name);label='A' if case['batch']=='main36' else 'global';query=folder/'exact'/name/f'{label}.json';req=read(query.with_suffix('.request.json'))
 assert req['input_sha256']==case['sha256'];r=read(query);assert r['status']=='optimal'
 result=dict(Lstar=r['length'],original_gap=row['G'],group=row.get('shape_group'),Lnear=None,Lnear_source='unavailable',reference_files=[str(query.relative_to(R)),str(query.with_suffix('.request.json').relative_to(R)),str((folder/'analysis.json').relative_to(R))])
 if e is None:return result
 if case['batch']=='main36':
  mp=read(folder/'exact'/name/'mapping.json');assert mp['emin']==list(e);label=mp['mapping']['C'];q=folder/'exact'/name/f'{label}.json';nr=read(q);assert nr['last']==list(e)
  result.update(Lnear=nr['length'] if nr['status']=='optimal' else None,Lnear_source='existing_C_or_reused_B',Lnear_status=nr['status']);result['reference_files'] += [str(q.relative_to(R)),str(q.with_suffix('.request.json').relative_to(R))]
 else:
  mp=read(folder/'exact'/name/'mapping.json')
  if mp['last']==list(e):
   q=folder/'exact'/name/'fixed_last.json';result.update(Lnear=read(q)['length'],Lnear_source='existing_same_last_query');result['reference_files'] += [str(q.relative_to(R)),str(q.with_suffix('.request.json').relative_to(R))]
  else:
   pending=points(c['targets'])-points(c['covered']);last=None
   for p in map(tuple,r['route']):
    if p in pending:pending.remove(p);last=p
   if last==e:result.update(Lnear=r['length'],Lnear_source='global_LB_plus_same_last_optimal_witness')
 return result
def summarize(rows):
 pairs=[r for r in rows if r['paired']];improved=[r for r in pairs if r['saved']>0];alts=[r for r in rows if r.get('P1_metrics')];statuses=Counter(r['P1_status'] for r in rows)
 return dict(states=len(rows),paired=len(pairs),short=sum(r['saved']>0 for r in pairs),equal=sum(r['saved']==0 for r in pairs),long=sum(r['saved']<0 for r in pairs),PPCPP=sum(r['PPCPP_metrics']['length'] for r in pairs),LAST=sum(r['LAST_metrics']['length'] for r in pairs),saved=sum(r['saved'] for r in pairs),mean_relative_change=mean([-r['saved']/r['PPCPP_metrics']['length'] for r in pairs if r['PPCPP_metrics']['length']]) if pairs else None,selected_P1=sum(r.get('selected')=='P1' for r in rows),P1_statuses=dict(statuses),P1_short=sum(r['P1_metrics']['length']<r['PPCPP_metrics']['length'] for r in alts),P1_equal=sum(r['P1_metrics']['length']==r['PPCPP_metrics']['length'] for r in alts),P1_long=sum(r['P1_metrics']['length']>r['PPCPP_metrics']['length'] for r in alts),baseline_optimal=sum(r['reference']['original_gap']==0 for r in rows),baseline_gap_states=sum(r['reference']['original_gap']>0 for r in rows),final_optimal=sum(r.get('final_gap')==0 for r in pairs),initial_gap=sum(r['reference']['original_gap'] for r in rows),remaining_gap=sum(r.get('final_gap',0) for r in pairs),improved_groups=len({r['reference']['group'] for r in improved if r['reference']['group']}),extra_work_connection_steps=sum(r['audit']['extra_work_connection_steps'] for r in rows))
def compute():
 protect();assert read(H/'completion.json')['completed'];cases=read(H/'protocol.json')['cases'];results={};audits={};calls=[]
 for j in read(H/'completion.json')['jobs']:
  path=H/'execution'/f"{j['id']}.json";x=read(path);assert not x.get('technical_failure'),path
  c=read(j['input']);assert sha(j['input'])==j['input_sha256'];audit=audit_module.check(c,x);audits[j['id']]=audit
  assert x['runtime_reads']==[str(Path(j['input']).resolve())],x['runtime_reads']
  assert not any(Path(p).name in ('exact.py','independent.py','analyze.py') for p in x['imported_modules'])
  assert x['job']==j;results[j['case_id'],j['method'],j['repetition']]=x
  calls.append(dict(id=j['id'],case_id=j['case_id'],method=j['method'],batch=j['batch'],repetition=j['repetition'],eligible=x['eligible'],status=x['raw']['status'],entry_seconds=x['entry_seconds'],phases=x['phase_seconds']))
 rows=[];refs={}
 eqmod=load('last_shape_equivalence',R/'PPCPP结束位置跨几何验证_v0.1_20261020/equivalence.py')
 for case in cases:
  ident=case['id'];c=read(R/case['input']);base=results[ident,'PPCPP',0];last=results[ident,'LAST',0];b=base['raw'];r=last['raw'];stable=[]
  for rep in (0,1,2):
   p=results[ident,'PPCPP',rep]['raw'];q=results[ident,'LAST',rep]['raw']
   for k in ('route','trace'):assert p['branches']['P0'][k]==q['branches']['P0'][k]
   for method in ('PPCPP','LAST'):
    cur=results[ident,method,rep]['raw'];first=results[ident,method,0]['raw']
    for k in ('route','trace','selected','e'):assert cur[k]==first[k],(ident,method,rep,k)
    if method=='LAST' and 'P1' in cur['branches']:
     for k in ('route','trace','status','phase1_end','diagnostic_route'):assert cur['branches']['P1'][k]==first['branches']['P1'][k]
   stable.append(True)
  e=tuple(r['e']) if r['e'] is not None else None;ref=reference(case,c,e);ref['group']=ref['group'] or 'old_'+eqmod.signature(c)[:12]
  for file in ref['reference_files']:refs[file]=sha(R/file)
  paired=all(results[ident,m,k]['eligible'] for m in ('PPCPP','LAST') for k in (0,1,2))
  p1=r['branches'].get('P1');row=dict(**case,paired=paired,selected=r['selected'],P1_status=p1['status'] if p1 else 'empty_U',e=r['e'],reference=ref,audit=audits[ident+'__r0__LAST'],stable_all_repeats=all(stable),PPCPP_entry_times=[results[ident,'PPCPP',k]['entry_seconds'] for k in (0,1,2)],LAST_entry_times=[results[ident,'LAST',k]['entry_seconds'] for k in (0,1,2)])
  for label,out in [('PPCPP',base),('LAST',last)]:
   if out['eligible']:row[label+'_metrics']=metric(c,out['raw']['route'])
  if p1 and p1['status']=='core_complete':
   row['P1_metrics']=metric(c,p1['route'])
   if ref['Lnear'] is not None:
    row['P1_minus_Lnear']=row['P1_metrics']['length']-ref['Lnear'];assert row['P1_minus_Lnear']>=0,'P1 violated proven bound'
  if paired:
   row.update(saved=row['PPCPP_metrics']['length']-row['LAST_metrics']['length'],final_gap=row['LAST_metrics']['length']-ref['Lstar']);assert row['saved']>=0 and row['final_gap']>=0
  rows.append(row)
 return rows,calls,refs
def main():
 rows,calls,refs=compute();batches={b:summarize([r for r in rows if r['batch']==b]) for b in ('main36','supp24')};times={b:{m:timing([x['entry_seconds'] for x in calls if x['batch']==b and x['method']==m]) for m in ('PPCPP','LAST')} for b in batches};totals={}
 for batch in batches:
  rr=[r for r in rows if r['batch']==batch];totals[batch]={}
  for method in ('PPCPP','LAST','P1'):
   ms=[r[method+'_metrics'] for r in rr if method+'_metrics' in r]
   if not ms:continue
   keys=['length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','initial_credit','target_arrivals','duplicate_target_arrivals']
   totals[batch][method]=dict(N=len(ms),**{k:sum(m[k] for m in ms) for k in keys})
   t=totals[batch][method];t.update(active_coverage=t['active_covered']/t['active_targets'],published_coverage=t['published_covered']/t['published_targets'],overlap=t['duplicate_target_arrivals']/t['target_arrivals'])
 choices={'best_improvement':sorted([r for r in rows if r.get('saved',0)>0],key=lambda r:(-r['saved'],r['id'])),'unrecovered_space':sorted([r for r in rows if r['reference']['original_gap']>0 and r.get('final_gap',0)>0],key=lambda r:r['id']),'P1_longer':sorted([r for r in rows if 'P1_metrics' in r and r['P1_metrics']['length']>r['PPCPP_metrics']['length']],key=lambda r:r['id']),'reservation_infeasible':sorted([r for r in rows if r['P1_status']=='reservation_infeasible'],key=lambda r:r['id'])}
 selected={k:v[0]['id'] if v else None for k,v in choices.items()};phase_times={b:{m:{k:mean([x['phases'].get(k,0) for x in calls if x['batch']==b and x['method']==m]) for k in ('p0','candidate','p1','final_audit','encoding')} for m in ('PPCPP','LAST')} for b in batches}
 save(H/'analysis.json',dict(states=rows,batches=batches,timing=times,phase_timing=phase_times,metric_totals=totals,selected=selected,calls=calls,review_status='执行完成，待负责人审核'))
 save(H/'reference_seal.json',dict(phase='references read only after all 360 formal calls completed',files=refs));save(H/'formal_call_ledger.json',dict(calls=360,methods=dict(Counter(x['method'] for x in calls)),statuses=dict(Counter(x['status'] for x in calls)),eligible=sum(x['eligible'] for x in calls),gate_calls=read(H/'gate_index.json')['calls'],gate_exact_calls=read(H/'gate_index.json')['exact_fixture_calls']))
 print(json.dumps(dict(batches=batches,timing=times,selected=selected),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
