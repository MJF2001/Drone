import json,sys,statistics
from pathlib import Path
from run import protect,read,save,H,R,metrics
def trace(c,raw,method):
    path=list(map(tuple,raw['route']));seen=set(map(tuple,c['covered']));t=set(map(tuple,c['targets']));seen.add(path[0]);fresh=[]
    for point in path[1:]:fresh.append(point in t and point not in seen);seen.add(point)
    if method=='PPCPP':
        events=raw['trace'];costs=dict(local=0,recovery=0,return_steps=0);recoveries=[]
        for k,e in enumerate(events):
            start=e['index'];end=events[k+1]['index'] if k+1<len(events) else len(path)-1
            costs['return_steps' if e['kind']=='return' else e['kind']]+=end-start
            if e['kind']=='recovery':recoveries.append(dict(start=start,end=end,goal=e['goal'],steps=end-start,newly_collected=sum(fresh[start:end])))
        assert sum(costs.values())==len(path)-1
        return dict(costs=costs,recoveries=recoveries,decision_count=len(events))
    plans=[]
    for p in raw['plans']:
        s=p['path_start'];e=p['path_end'];required=set(map(tuple,p['required']));first={}
        for i in range(s,e+1):
            if path[i] in required:first.setdefault(path[i],i)
        assert set(first)==required
        entry=min(first.values());last=max(first.values());tail=e-last
        d=dict(region_id=p['region_id'],required_count=len(required),start=p['start'],target=p['end'],target_source=p['target_state']['source'],target_inside_required=tuple(p['end']) in required,
            total=e-s,entry_steps=entry-s,inside_until_last_service_steps=last-entry,interface_tail_steps=tail,
            interface_tail_new_other_targets=sum(fresh[last:e]),target_generation=p['target_state']['generation'])
        assert d['entry_steps']+d['inside_until_last_service_steps']+tail==d['total'];plans.append(d)
    final_return=len(path)-1-sum(p['total'] for p in plans)
    return dict(plans=plans,costs=dict(entry=sum(p['entry_steps'] for p in plans),service=sum(p['inside_until_last_service_steps'] for p in plans),interface_tail=sum(p['interface_tail_steps'] for p in plans),return_steps=final_return),interface_tail_new_other_targets=sum(p['interface_tail_new_other_targets'] for p in plans))
def main():
    p=protect();checks=read(H/'execution/checks.json');assert len(checks)==36
    rows=[];traces=[]
    for case in p['cases']:
        one=dict(case_id=case['case_id'],family=case['family'],gap=case['gap_columns'])
        for method in ('PPCPP','CAP_KR1'):
            xs=[x for x in checks if x['job']['case_id']==case['case_id'] and x['job']['method']==method];assert len(xs)==2 and xs[0]['metrics']==xs[1]['metrics']
            raw=read(H/'execution/results'/(xs[0]['job']['run_id']+'.json'))['raw'];c=read(case['input']);tr=trace(c,raw,method)
            one[method]=dict(metrics=xs[0]['metrics'],trace=tr)
            traces.append(dict(case_id=case['case_id'],method=method,origin='new_controlled',source=str(H/'execution/results'/(xs[0]['job']['run_id']+'.json')),detail=tr))
        one['relative']=(one['PPCPP']['metrics']['length']-one['CAP_KR1']['metrics']['length'])/one['CAP_KR1']['metrics']['length'];rows.append(one)
    trends=[]
    for family in (0,1,2):
        own=sorted([x for x in rows if x['family']==family],key=lambda x:x['gap']);v=[x['relative'] for x in own]
        trends.append(dict(family=family,relative=v,increasing=all(a<=b for a,b in zip(v,v[1:])) and any(a<b for a,b in zip(v,v[1:])),decreasing=all(a>=b for a,b in zip(v,v[1:])) and any(a>b for a,b in zip(v,v[1:]))))
    stable_trend=all(x['increasing'] for x in trends) or all(x['decreasing'] for x in trends)
    stable_advantage=all(all(v<0 for v in x['relative']) for x in trends) or all(all(v>0 for v in x['relative']) for x in trends)
    old=[]
    for x in p['old_cases']:
        c=read(x['input']);raw=read(x['result'])['raw'];d=trace(c,raw,x['method']);old.append(dict(**x,detail=d,metrics=metrics(c,raw['route'])));traces.append(dict(case_id=x['case_id'],method=x['method'],origin='original_read_only',source=x['result'],detail=d))
    save(H/'analysis.json',dict(rows=rows,trends=trends,stable_monotonic_trend=stable_trend,stable_nonzero_advantage=stable_advantage,old_cases=old,new_calls=36,unique_inputs=9,unchanged_implementations=True))
    save(H/'decision_trace.json',traces)
    for x in rows:print(x['case_id'],x['PPCPP']['metrics']['length'],x['CAP_KR1']['metrics']['length'],round(x['relative']*100,3),x['CAP_KR1']['trace']['costs'],x['PPCPP']['trace']['costs'])
    print('stable_monotonic',stable_trend,'stable_advantage',stable_advantage)
    for x in old:print('old',x['case_id'],x['method'],x['metrics']['length'],x['detail']['costs'])
if __name__=='__main__':main()
