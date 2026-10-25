"""Read-only independent metric, decision and source verification."""
import json,sys,statistics
from pathlib import Path
from run import H,R,protect,read,sha
from checks import audit,norm
from audit_branch import bfs
from analyze import METHODS,TOTAL_KEYS,percentile
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
from crosscheck import calculate

def main():
    p=protect();rows=read(H/'execution/checks.json');assert len(rows)==282 and len(p['jobs'])==282
    assert [x['job'] for x in rows]==p['jobs'];gs=read(H/'gates.json');g=read(H/'gate_PASS.json')
    assert g['all_pass'] and g['calls']==len(gs)==256+12+g['supplement_calls']+1+g['deadline_stages']
    for x in gs:
        audit(x['input'],x['result'])
        if x['result']['status']=='deadline':assert not x['result']['route']
    lookup={};branch_count=0
    for x in rows:
        j=x['job'];rp=H/'execution/results'/(j['run_id']+'.json');r=read(rp);c=read(j['input']);raw=r['raw'];audit(c,raw);assert sha(rp)==x['result_sha256']
        assert r['job']==j and r['eligible']==x['eligible'] and r['eligible']==(raw['status']=='core_complete' and r['entry_seconds']<j['budget'] and r['independent_seconds']<j['budget'])
        assert r['entry_seconds']==x['entry_seconds'] and 0<=raw['seconds']<=r['entry_seconds']<=r['independent_seconds']
        if raw['route']:assert metrics(c,raw['route'])==calculate(c,raw['route'])==x['metrics']
        else:assert x['metrics'] is None
        for b in raw.get('branches',[]):
            if b['route']:assert metrics(c,b['route'])==calculate(c,b['route']);branch_count+=1
        lookup[j['batch'],j['case_id'],j['seed'],j['method']]=r
    old=read(R/'PPCPP首次恢复完整试走_v0.1_20261020/protocol.json')
    for c in p['cases']:
        for seed in (20261018,20261019):
            n=lookup[c['batch'],c['case_id'],seed,'PPCPP']['raw']
            for m in ('FIRST','SECOND'):
                r=lookup[c['batch'],c['case_id'],seed,m]['raw']
                if n['status']=='core_complete' and r['branches']:
                    b=r['branches'][0];assert norm(n['route'])==norm(b['route']) and norm(n['trace'])==norm(b['trace'])
                if r['status']=='core_complete':
                    assert len(r['route'])<=len(n['route'])
                    if r['branch_state'] is None:assert norm(n['route'])==norm(r['route']) and norm(n['trace'])==norm(r['trace'])
            job=next(j for j in old['jobs'] if j['batch']==c['batch'] and j['case_id']==c['case_id'] and j['seed']==seed and j['method']=='THREE')
            oldraw=read(R/'PPCPP首次恢复完整试走_v0.1_20261020/execution/results'/(job['run_id']+'.json'))['raw'];f=lookup[c['batch'],c['case_id'],seed,'FIRST']['raw']
            assert norm(oldraw['route'])==norm(f['route']) and norm(oldraw['trace'])==norm(f['trace'])
    a=read(H/'analysis.json');assert len(a['states'])==47 and a['formal_calls']==282
    for s in a['states']:
        c=read(s['input'])
        for m,v in s['methods'].items():
            xs=[x for x in rows if x['job']['batch']==s['batch'] and x['job']['case_id']==s['case_id'] and x['job']['method']==m]
            assert len(xs)==2 and all(x['metrics']==v['metrics'] for x in xs) and v['eligible']==all(x['eligible'] for x in xs)
            if m!='PPCPP':
                r=lookup[s['batch'],s['case_id'],xs[0]['job']['seed'],m]['raw'];assert v['triggered']==(r['branch_state'] is not None) and v['selected']==r['selected_branch'] and v['candidates']==len(r['branches'])
                if r['status']=='core_complete':
                    assert sum(v['cost'].values())==v['metrics']['length']
                    b=r['branches'][r['selected_branch']]
                    if r['branch_state']:
                        k=1 if m=='FIRST' else 2;e=[e for e in b['trace'] if e['kind']=='recovery'][k-1];i=b['trace'].index(e);end=b['trace'][i+1]['index'];ret=b['trace'][-1]['index']
                        assert v['cost']==dict(prefix=e['index'],approach=end-e['index'],continuation=ret-end,return_steps=len(b['route'])-1-ret)
                    assert v['candidate_goals']==[b['forced_goal'] for b in r['branches']] and v['candidate_steps']==[len(b['route'])-1 if b['route'] else None for b in r['branches']]
    for batch,s in a['summary'].items():
        ss=[x for x in a['states'] if x['batch']==batch];assert s['n']==len(ss)
        for m,v in s['methods'].items():
            valid=[x['methods'][m]['metrics'] for x in ss if x['methods'][m]['eligible']]
            for key in TOTAL_KEYS:assert v['totals'][key]==sum(x[key] for x in valid)
            t=v['totals']
            for key,num,den in [('overlap_pooled','duplicate_target_arrivals','target_arrivals'),('active_coverage_pooled','active_covered','active_targets'),('published_coverage_pooled','published_covered','published_targets'),('remaining_completion_pooled','newly_completed','remaining_before')]:
                if t[den]:assert t[key]==t[num]/t[den]
            xs=[x for x in rows if x['job']['batch']==batch and x['job']['method']==m];ts=[x['entry_seconds'] for x in xs]
            assert v['calls']==len(xs) and v['eligible']==sum(x['eligible'] for x in xs)
            assert v['time_mean']==statistics.mean(ts) and v['time_median']==statistics.median(ts) and v['time_p95']==percentile(ts) and v['time_max']==max(ts)
        for name,pair in s['pairs'].items():
            ma,mb=name.split('_vs_');pairs=[(x['methods'][ma]['metrics']['length'],x['methods'][mb]['metrics']['length']) for x in ss if x['methods'][ma]['eligible'] and x['methods'][mb]['eligible']]
            assert pair['common_states']==len(pairs) and pair['shorter']==sum(x<y for x,y in pairs) and pair['equal']==sum(x==y for x,y in pairs) and pair['longer']==sum(x>y for x,y in pairs)
            assert pair['total_a']==sum(x for x,y in pairs) and pair['total_b']==sum(y for x,y in pairs) and pair['difference']==sum(x-y for x,y in pairs)
            if pair['mean_relative'] is not None:assert pair['mean_relative']==statistics.mean((x-y)/y for x,y in pairs)
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,formal_calls=282,gate_calls=len(gs),candidate_branches_audited=branch_count,unique_states=47,baseline_trace_pairs=94,first_vs_prior_trace_pairs=94,holdout=False,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
