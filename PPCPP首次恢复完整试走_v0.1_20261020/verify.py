import json,sys
from pathlib import Path
from run import H,R,protect,read,sha
from checks import audit,norm
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
from crosscheck import calculate
def main():
    p=protect();rows=read(H/'execution/checks.json');assert len(rows)==282
    for x in read(H/'gates.json'):
        audit(x['input'],x['result'])
        if x['result']['status']=='deadline':assert not x['result']['route']
    gates=read(H/'gate_PASS.json');assert gates['calls']==211 and gates['deadline_stages']==18
    lookup={}
    for x in rows:
        j=x['job'];rp=H/'execution/results'/(j['run_id']+'.json');r=read(rp);c=read(j['input']);audit(c,r['raw']);assert sha(rp)==x['result_sha256']
        assert r['job']==j and r['eligible']==x['eligible'] and r['eligible']==(r['raw']['status']=='core_complete' and r['entry_seconds']<20 and r['independent_seconds']<20)
        assert metrics(c,r['raw']['route'])==calculate(c,r['raw']['route'])==x['metrics']
        lookup[j['batch'],j['case_id'],j['seed'],j['method']]=r
    for c in p['cases']:
        for seed in (20261018,20261019):
            n=lookup[c['batch'],c['case_id'],seed,'PPCPP']['raw']
            for m in ('ONE','THREE'):
                r=lookup[c['batch'],c['case_id'],seed,m]['raw'];b=r['branches'][0]
                assert norm(n['route'])==norm(b['route']) and norm(n['trace'])==norm(b['trace'])
                if m=='ONE':assert norm(r['route'])==norm(n['route'])
                assert len(r['route'])<=len(n['route'])
    a=read(H/'analysis.json');assert len(a['states'])==a['equivalent_unique_states']==47
    for batch,s in a['summary'].items():
        ss=[x for x in a['states'] if x['batch']==batch];assert len(ss)==s['n']
        assert s['shorter']==sum(x['difference']<0 for x in ss) and s['equal']==sum(x['difference']==0 for x in ss) and s['longer']==sum(x['difference']>0 for x in ss)
        assert abs(s['mean_relative']-sum(x['relative'] for x in ss)/len(ss))<1e-12
        for x in ss:
            for method in ('PPCPP','ONE','THREE'):
                actual=next(y for y in rows if y['job']['batch']==batch and y['job']['case_id']==x['case_id'] and y['job']['method']==method)
                assert actual['metrics']==x['methods'][method]['metrics']
        for method,summary in s['methods'].items():
            for key,value in summary['totals'].items():
                if key=='overlap_pooled':continue
                assert value==sum(x['methods'][method]['metrics'][key] for x in ss)
            totals=summary['totals'];assert totals['overlap_pooled']==totals['duplicate_target_arrivals']/totals['target_arrivals']
            timed=sorted(x['entry_seconds'] for x in rows if x['job']['batch']==batch and x['job']['method']==method)
            assert summary['time_max']==max(timed) and abs(summary['time_mean']-sum(timed)/len(timed))<1e-12
            index=(len(timed)-1)*.95;i=int(index);assert summary['time_p95']==timed[i]+(timed[min(i+1,len(timed)-1)]-timed[i])*(index-i)
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,formal_calls=282,gate_calls=211,unique_inputs=47,full_trace_equivalence_pairs=94,holdout=False,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
