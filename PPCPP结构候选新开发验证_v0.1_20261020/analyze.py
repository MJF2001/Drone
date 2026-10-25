"""Full saved-result accounting; never invokes a planner."""
import statistics,json
from pathlib import Path
H=Path(__file__).resolve().parent
METHODS=('PPCPP','FIRST','STRUCT')
TOTAL_KEYS=('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','direction_changes','return_tail_steps','completion_step','target_arrivals','duplicate_target_arrivals','initial_credit','active_targets','active_covered','remaining_before','newly_completed','missing_active','published_targets','published_covered','deferred','uncompleted_published')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def percentile(ts):
    ts=sorted(ts);pos=(len(ts)-1)*.95;i=int(pos);return ts[i]+(ts[min(i+1,len(ts)-1)]-ts[i])*(pos-i)
def main():
    p=read(H/'protocol.json');rows=read(H/'execution/checks.json');assert len(rows)==540
    states=[]
    for c in p['cases']:
        s=dict(**c,methods={})
        for m in METHODS:
            xs=[x for x in rows if x['job']['batch']==c['batch'] and x['job']['case_id']==c['case_id'] and x['job']['method']==m];assert len(xs)==5
            available=[x['metrics'] for x in xs if x['metrics'] is not None]
            assert not available or all(v==available[0] for v in available),'seed-dependent route metrics need explicit review'
            rr=[read(H/'execution/results'/(x['job']['run_id']+'.json'))['raw'] for x in xs]
            details=dict(metrics=available[0] if available else None,eligible=all(x['eligible'] for x in xs))
            if m!='PPCPP':
                r=next((r for r in rr if r['status']=='core_complete'),rr[0]);details.update(triggered=r['branch_state'] is not None,candidates=len(r['branches']),selected=r['selected_branch'])
                if m=='STRUCT':details.update(windows=r['structural_windows'],trigger_recovery=r['override_recovery'])
                if r['status']=='core_complete':
                    b=r['branches'][r['selected_branch']];k=1 if m=='FIRST' else r['override_recovery']
                    if r['branch_state']:
                        e=[e for e in b['trace'] if e['kind']=='recovery'][k-1];idx=b['trace'].index(e);end=b['trace'][idx+1]['index'];ret=b['trace'][-1]['index']
                        details['cost']=dict(prefix=e['index'],approach=end-e['index'],continuation=ret-end,return_steps=len(b['route'])-1-ret)
                    else:details['cost']=dict(coverage=b['trace'][-1]['index'],return_steps=len(b['route'])-1-b['trace'][-1]['index'])
                    details['candidate_goals']=[z['forced_goal'] for z in r['branches']]
                    details['candidate_steps']=[len(z['route'])-1 if z['route'] else None for z in r['branches']]
            s['methods'][m]=details
        states.append(s)
    summary={}
    for batch in ('newdev36',):
        ss=[s for s in states if s['batch']==batch];s=dict(n=len(ss),methods={},pairs={})
        for m in METHODS:
            xs=[x for x in rows if x['job']['batch']==batch and x['job']['method']==m];ts=[x['entry_seconds'] for x in xs]
            valid=[x['methods'][m]['metrics'] for x in ss if x['methods'][m]['eligible']]
            total={k:sum(x[k] for x in valid) for k in TOTAL_KEYS}
            total.update(overlap_pooled=total['duplicate_target_arrivals']/total['target_arrivals'] if total['target_arrivals'] else None,active_coverage_pooled=total['active_covered']/total['active_targets'] if total['active_targets'] else 1,published_coverage_pooled=total['published_covered']/total['published_targets'] if total['published_targets'] else 1,remaining_completion_pooled=total['newly_completed']/total['remaining_before'] if total['remaining_before'] else 1)
            s['methods'][m]=dict(calls=len(xs),eligible=sum(x['eligible'] for x in xs),complete_timed_states=len(valid),totals=total,time_mean=statistics.mean(ts),time_median=statistics.median(ts),time_p95=percentile(ts),time_max=max(ts),triggered=sum(x['methods'][m].get('triggered',False) for x in ss),selected_alternative=sum(x['methods'][m].get('selected',0) not in (None,0) for x in ss),structural_checks=sum(len(x['methods'][m].get('windows',[])) for x in ss),trigger_at_first=sum(x['methods'][m].get('trigger_recovery')==1 for x in ss),trigger_at_second=sum(x['methods'][m].get('trigger_recovery')==2 for x in ss))
        for a,b in (('FIRST','PPCPP'),('STRUCT','PPCPP'),('STRUCT','FIRST')):
            pairs=[(x['methods'][a]['metrics']['length'],x['methods'][b]['metrics']['length']) for x in ss if x['methods'][a]['eligible'] and x['methods'][b]['eligible']]
            diffs=[x-y for x,y in pairs]
            s['pairs'][a+'_vs_'+b]=dict(common_states=len(pairs),shorter=sum(d<0 for d in diffs),equal=sum(d==0 for d in diffs),longer=sum(d>0 for d in diffs),total_a=sum(x for x,y in pairs),total_b=sum(y for x,y in pairs),difference=sum(diffs),mean_relative=statistics.mean((x-y)/y for x,y in pairs) if pairs and all(y for x,y in pairs) else None)
        summary[batch]=s
    result=dict(summary=summary,states=states,formal_calls=len(rows),new_solver_calls=len(rows),holdout=False)
    (H/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
