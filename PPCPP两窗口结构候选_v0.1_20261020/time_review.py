"""Post-run timing robustness description, no solver calls or run exclusions."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    rows=read(H/'execution/checks.json');analysis=read(H/'analysis.json');summary={}
    for batch in ('original20','controlled27'):
        own=[r for r in rows if r['job']['batch']==batch];pairs=[]
        cases=[c for c in analysis['states'] if c['batch']==batch]
        for c in cases:
            for seed in (20261018,20261019):
                pair={m:next(r for r in own if r['job']['case_id']==c['case_id'] and r['job']['seed']==seed and r['job']['method']==m)['entry_seconds'] for m in ('FIRST','STRUCT')}
                pairs.append(dict(case_id=c['case_id'],seed=seed,**pair))
        faster=sum(x['STRUCT']<x['FIRST'] for x in pairs);slower=sum(x['STRUCT']>x['FIRST'] for x in pairs)
        state_pairs=[{m:statistics.mean(x[m] for x in pairs if x['case_id']==c['case_id']) for m in ('FIRST','STRUCT')} for c in cases]
        seed_means={str(seed):{m:statistics.mean(x[m] for x in pairs if x['seed']==seed) for m in ('FIRST','STRUCT')} for seed in (20261018,20261019)}
        branch_counts={m:sum(c['methods'][m]['candidates'] for c in cases) for m in ('FIRST','STRUCT')}
        s=analysis['summary'][batch]['methods'];ratio=s['STRUCT']['time_mean']/s['FIRST']['time_mean']-1
        summary[batch]=dict(paired_calls=len(pairs),struct_faster=faster,tie=len(pairs)-faster-slower,struct_slower=slower,state_mean_faster=sum(x['STRUCT']<x['FIRST'] for x in state_pairs),state_mean_slower=sum(x['STRUCT']>x['FIRST'] for x in state_pairs),seed_means=seed_means,complete_branches_per_state_once=branch_counts,mean_time_relative_change=ratio,median_time_relative_change=s['STRUCT']['time_median']/s['FIRST']['time_median']-1,all_calls_retained=True)
    (H/'time_review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
