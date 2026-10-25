import json,statistics
from pathlib import Path
from checks import norm
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    p=read(H/'protocol.json');rows=read(H/'execution/checks.json');assert len(rows)==282
    state=[];times={};equiv=0
    for case in p['cases']:
        own=[r for r in rows if r['job']['batch']==case['batch'] and r['job']['case_id']==case['case_id']];s=dict(**case,methods={})
        for method in ('PPCPP','ONE','THREE'):
            xs=[x for x in own if x['job']['method']==method];assert len(xs)==2
            assert xs[0]['metrics']==xs[1]['metrics']
            raw=read(H/'execution/results'/(xs[0]['job']['run_id']+'.json'))['raw'];s['methods'][method]=dict(metrics=xs[0]['metrics'],eligible=all(x['eligible'] for x in xs),raw=raw)
        native=s['methods']['PPCPP']['raw'];one=s['methods']['ONE']['raw'];three=s['methods']['THREE']['raw']
        assert norm(one['route'])==norm(native['route']) and norm(one['trace'])==norm(native['trace'])
        assert norm(three['branches'][0]['route'])==norm(native['route']) and norm(three['branches'][0]['trace'])==norm(native['trace']);equiv+=1
        entry=s['methods']['THREE'];s['triggered']=entry['raw']['branch_state'] is not None;s['candidates']=len(entry['raw']['branches']);s['selected']=entry['raw']['selected_branch']
        s['difference']=entry['metrics']['length']-s['methods']['PPCPP']['metrics']['length'];s['relative']=s['difference']/s['methods']['PPCPP']['metrics']['length']
        for method in s['methods']:s['methods'][method].pop('raw')
        state.append(s)
    summary={}
    for batch in ('original20','controlled27'):
        ss=[x for x in state if x['batch']==batch];summary[batch]=dict(n=len(ss),shorter=sum(x['difference']<0 for x in ss),equal=sum(x['difference']==0 for x in ss),longer=sum(x['difference']>0 for x in ss),mean_relative=statistics.mean(x['relative'] for x in ss),triggered=sum(x['triggered'] for x in ss),selected_alternative=sum(x['selected']!=0 for x in ss),methods={})
        for method in ('PPCPP','ONE','THREE'):
            xs=[x for x in rows if x['job']['batch']==batch and x['job']['method']==method];ts=sorted(x['entry_seconds'] for x in xs);pos=(len(ts)-1)*.95;i=int(pos)
            totals={k:sum(x['methods'][method]['metrics'][k] for x in ss) for k in ('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','return_tail_steps','target_arrivals','duplicate_target_arrivals')}
            totals['overlap_pooled']=totals['duplicate_target_arrivals']/totals['target_arrivals']
            summary[batch]['methods'][method]=dict(totals=totals,calls=len(xs),eligible=sum(x['eligible'] for x in xs),time_mean=statistics.mean(ts),time_median=statistics.median(ts),time_p95=ts[i]+(ts[min(i+1,len(ts)-1)]-ts[i])*(pos-i),time_max=max(ts))
    save('analysis.json',dict(summary=summary,states=state,equivalent_unique_states=equiv,formal_calls=282))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
