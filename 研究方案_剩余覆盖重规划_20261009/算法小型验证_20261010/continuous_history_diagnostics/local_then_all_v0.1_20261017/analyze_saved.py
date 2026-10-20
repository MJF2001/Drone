from pathlib import Path
import json,csv,statistics
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def out(name,rows):
 if not rows:return
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 rows=[];curves=[]
 for j in read(D/'protocol.json')['jobs']:
  x=read(D/'formal'/(j['run_id']+'.json'));r=x['raw'];combo=j['method']=='LOCAL_THEN_ALL';d=r if combo else r['detail'];events=d['candidate_events'];c=read(j['case']);st=r.get('stages',[]);first=st[0] if combo else {};second=st[1] if combo else {};k=first.get('best_candidate_id');h=second.get('best_candidate_id');before=events[k]['steps'] if k is not None else None;after=events[h]['steps'] if h is not None else None
  rows.append(dict(run_id=j['run_id'],map_id=j['map_id'],event=c['metadata']['event'],repeat=j['repeat'],seed=j['seed'],budget=j['budget'],method=j['method'],valid=bool(r['route']),steps=len(r['route'])-1 if r['route'] else None,seconds=r['seconds'],source=r['source'],first_steps=before,second_steps=after,first_seconds=first.get('seconds'),first_overrun=r.get('first_stage_overrun'),switch=r.get('switch_public_elapsed'),all_available=second.get('available_seconds'),all_seconds=second.get('seconds'),all_status=second.get('status'),all_outcome=('skipped' if second.get('status')=='skipped' else 'no_valid_output' if after is None else 'improved' if before is None or after<before else 'output_without_improvement') if combo else None,within_improvement=before-(len(r['route'])-1) if before is not None else None,candidate_events=len(events)))
  for e in events:
   if e['accepted']:curves.append(dict(run_id=j['run_id'],method=j['method'],map_id=j['map_id'],repeat=j['repeat'],budget=j['budget'],public_elapsed=e['accepted_public_elapsed'],steps=e['steps'],source=e.get('source',e['label']),route_sha256=e['route_sha256']))
 out('all_results.csv',rows);out('public_acceptance_curves.csv',curves);idx={(r['map_id'],r['repeat'],r['budget'],r['method']):r for r in rows};maps=sorted({r['map_id'] for r in rows});pairs=[];summary=[];mapmeans=[]
 for baseline in ('FIX_PLUS1','FIX_ALL'):
  for b in (1,20):
   ds=[]
   for m in maps:
    aa=[];bb=[]
    for rep in (0,1):
     a=idx[m,rep,b,'LOCAL_THEN_ALL'];z=idx[m,rep,b,baseline]
     if a['valid'] and z['valid']:
      delta=a['steps']-z['steps'];ds.append((m,delta));aa.append(a['steps']);bb.append(z['steps']);pairs.append(dict(baseline=baseline,map_id=m,repeat=rep,budget=b,delta=delta))
    if aa:mapmeans.append(dict(baseline=baseline,map_id=m,budget=b,paired_seeds=len(aa),combo_mean=statistics.mean(aa),fixed_mean=statistics.mean(bb),relative_pct=100*(statistics.mean(aa)/statistics.mean(bb)-1)))
   subset=[r for r in mapmeans if r['baseline']==baseline and r['budget']==b];deltas=[d for _,d in ds];summary.append(dict(baseline=baseline,budget=b,maps=len(subset),pairs=len(deltas),mean_map_relative_pct=statistics.mean(r['relative_pct'] for r in subset),shorter=sum(d<0 for d in deltas),equal=sum(d==0 for d in deltas),longer=sum(d>0 for d in deltas),sum_delta=sum(deltas),median_delta=statistics.median(deltas),worst_degradation=max(deltas),map_deltas={m:sum(d for name,d in ds if name==m) for m in maps}))
 out('paired_seed_results.csv',pairs);out('paired_map_means.csv',mapmeans)
 methods=[]
 for method in ('FIX_PLUS1','FIX_ALL','LOCAL_THEN_ALL'):
  for b in (1,20):
   rr=[r for r in rows if r['method']==method and r['budget']==b];combo=method=='LOCAL_THEN_ALL';methods.append(dict(method=method,budget=b,runs=len(rr),failed=sum(not r['valid'] for r in rr),mean_seconds=statistics.mean(r['seconds'] for r in rr),overrun_gt10ms=sum(r['seconds']>b+.01 for r in rr),max_overrun=max(0,max(r['seconds']-b for r in rr)),first_overrun_gt10ms=sum(r['first_overrun']>.01 for r in rr) if combo else None,max_first_overrun=max(r['first_overrun'] for r in rr) if combo else None,second_overrun_gt10ms=sum(r['all_seconds']>r['all_available']+.01 for r in rr) if combo else None,mean_first_seconds=statistics.mean(r['first_seconds'] for r in rr) if combo else None,mean_all_available=statistics.mean(r['all_available'] for r in rr) if combo else None,all_outcomes={v:sum(r['all_outcome']==v for r in rr) for v in sorted({r['all_outcome'] for r in rr})} if combo else None,final_from_all=sum(str(r['source']).startswith('all:') for r in rr) if combo else None,within_improvement=sum(r['within_improvement'] or 0 for r in rr) if combo else None))
 result=dict(total=len(rows),failures=sum(not r['valid'] for r in rows),comparisons=summary,methods=methods,synthetic_calls=len((D/'synthetic_calls.jsonl').read_text().splitlines()),preflight_calls=6,formal_calls=120,initial_preparation=0,holdout_used=False)
 (D/'analysis_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
