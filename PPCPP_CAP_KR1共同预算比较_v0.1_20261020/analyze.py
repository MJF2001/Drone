"""Pre-registered paired developer analysis; does not run solvers."""
import json,csv,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def stat(pairs):
    if not pairs:return dict(n=0)
    delta=[(x['PPCPP_steps']-x['CAP_KR1_steps'])/x['CAP_KR1_steps'] for x in pairs]
    return dict(n=len(pairs),PPCPP_shorter=sum(d<0 for d in delta),equal=sum(d==0 for d in delta),PPCPP_longer=sum(d>0 for d in delta),
        mean_relative=sum(delta)/len(delta),median_relative=statistics.median(delta),
        PPCPP_total_steps=sum(x['PPCPP_steps'] for x in pairs),CAP_KR1_total_steps=sum(x['CAP_KR1_steps'] for x in pairs),
        aggregate_relative=(sum(x['PPCPP_steps'] for x in pairs)-sum(x['CAP_KR1_steps'] for x in pairs))/sum(x['CAP_KR1_steps'] for x in pairs))
def csvwrite(name,rows):
    if rows:
        with (H/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    p=read(H/'protocol.json');rows=read(H/'execution/checks.json');done=read(H/'execution/completion.json')
    assert done['executed']==done['scheduled']==len(rows)==80 and not done['not_run']
    cases={x['case_id']:x for x in p['cases']};lookup={(x['case_id'],x['seed'],x['method']):x for x in rows}
    pairs=[];states=[];rep=[]
    for case in p['cases']:
        own=[]
        for seed in p['seeds']:
            a=lookup[case['case_id'],seed,'PPCPP'];b=lookup[case['case_id'],seed,'CAP_KR1']
            if a['timely'] and b['timely']:
                x=dict(case_id=case['case_id'],original_name=case['original_name'],state=case['state'],scale=case['scale'],event=case['event'],seed=seed,PPCPP_steps=a['steps'],CAP_KR1_steps=b['steps'],relative=(a['steps']-b['steps'])/b['steps'])
                pairs.append(x);own.append(x)
        if len(own)==len(p['seeds']):
            x={k:v for k,v in own[0].items() if k not in ('seed','PPCPP_steps','CAP_KR1_steps','relative')}
            for m in p['methods']:x[m+'_steps']=sum(y[m+'_steps'] for y in own)/len(own)
            x['relative']=(x['PPCPP_steps']-x['CAP_KR1_steps'])/x['CAP_KR1_steps'];states.append(x)
        for method in p['methods']:
            routes=[]
            for seed in p['seeds']:
                r=read(H/'execution/results'/(lookup[case['case_id'],seed,method]['run_id']+'.json'))
                routes.append(r['raw']['route'] if r['raw'] else [])
            rep.append(dict(case_id=case['case_id'],method=method,identical=routes[0]==routes[1]))
    methods={}
    for m in p['methods']:
        xs=[x for x in rows if x['method']==m];timed=[x for x in xs if not x['technical_failure']]
        methods[m]=dict(calls=len(xs),valid=sum(x['valid'] for x in xs),timely=sum(x['timely'] for x in xs),late_valid=sum(x['valid'] and not x['timely'] for x in xs),technical_failures=sum(x['technical_failure'] for x in xs),
            mean_entry_seconds=statistics.mean(x['entry_seconds'] for x in timed),max_entry_seconds=max(x['entry_seconds'] for x in timed),max_independent_call_seconds=max(x['independent_call_seconds'] for x in timed),mean_payload_bytes=statistics.mean(x['payload_bytes'] for x in timed))
    out=dict(methods=methods,call_pairs=stat(pairs),unique_state_pairs=stat(states),unpaired_calls=40-len(pairs),state_groups={s:stat([x for x in states if x['state']==s]) for s in sorted({x['state'] for x in states})},scale_groups={s:stat([x for x in states if x['scale']==s]) for s in sorted({x['scale'] for x in states})},repeated_routes_identical=sum(x['identical'] for x in rep),repeated_route_checks=len(rep),states=states,pairs=pairs,repetition=rep)
    (H/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');csvwrite('逐状态结果.csv',states);csvwrite('逐调用配对.csv',pairs)
    print(json.dumps({k:v for k,v in out.items() if k not in ('states','pairs','repetition')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
