"""Offline complete auditing and paired statistics. Never calls the planner."""
import csv
from statistics import mean,median
from collections import Counter
from common import *
from semantics import compare,p0_semantic,norm,last_capture
from run import stable_fingerprint
adapter=load('speed_analysis_adapter',H/'audit_adapter.py')
METHODS=('PPCPP','LAST_V1','LAST_V2');PHASES=('p0','candidate','p1','final_audit','encoding')
def timing(values):
 a=sorted(values);z=(len(a)-1)*.95;i=int(z)
 return dict(N=len(a),mean=mean(a),median=median(a),p95=a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i),max=max(a))
def faster(a,b):return dict(faster=sum(x<y for x,y in zip(a,b)),equal=sum(x==y for x,y in zip(a,b)),slower=sum(x>y for x,y in zip(a,b)))
def summarize_times(calls):
 out={}
 for m in METHODS:
  xs=[x for x in calls if x['method']==m];t=timing([x['entry_seconds'] for x in xs]);t.update(eligible=sum(x['eligible'] for x in xs),legal=sum(x['legal'] for x in xs),statuses=dict(Counter(x['status'] for x in xs)),max_overrun=max(x['overrun'] for x in xs),overrun_gt_10ms=sum(x['overrun']>.01 for x in xs))
  t['phases']={p:mean(x['phases'].get(p,0) for x in xs) for p in PHASES};t['unsegmented']=t['mean']-sum(t['phases'].values());out[m]=t
 return out
def total_metrics(rows):
 sums=('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','direction_changes','completion_step','return_tail_steps','initial_credit','active_targets','remaining_before','newly_completed','active_covered','missing_active','published_targets','published_covered','deferred','uncompleted_published','target_arrivals','duplicate_target_arrivals')
 out={}
 for m in METHODS+('P1',):
  xs=[r['metrics'][m] for r in rows if m in r['metrics']];d=dict(N=len(xs),**{k:sum(x[k] for x in xs) for k in sums})
  d.update(active_coverage=d['active_covered']/d['active_targets'],remaining_completion_fraction=d['newly_completed']/d['remaining_before'],published_coverage=d['published_covered']/d['published_targets'],overlap_ratio=d['duplicate_target_arrivals']/d['target_arrivals']);out[m]=d
 return out
def compute():
 protect();completion=read(H/'completion.json');assert completion['completed'] and completion['calls']==810
 protocol=read(H/'protocol.json');rows=[];calls=[];pairs=0;p0_pairs=0;stable=0
 order={x['id']:x['sequence'] for x in completion['actual_order']}
 for slot in protocol['slots']:
  ident=slot['id'];item=next(i for i in protocol['inputs'][:54] if i['id']==ident);c=read(H/item['input']);auditor=adapter.Audit(c);results={};row=dict(**slot,methods={},metrics={})
  for rep in range(5):
   for m in METHODS:
    name=f'{ident}__r{rep}__{m}';x=read(H/'execution'/(name+'.json'));assert not x.get('technical_failure');j=x['job'];results[m,rep]=x
    assert j['method']==m and j['repetition']==rep and j['seed']==20261020+rep and j['input_sha256']==sha(Path(j['input']))==item['sha256']
    assert j['source_seal_sha256']==sha(H/'source_seal.json') and j['production_hashes']==x['production_sources']==read(H/'source_seal.json')['actual_sources'][m]
    for p,h in x['production_sources'].items():assert sha(Path(p))==h
    assert x['runtime_reads']==[str((H/item['input']).resolve())]
    assert not any(Path(p).name in ('exact.py','independent.py','analyze.py','audit_adapter.py','semantics.py','run.py','common.py') for p in x['imported_modules'])
    assert not any(Path(p).resolve()==H/'audit.py' for p in x['imported_modules'])
    # Frozen baseline_suite eagerly imports its own audit and method modules;
    # these are inherited imports, not this experiment's offline auditor.
    for p in x['imported_modules']:
     pp=Path(p)
     if pp.is_relative_to(R) and not pp.is_relative_to(R/'运行环境') and pp.suffix=='.py':
      expected=j['production_hashes'].get(str(pp)) or protocol['files'].get(str(pp.relative_to(R)))
      if expected:assert sha(pp)==expected,('workspace dependency changed',p)
      else:
       # Eager optional package imports were logged by every worker. Their
       # supplemental file inventory is explicitly post-run, not a pre-run seal.
       assert '.deps' in pp.parts,('unsealed project source',p)
       assert read(H/'imported_dependency_inventory.json')['files'][str(pp)]==sha(pp)
    details=auditor.check(x);metrics={}
    for label,b in x['raw']['branches'].items():
     if b['status']=='core_complete':metrics[label]=metric(c,b['route']);assert metrics[label]==cross(c,b['route'])
    if x['eligible']:metrics['final']=metric(c,x['raw']['route']);assert metrics['final']==cross(c,x['raw']['route'])
    capture={label:last_capture(c,b['route']) for label,b in x['raw']['branches'].items() if b['status']=='core_complete'}
    calls.append(dict(id=name,sequence=order[name],case_id=ident,method=m,repetition=rep,status=x['raw']['status'],eligible=x['eligible'],legal=metrics.get('final',{}).get('complete_legal',False),entry_seconds=x['entry_seconds'],overrun=max(0,x['entry_seconds']-20),phases=x['phase_seconds'],metrics=metrics,last_capture=capture,audit=details))
   a=results['LAST_V1',rep];b=results['LAST_V2',rep];paired=compare(a,b)=='equal_complete';pairs+=paired
   if paired:
    for label in ('P0','P1'):
     aa=a['raw']['branches'].get(label);bb=b['raw']['branches'].get(label)
     if aa and bb and aa['status']==bb['status']=='core_complete':assert metric(c,aa['route'])==metric(c,bb['route']) and norm(last_capture(c,aa['route']))==norm(last_capture(c,bb['route']))
    assert metric(c,a['raw']['route'])==metric(c,b['raw']['route'])
   for m in ('LAST_V1','LAST_V2'):
    aa=results['PPCPP',rep]['raw']['branches']['P0'];bb=results[m,rep]['raw']['branches']['P0']
    if aa['status']==bb['status']=='core_complete':assert p0_semantic(aa)==p0_semantic(bb);p0_pairs+=1
  for m in METHODS:
   xs=[results[m,r] for r in range(5)];isstable=len({stable_fingerprint(x['raw']) for x in xs})==1;stable+=isstable
   row['methods'][m]=dict(successes=sum(x['eligible'] for x in xs),stable=isstable,times=[x['entry_seconds'] for x in xs],mean=mean(x['entry_seconds'] for x in xs))
   if isstable and all(x['eligible'] for x in xs):row['metrics'][m]=metric(c,xs[0]['raw']['route'])
  alt=results['LAST_V2',0]['raw'];p1=alt['branches'].get('P1');row.update(e=alt['e'],selected=alt['selected'],P1_status=p1['status'] if p1 else 'empty_U',phase1_end=p1.get('phase1_end') if p1 else None)
  if p1 and p1['status']=='core_complete':row['metrics']['P1']=metric(c,p1['route'])
  row['saved']=row['metrics']['PPCPP']['length']-row['metrics']['LAST_V2']['length'];row['relative_saved']=row['saved']/row['metrics']['PPCPP']['length']
  row['time_pairs']={ref:dict(ratio=row['methods']['LAST_V2']['mean']/row['methods'][ref]['mean'],delta_ms=(row['methods']['LAST_V2']['mean']-row['methods'][ref]['mean'])*1000,**faster(row['methods']['LAST_V2']['times'],row['methods'][ref]['times'])) for ref in ('LAST_V1','PPCPP')}
  rows.append(row)
 calls.sort(key=lambda x:x['sequence']);times=summarize_times(calls)
 strata=[]
 for factor in ('size','family','event','progress'):
  for value in sorted({r[factor] for r in rows}):
   rr=[r for r in rows if r[factor]==value];ids={r['id'] for r in rr};cc=[x for x in calls if x['case_id'] in ids]
   strata.append(dict(factor=factor,value=value,states=len(rr),timing=summarize_times(cc),state_pairs={ref:faster([r['methods']['LAST_V2']['mean'] for r in rr],[r['methods'][ref]['mean'] for r in rr]) for ref in ('LAST_V1','PPCPP')},call_pairs={ref:faster([v for r in rr for v in r['methods']['LAST_V2']['times']],[v for r in rr for v in r['methods'][ref]['times']]) for ref in ('LAST_V1','PPCPP')}))
 paircounts={ref:dict(state_means=faster([r['methods']['LAST_V2']['mean'] for r in rows],[r['methods'][ref]['mean'] for r in rows]),calls=faster([v for r in rows for v in r['methods']['LAST_V2']['times']],[v for r in rows for v in r['methods'][ref]['times']]),ratio_means=times['LAST_V2']['mean']/times[ref]['mean'],delta_ms=(times['LAST_V2']['mean']-times[ref]['mean'])*1000) for ref in ('LAST_V1','PPCPP')}
 summ=dict(states=len(rows),short=sum(r['saved']>0 for r in rows),equal=sum(r['saved']==0 for r in rows),long=sum(r['saved']<0 for r in rows),original=sum(r['metrics']['PPCPP']['length'] for r in rows),v2=sum(r['metrics']['LAST_V2']['length'] for r in rows),P1_statuses=dict(Counter(r['P1_status'] for r in rows)),P1_short=sum(r['metrics']['P1']['length']<r['metrics']['PPCPP']['length'] for r in rows),P1_equal=sum(r['metrics']['P1']['length']==r['metrics']['PPCPP']['length'] for r in rows),P1_long=sum(r['metrics']['P1']['length']>r['metrics']['PPCPP']['length'] for r in rows),V1_V2_complete_pairs=pairs,P0_pairs=p0_pairs,stable_groups=stable,mean_relative_saved=mean(r['relative_saved'] for r in rows))
 assert (summ['original'],summ['v2'],summ['short'],summ['equal'],summ['long'])==(5530,5476,27,27,0)
 assert pairs==270 and p0_pairs==540 and stable==162
 return norm(dict(summary=summ,states=rows,calls=calls,timing=times,time_pairs=paircounts,strata=strata,metric_totals=total_metrics(rows)))
def csvfile(name,rows):
 with (H/name).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 d=compute();save(H/'analysis.json',d)
 csvfile('810调用时间与分段.csv',[dict(sequence=x['sequence'],id=x['id'],case_id=x['case_id'],method=x['method'],repetition=x['repetition'],status=x['status'],eligible=x['eligible'],entry_ms=x['entry_seconds']*1000,**{p+'_ms':x['phases'].get(p,0)*1000 for p in PHASES},unsegmented_ms=(x['entry_seconds']-sum(x['phases'].get(p,0) for p in PHASES))*1000) for x in d['calls']])
 csvfile('54状态配对.csv',[dict(id=r['id'],size=r['size'],family=r['family'],event=r['event'],progress=r['progress'],original=r['metrics']['PPCPP']['length'],v2=r['metrics']['LAST_V2']['length'],P1=r['metrics']['P1']['length'],saved=r['saved'],selected=r['selected'],e=json.dumps(r['e']),**{m+'_mean_ms':r['methods'][m]['mean']*1000 for m in METHODS},**{m+'_r0_r4_ms':json.dumps([v*1000 for v in r['methods'][m]['times']]) for m in METHODS},v2_v1_ratio=r['time_pairs']['LAST_V1']['ratio'],v2_v1_delta_ms=r['time_pairs']['LAST_V1']['delta_ms'],v2_v1_faster=r['time_pairs']['LAST_V1']['faster'],v2_v1_slower=r['time_pairs']['LAST_V1']['slower'],v2_ppcpp_ratio=r['time_pairs']['PPCPP']['ratio'],v2_ppcpp_delta_ms=r['time_pairs']['PPCPP']['delta_ms']) for r in d['states']])
 csvfile('分层时间配对.csv',[dict(factor=r['factor'],value=r['value'],states=r['states'],**{m+'_mean_ms':r['timing'][m]['mean']*1000 for m in METHODS},v2_v1_ratio=r['timing']['LAST_V2']['mean']/r['timing']['LAST_V1']['mean'],v2_ppcpp_ratio=r['timing']['LAST_V2']['mean']/r['timing']['PPCPP']['mean'],state_v1_faster=r['state_pairs']['LAST_V1']['faster'],state_v1_slower=r['state_pairs']['LAST_V1']['slower'],call_v1_faster=r['call_pairs']['LAST_V1']['faster'],call_v1_slower=r['call_pairs']['LAST_V1']['slower'],call_ppcpp_faster=r['call_pairs']['PPCPP']['faster'],call_ppcpp_slower=r['call_pairs']['PPCPP']['slower']) for r in d['strata']])
 csvfile('54几何BFS诊断.csv',[{k:v for k,v in r.items() if k!='distances'} for r in read(H/'distance_diagnostics.json')])
 csvfile('完整路线指标.csv',[dict(id=r['id'],method=m,**ms) for r in d['states'] for m,ms in r['metrics'].items()])
 print(json.dumps({k:d[k] for k in ('summary','timing','time_pairs')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
