from pathlib import Path
import json,sys,statistics,csv
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def csvout(name,rows):
 if not rows:return
 with (D/name).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 jobs=read(D/'protocol.json')['jobs'];rows=[];curves=[]
 for j in jobs:
  x=read(D/'formal'/(j['run_id']+'.json'));r=x['raw'];pool=j['method'].startswith('POOL_');d=r if pool else r['detail'];events=d['candidate_events']
  k=r.get('construction_best_candidate_id');cb=len(events[k]['route'])-1 if k is not None else None
  cont=r.get('continuation') or {};st=cont.get('detail',{}).get('stages',{})
  c=read(j['case']);rows.append(dict(run_id=j['run_id'],map_id=j['map_id'],event_type=c['metadata'].get('event_type',c['metadata'].get('event','unknown')),repeat=j['repeat'],seed=j['seed'],budget=j['budget'],method=j['method'],valid=x['independent_route_check']['valid'],steps=len(r['route'])-1 if r['route'] else None,seconds=r['seconds'],source=r['source'],construction_best_steps=cb,construction_seconds=r.get('construction_seconds'),continuation_available=r.get('continuation_available_seconds'),continuation_seconds=r.get('continuation_seconds'),repeated_preprocessing_seconds=st.get('outside_end'),within_run_improvement=cb-(len(r['route'])-1) if cb is not None and r['route'] else None,candidate_count=len(events),late_rejections=sum(e.get('late_rejected',not e['before_deadline']) for e in events),incomplete_stages=sum(v.get('status')=='deadline' for v in r.get('stages',[]) if isinstance(v,dict))))
  for e in events:
   if e['accepted']:curves.append(dict(run_id=j['run_id'],map_id=j['map_id'],method=j['method'],budget=j['budget'],seed=j['seed'],public_elapsed=e['accepted_public_elapsed'],steps=e['steps'],source=e.get('source',e['label']),route_sha256=e['route_sha256']))
 csvout('all_results.csv',rows);csvout('public_acceptance_curves.csv',curves)
 index={(r['map_id'],r['repeat'],r['budget'],r['method']):r for r in rows};maps=sorted({r['map_id'] for r in rows})
 pairs=[('POOL_PLUS1','FIX_PLUS1'),('POOL_INIT','FIX_PLUS1'),('POOL_PLUS1','POOL_INIT'),('POOL_INIT','FIX_SEED'),('POOL_PLUS1','FIX_SEED'),('POOL_INIT','FIX_ALL'),('POOL_PLUS1','FIX_ALL')];paired=[];summaries=[];maprows=[]
 for a,b in pairs:
  for budget in (1,20):
   observations=[]
   for m in maps:
    ap=[];bp=[]
    for rep in (0,1):
     x=index[m,rep,budget,a];y=index[m,rep,budget,b]
     if x['valid'] and y['valid']:
      delta=x['steps']-y['steps'];observations.append((m,delta));ap.append(x['steps']);bp.append(y['steps']);paired.append(dict(a=a,b=b,map_id=m,budget=budget,repeat=rep,delta=delta))
    if ap:
     av=statistics.mean(ap);bv=statistics.mean(bp);maprows.append(dict(a=a,b=b,budget=budget,map_id=m,paired_seeds=len(ap),a_mean=av,b_mean=bv,relative_pct=100*(av/bv-1)))
   for exclude in (False,True):
    ds=[v for m,v in observations if not exclude or not m.startswith('large_g4')];ms=[r['relative_pct'] for r in maprows if r['a']==a and r['b']==b and r['budget']==budget and (not exclude or not r['map_id'].startswith('large_g4'))]
    summaries.append(dict(a=a,b=b,budget=budget,exclude_large_g4=exclude,maps=len(ms),quality_pairs=len(ds),mean_map_relative_pct=statistics.mean(ms) if ms else None,shorter=sum(v<0 for v in ds),equal=sum(v==0 for v in ds),longer=sum(v>0 for v in ds),sum_delta=sum(ds),median_delta=statistics.median(ds) if ds else None,worst_degradation=max(ds) if ds else None))
 csvout('paired_seed_results.csv',paired);csvout('paired_map_means.csv',maprows);csvout('paired_summary.csv',summaries)
 methods=[]
 for m in sorted({r['method'] for r in rows}):
  for budget in (1,20):
   rr=[r for r in rows if r['method']==m and r['budget']==budget];sources={v:sum(r['source']==v for r in rr) for v in sorted({str(r['source']) for r in rr})}
   methods.append(dict(method=m,budget=budget,runs=len(rr),failed=sum(not r['valid'] for r in rr),mean_seconds=statistics.mean(r['seconds'] for r in rr),overrun_gt10ms=sum(r['seconds']>budget+.01 for r in rr),max_overrun=max(0,max(r['seconds']-budget for r in rr)),sources=sources,mean_construction_seconds=statistics.mean(r['construction_seconds'] for r in rr) if m.startswith('POOL') else None,mean_construction_budget_fraction=statistics.mean(r['construction_seconds']/budget for r in rr) if m.startswith('POOL') else None,mean_continuation_available=statistics.mean(r['continuation_available'] for r in rr) if m.startswith('POOL') else None,mean_repeated_preprocessing_seconds=statistics.mean(r['repeated_preprocessing_seconds'] for r in rr if r['repeated_preprocessing_seconds'] is not None) if any(r['repeated_preprocessing_seconds'] is not None for r in rr) else None,within_run_improved=sum((r['within_run_improvement'] or 0)>0 for r in rr),within_run_total_improvement=sum(r['within_run_improvement'] or 0 for r in rr),late_rejections=sum(r['late_rejections'] for r in rr),incomplete_stages=sum(r['incomplete_stages'] for r in rr)))
 summary=dict(total=len(rows),failures=sum(not r['valid'] for r in rows),overrun_gt10ms=sum(r['seconds']>r['budget']+.01 for r in rows),max_overrun=max(0,max(r['seconds']-r['budget'] for r in rows)),methods=methods,comparisons=summaries,synthetic_top_level_calls=len((D/'synthetic_calls.jsonl').read_text().splitlines()),preflight_calls=10,formal_calls=len(rows),new_initial_preparation_calls=0,holdout_used=False)
 (D/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
