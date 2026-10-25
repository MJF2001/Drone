"""Full seed ranges and explicitly timely-only views, no solving."""
import statistics
from collections import defaultdict
from bridge_analysis import H,read,save,csv_write,summarize
def compute():
    a=read(H/'analysis.json');groups=defaultdict(list)
    for r in a['rows']:groups[(r['case'],r['method'])].append(r)
    ranges=[]
    for (case,method),rs in sorted(groups.items()):
        valid=[r for r in rs if r['metrics'] is not None]
        if not valid:continue
        for k in valid[0]['metrics']:
            values=[r['metrics'][k] for r in sorted(valid,key=lambda r:r['rep'])];vv=[v for v in values if v is not None]
            ranges.append(dict(case=case,method=method,metric=k,n=len(vv),mean=statistics.mean(vv) if vv else None,min=min(vv) if vv else None,max=max(vv) if vv else None,raw_rep012=values))
    timely={m:summarize([r for r in a['rows'] if r['method']==m and r['timely']]) for m in ('PPCPP','P2_MULTI') if any(r['method']==m and r['timely'] for r in a['rows'])}
    eligible_cases={s['case'] for s in a['states'] if len(s['pairs'])==3 and all(p['timely_both'] for p in s['pairs'])}
    matched=[p for p in a['matched'] if p['case'] in eligible_cases and p['dispersed_case'] in eligible_cases]
    positive=[p for p in matched if p['signal']];bases=sorted({p['base_id'] for p in positive});families=sorted({p['family'] for p in positive})
    timely_view=dict(summary=timely,excluded_ids=[r['id'] for r in a['rows'] if not r['timely']],eligible_three_seed_cases=sorted(eligible_cases),matched=matched,signal=dict(bases=bases,families=families,passed=len(bases)>=3 and len(families)>=2))
    relation={}
    for m in ('PPCPP','P2_MULTI'):
        rr=[r for r in a['rows'] if r['method']==m and r['metrics'] is not None];allcuts=[read(H/'route_cuts'/f'{r["id"]}.json') for r in rr]
        relation[m]=dict(valid_routes=len(rr),routes_any_group_min_excess=sum(r['excess_group_sum_min']>0 for r in rr),routes_any_raw_bridge_excess=sum(any(e['excess']>0 for e in c['edges']) for c in allcuts),routes_unfinished_exit_reentry=sum(any(e['unfinished_exit_reentry']>0 for e in c['edges']) for c in allcuts),max_group_sum_min=max(r['excess_group_sum_min'] for r in rr),max_group_sum_max=max(r['excess_group_sum_max'] for r in rr),by_layout={layout:dict(n=sum(r['layout']==layout for r in rr),positive_group_min=sum(r['layout']==layout and r['excess_group_sum_min']>0 for r in rr)) for layout in ('dispersed','single','multi')})
    return dict(seed_ranges=ranges,timely_view=timely_view,bridge_relation=relation)
if __name__=='__main__':
    x=compute();save(H/'supplement.json',x);csv_write(H/'三种子完整指标均值范围.csv',x['seed_ranges']);print('Supplement saved: every metric seed range, timely-only view and both methods bridge incidence.')
