import json,sys,statistics
from pathlib import Path
from collections import Counter
H=Path(__file__).resolve().parent;R=H.parent
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def trace(c,r,m):
    path=list(map(tuple,r['route']));cost=Counter();detail=[]
    if m=='PPCPP':
        es=r['trace']
        for k,e in enumerate(es):
            a=e['index'];b=es[k+1]['index'] if k+1<len(es) else len(path)-1;cost[e['kind']]+=b-a
            if e['kind']!='local':detail.append(dict(kind=e['kind'],start=a,end=b,goal=e['goal'],steps=b-a))
    elif m=='CSTAR':
        cursor=0
        for e in r['task_events']:
            a=e['start_index'];b=e['end_index'];assert a==cursor and b>=a;cursor=b;cost[e['mode']]+=b-a
        cost['return']=len(path)-1-cursor
        detail=[{k:e[k] for k in ('type','step','case','start','goal','end','targets','moved_steps') if k in e} for e in r['events']]
    else:
        total=0
        seen=set(map(tuple,c['covered']));targets=set(map(tuple,c['targets']));seen.add(path[0]);fresh=[]
        for q in path[1:]:fresh.append(q in targets and q not in seen);seen.add(q)
        for plan in r['plans']:
            a=plan['path_start'];b=plan['path_end'];required=set(map(tuple,plan['required']));first={}
            for i in range(a,b+1):
                if path[i] in required:first.setdefault(path[i],i)
            assert set(first)==required
            entry=min(first.values());last=max(first.values());cost['entry']+=entry-a;cost['service']+=last-entry;cost['interface_tail']+=b-last;total+=b-a
            d=dict(region_id=plan['region_id'],required=len(required),start=plan['start'],target=plan['end'],target_source=plan.get('end_source',plan.get('target_state',{}).get('source')),entry=entry-a,service=last-entry,interface_tail=b-last,tail_other_task_credit=sum(fresh[last:b]),target_inside_required=tuple(plan['end']) in required if plan['end'] is not None else None,executed_endpoint=path[b],virtual_end_clipped=m=='TRACE' and plan['end'] is not None)
            detail.append(d)
        cost['return']=len(path)-1-total
    assert sum(cost.values())==len(path)-1
    return dict(costs=dict(cost),decisions=detail)
def main():
    p=read(H/'protocol.json');rs=read(H/'execution/checks.json');assert len(rs)==270
    rows=[];trace_records=[]
    for case in p['cases']:
        row=dict(case_id=case['case_id'],factor=case['factor'],template=case['template'],level=case['level'],methods={})
        for m in p['methods']:
            xs=[x for x in rs if x['job']['case_id']==case['case_id'] and x['job']['method']==m];assert len(xs)==2
            identical=xs[0]['metrics']==xs[1]['metrics']
            complete=all(x['eligible'] for x in xs)
            row['methods'][m]=dict(eligible=complete,repeat_identical=identical,metrics=xs[0]['metrics'],mean_seconds=statistics.mean(x['entry_seconds'] for x in xs))
            if complete:
                raw=read(H/'execution/results'/(xs[0]['job']['run_id']+'.json'))['raw'];d=trace(read(case['input']),raw,m);row['methods'][m]['trace']=d
                trace_records.append(dict(origin='controlled',case_id=case['case_id'],method=m,source=str(H/'execution/results'/(xs[0]['job']['run_id']+'.json')),detail=d))
        rows.append(row)
    factors={}
    for factor in ('gap','history','barrier'):
        factors[factor]={}
        for m in p['methods'][1:]:
            xs=[x for x in rows if x['factor']==factor and x['methods']['PPCPP']['eligible'] and x['methods'][m]['eligible']]
            d=[x['methods']['PPCPP']['metrics']['length']-x['methods'][m]['metrics']['length'] for x in xs]
            patterns=[]
            for template in (0,1,2):
                own=sorted([x for x in xs if x['template']==template],key=lambda x:x['level']);absd=[x['methods']['PPCPP']['metrics']['length']-x['methods'][m]['metrics']['length'] for x in own]
                patterns.append(dict(template=template,deltas=absd,increasing=len(absd)==3 and absd[0]<=absd[1]<=absd[2] and absd[0]<absd[2],decreasing=len(absd)==3 and absd[0]>=absd[1]>=absd[2] and absd[0]>absd[2],changes_from_boundary=[v-absd[0] for v in absd[1:]] if absd else []))
            stable_abs=all(x['increasing'] for x in patterns) or all(x['decreasing'] for x in patterns)
            contrasts=[]
            if factor=='history':
                for i in (0,1):
                    v=[x['changes_from_boundary'][i] for x in patterns];contrasts.append(dict(to_level=i+1,changes=v,all_positive=all(z>0 for z in v),all_negative=all(z<0 for z in v)))
            factors[factor][m]=dict(paired_states=len(d),ppcpp_shorter=sum(z<0 for z in d),equal=sum(z==0 for z in d),ppcpp_longer=sum(z>0 for z in d),mean_absolute_gap=statistics.mean(d),stable_absolute_monotonic=stable_abs if factor!='history' else None,patterns=patterns,history_contrasts=contrasts)
    old=[]
    for selection in p['selected_cases']:
        c=read(selection['input']);entry=dict(selection=selection,methods={})
        for m,key in [('PPCPP','ppcpp_source'),(selection['opponent'],'opponent_source')]:
            raw=read(selection[key])['raw'];entry['methods'][m]=dict(metrics=metrics(c,raw['route']),trace=trace(c,raw,m))
        old.append(entry)
    save('analysis.json',dict(rows=rows,factors=factors,old_cases=old,formal_calls=270,all_valid=sum(x['valid'] for x in rs),all_eligible=sum(x['eligible'] for x in rs),repeat_consistent=sum(v['repeat_identical'] for row in rows for v in row['methods'].values())))
    save('decision_trace.json',trace_records)
    for f,ms in factors.items():
        for m,d in ms.items():print(f,m,'win',d['ppcpp_shorter'],d['equal'],d['ppcpp_longer'],'patterns',[x['deltas'] for x in d['patterns']],'stable',d['stable_absolute_monotonic'],'contrasts',d['history_contrasts'])
if __name__=='__main__':main()
