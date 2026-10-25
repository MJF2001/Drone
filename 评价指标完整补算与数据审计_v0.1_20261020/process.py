import json,hashlib,statistics,itertools,ast
from pathlib import Path
from metrics import metrics,percentile
from crosscheck import calculate
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):(H/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
TOTAL=('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','target_arrivals','duplicate_target_arrivals','turns90','turns180','direction_changes','initial_credit','return_tail_steps','active_targets','active_covered','published_targets','published_covered','deferred','missing_active','uncompleted_published')
def summarize(rs):
    out=dict(calls=len(rs),valid=sum(x['m']['complete_legal'] for x in rs),timely=sum(x['timely'] for x in rs),late=sum(not x['timely'] for x in rs))
    for label,xs in [('all_valid',rs),('timely_only',[x for x in rs if x['timely']])]:
        totals={k:sum(x['m'][k] for x in xs) for k in TOTAL}
        ratios=[x['m']['overlap_ratio'] for x in xs if x['m']['overlap_ratio'] is not None]
        totals.update(n=len(xs),overlap_pooled=totals['duplicate_target_arrivals']/totals['target_arrivals'] if totals['target_arrivals'] else None,
            overlap_route_mean=statistics.mean(ratios) if ratios else None,overlap_null_count=len(xs)-len(ratios),
            active_coverage_pooled=totals['active_covered']/totals['active_targets'] if totals['active_targets'] else 1.,
            published_coverage_pooled=totals['published_covered']/totals['published_targets'] if totals['published_targets'] else 1.)
        out[label]=totals
    ts=[x['entry_seconds'] for x in rs];excess=[max(0,x['entry_seconds']-20) for x in rs]
    out['time']=dict(n=len(ts),mean=statistics.mean(ts),median=statistics.median(ts),p95=percentile(ts,.95),maximum=max(ts),strict_over_budget=sum(t>=20 for t in ts),over_10ms=sum(e>.01 for e in excess),max_excess=max(excess),primary_untimely=sum(not x['timely'] for x in rs))
    return out
def tests():
    free={(0,0),(1,0),(0,1),(1,1)};walks=[[(0,0)]];layer=list(walks)
    for _ in range(6):
        layer=[w+[q] for w in layer for q in sorted(free) if abs(w[-1][0]-q[0])+abs(w[-1][1]-q[1])==1];walks+=layer
    count=0
    for labels in itertools.product(range(3),repeat=4):
        t={q for q,s in zip(sorted(free),labels) if s};h={q for q,s in zip(sorted(free),labels) if s==2}
        for route in walks:
            c=dict(free=list(free),targets=list(t),covered=list(h),published_targets=list(t),deferred_targets=[],current=(0,0),base=route[-1],distance_budget=100)
            assert metrics(c,route)==calculate(c,route);count+=1
    # Explicit blocked history vs deferred and no-target/zero-overlap denominator.
    c=dict(free=[(0,0)],targets=[],covered=[(8,8)],published_targets=[(8,8),(9,9)],deferred_targets=[(9,9)],current=(0,0),base=(0,0),distance_budget=0)
    x=metrics(c,[(0,0)]);assert x==calculate(c,[(0,0)]) and x['active_coverage']==1 and x['published_coverage']==.5 and x['overlap_ratio'] is None
    assert percentile([0,10],.95)==9.5
    return count+1
def main():
    protocol=read(H/'protocol.json')
    for f,h in protocol['files'].items():assert sha(f)==h,f
    # Extract only the original pure metric definition; never execute the old
    # script's imports/main or write into its archived output directory.
    source=Path(protocol['legacy_metric_source'])
    tree=ast.parse(source.read_text(encoding='utf-8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='metrics')
    namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
    legacy=namespace['metrics']
    tested=tests();records=[]
    for batch in protocol['batches']:
        root=Path(batch['root']);p=read(root/'protocol.json');cases={x['case_id']:x for x in p['cases']}
        checks=read(root/'execution/checks.json');assert len(checks)==batch['expected_calls']
        for row in checks:
            assert not row['technical_failure'];c=read(cases[row['case_id']]['input']);path=root/'execution/results'/(row['run_id']+'.json');result=read(path)
            raw=result['raw'];route=raw['route'];a=metrics(c,route);b=calculate(c,route)
            assert a==b and a['complete_legal'] and row['valid'] and a['length']==row['steps']
            old_metrics=legacy(route,set(map(tuple,c['targets'])),set(map(tuple,c['covered'])))
            for key,value in old_metrics.items():assert a['missing_active' if key=='missing_targets' else key]==value
            if batch['id']=='KR1_PAIR':timely=result['eligible'];assert timely==(result['complete'] and result['entry_seconds']<20 and result['independent_call_seconds']<20)
            else:timely=row['strict_timely'];assert timely==(result['entry_seconds']<=20)
            assert timely==row['timely'] # this dataset has no 10ms-boundary disagreement
            assert sha(path)==row['result_sha256']
            meta=cases[row['case_id']]
            records.append(dict(batch=batch['id'],run_id=row['run_id'],case_id=row['case_id'],map_id=meta['original_name'].rsplit('__',1)[0],state=meta['state'],scale=meta['scale'],method=row['method'],seed=row['seed'],timely=timely,entry_seconds=result['entry_seconds'],independent_call_seconds=result.get('independent_call_seconds'),source_path=str(path),m=a))
    summary={}
    for batch in protocol['batches']:
        own=[x for x in records if x['batch']==batch['id']]
        summary[batch['id']]={m:summarize([x for x in own if x['method']==m]) for m in sorted({x['method'] for x in own})}
    # Within batch, both methods + both repeats must be timely for an endpoint
    # pair. Primary KR1 batch has 20 such states; no cross-batch comparisons.
    paired=[]
    for cid in sorted({x['case_id'] for x in records if x['batch']=='KR1_PAIR'}):
        xs=[x for x in records if x['batch']=='KR1_PAIR' and x['case_id']==cid];assert len(xs)==4 and all(x['timely'] for x in xs)
        pair=dict(case_id=cid,map_id=xs[0]['map_id'],state=xs[0]['state'],scale=xs[0]['scale'])
        for m in ('PPCPP','CAP_KR1'):
            own=[x for x in xs if x['method']==m];assert own[0]['m']==own[1]['m']
            pair[m]=own[0]['m']
        paired.append(pair)
    measures=('length','overlap_ratio','turns90','turns180','historical_target_steps','repeated_new_target_steps','non_target_steps','return_tail_steps')
    wins={}
    for group in ('all','control','event','small','medium','large'):
        xs=[x for x in paired if group=='all' or group in (x['state'],x['scale'])];wins[group]={}
        for key in measures:
            ds=[x['PPCPP'][key]-x['CAP_KR1'][key] for x in xs if x['PPCPP'][key] is not None and x['CAP_KR1'][key] is not None]
            wins[group][key]=dict(n=len(ds),PPCPP_better=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),PPCPP_worse=sum(d>0 for d in ds))
    save('per_run.json',records);save('summary.json',summary);save('paired_states.json',paired);save('paired_wins.json',wins)
    save('audit_results.json',dict(metric_crosschecks=tested,source_routes=len(records),independent_metric_agreements=len(records),planners_called=0,source_hashes_unchanged=all(sha(f)==h for f,h in protocol['files'].items()),no_claim_of_new_independent_maps=True))
    print(json.dumps(dict(metric_crosschecks=tested,source_routes=len(records),planners_called=0,summary=summary),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
