"""Full read-only audit; saved replay is checked here, NEVER read by the solver."""
import json,sys,statistics
from run import H,R,read,sha,protect,gate_records
from checks import audit,norm
from analyze import METHODS,TOTAL_KEYS,percentile
from crosscheck import calculate
from metrics import metrics
def main():
    p=protect();rows=read(H/'execution/checks.json');assert len(rows)==len(p['jobs'])==282 and [x['job'] for x in rows]==p['jobs']
    gs=gate_records();g=read(H/'gate_PASS.json');assert g['all_pass'] and len(gs)==g['calls']==456+2+sum(g['deadline_stage_calls'].values())+3
    for x in gs:
        audit(x['input'],x['result'])
        if x['injection']:assert x['result']['status']=='deadline' and not x['result']['route']
    for i in range(0,456,4):
        group=gs[i:i+4];assert [x['method'] for x in group]==['PPCPP','FIRST','ONE','STRUCT'] and all(x['input']==group[0]['input'] for x in group)
        n=group[0]['result']
        if n['status']=='core_complete':
            for x in group[1:]:
                b=x['result']['branches'][0];assert b['route']==n['route'] and b['trace']==n['trace']
            assert group[2]['result']['route']==n['route'] and group[2]['result']['trace']==n['trace']
    lookup={};branches=0
    for x in rows:
        j=x['job'];path=H/'execution/results'/(j['run_id']+'.json');r=read(path);raw=r['raw'];c=read(j['input']);audit(c,raw);assert sha(path)==x['result_sha256'] and r['job']==j
        assert r['eligible']==x['eligible']==(raw['status']=='core_complete' and r['entry_seconds']<20 and r['independent_seconds']<20)
        assert x['entry_seconds']==r['entry_seconds'] and 0<=raw['seconds']<=r['entry_seconds']<=r['independent_seconds']
        if raw['route']:assert metrics(c,raw['route'])==calculate(c,raw['route'])==x['metrics']
        else:assert x['metrics'] is None
        for b in raw.get('branches',[]):
            if b['route']:assert metrics(c,b['route'])==calculate(c,b['route']);branches+=1
        lookup[j['batch'],j['case_id'],j['seed'],j['method']]=r
    replay=read(R/'PPCPP结构触发可辨识性审查_v0.1_20261020/analysis.json');baseline_pairs=0;replay_pairs=0;repeat_pairs=0
    for case in p['cases']:
        expected=next(x for x in replay['states'] if x['batch']==case['batch'] and x['case_id']==case['case_id'])
        for seed in (20261018,20261019):
            n=lookup[case['batch'],case['case_id'],seed,'PPCPP']['raw'];pair_good=n['status']=='core_complete'
            for m in ('FIRST','STRUCT'):
                raw=lookup[case['batch'],case['case_id'],seed,m]['raw']
                if n['status']=='core_complete' and raw['branches'] and raw['branches'][0]['status']=='core_complete':
                    b=raw['branches'][0];assert norm(b['route'])==norm(n['route']) and norm(b['trace'])==norm(n['trace'])
                else:pair_good=False
            baseline_pairs+=pair_good
            raw=lookup[case['batch'],case['case_id'],seed,'STRUCT']['raw'];source=expected['selections']['TWO_WINDOW_REPLAY'];prior=read(expected['sources'][source])['raw']
            if raw['status']=='core_complete':
                assert norm(raw['route'])==norm(prior['route']) and norm(raw['trace'])==norm(prior['trace'])
                assert raw['override_recovery']==({'FIRST':1,'SECOND':2}.get(source))
                replay_pairs+=1
        for m in METHODS:
            rs=[lookup[case['batch'],case['case_id'],seed,m]['raw'] for seed in (20261018,20261019)]
            if all(r['status']=='core_complete' for r in rs):
                assert norm(rs[0]['route'])==norm(rs[1]['route']) and norm(rs[0]['trace'])==norm(rs[1]['trace']);repeat_pairs+=1
    a=read(H/'analysis.json');assert len(a['states'])==47 and a['formal_calls']==282
    for s in a['states']:
        for m,v in s['methods'].items():
            xs=[x for x in rows if x['job']['batch']==s['batch'] and x['job']['case_id']==s['case_id'] and x['job']['method']==m]
            assert len(xs)==2 and all(x['metrics']==v['metrics'] for x in xs if x['metrics'] is not None) and v['eligible']==all(x['eligible'] for x in xs)
            if m!='PPCPP':
                rs=[lookup[s['batch'],s['case_id'],x['job']['seed'],m]['raw'] for x in xs];raw=next((r for r in rs if r['status']=='core_complete'),rs[0]);assert v['triggered']==(raw['branch_state'] is not None) and v['selected']==raw['selected_branch'] and v['candidates']==len(raw['branches'])
                if m=='STRUCT':assert norm(v['windows'])==norm(raw['structural_windows']) and v['trigger_recovery']==raw['override_recovery']
                if raw['status']=='core_complete':
                    assert sum(v['cost'].values())==v['metrics']['length']
                    b=raw['branches'][raw['selected_branch']]
                    if raw['branch_state']:
                        k=1 if m=='FIRST' else raw['override_recovery'];e=[e for e in b['trace'] if e['kind']=='recovery'][k-1];i=b['trace'].index(e);end=b['trace'][i+1]['index'];ret=b['trace'][-1]['index']
                        assert v['cost']==dict(prefix=e['index'],approach=end-e['index'],continuation=ret-end,return_steps=len(b['route'])-1-ret)
                    else:assert v['cost']==dict(coverage=b['trace'][-1]['index'],return_steps=len(b['route'])-1-b['trace'][-1]['index'])
                    assert v['candidate_goals']==[b['forced_goal'] for b in raw['branches']] and v['candidate_steps']==[len(b['route'])-1 if b['route'] else None for b in raw['branches']]
    for batch,s in a['summary'].items():
        ss=[x for x in a['states'] if x['batch']==batch];assert s['n']==len(ss)
        for m,v in s['methods'].items():
            ms=[x['methods'][m]['metrics'] for x in ss if x['methods'][m]['eligible']]
            for k in TOTAL_KEYS:assert v['totals'][k]==sum(x[k] for x in ms)
            t=v['totals']
            for k,num,den in [('overlap_pooled','duplicate_target_arrivals','target_arrivals'),('active_coverage_pooled','active_covered','active_targets'),('published_coverage_pooled','published_covered','published_targets'),('remaining_completion_pooled','newly_completed','remaining_before')]:
                if t[den]:assert t[k]==t[num]/t[den]
            xs=[x for x in rows if x['job']['batch']==batch and x['job']['method']==m];ts=[x['entry_seconds'] for x in xs]
            assert v['calls']==len(xs) and v['eligible']==sum(x['eligible'] for x in xs)
            assert v['time_mean']==statistics.mean(ts) and v['time_median']==statistics.median(ts) and v['time_p95']==percentile(ts) and v['time_max']==max(ts)
            assert v['triggered']==sum(x['methods'][m].get('triggered',False) for x in ss) and v['structural_checks']==sum(len(x['methods'][m].get('windows',[])) for x in ss)
            assert v['trigger_at_first']==sum(x['methods'][m].get('trigger_recovery')==1 for x in ss) and v['trigger_at_second']==sum(x['methods'][m].get('trigger_recovery')==2 for x in ss)
        for name,pair in s['pairs'].items():
            ma,mb=name.split('_vs_');pairs=[(x['methods'][ma]['metrics']['length'],x['methods'][mb]['metrics']['length']) for x in ss if x['methods'][ma]['eligible'] and x['methods'][mb]['eligible']]
            assert pair['common_states']==len(pairs) and pair['shorter']==sum(x<y for x,y in pairs) and pair['equal']==sum(x==y for x,y in pairs) and pair['longer']==sum(x>y for x,y in pairs)
            assert pair['total_a']==sum(x for x,y in pairs) and pair['total_b']==sum(y for x,y in pairs) and pair['difference']==sum(x-y for x,y in pairs)
            if pair['mean_relative'] is not None:assert pair['mean_relative']==statistics.mean((x-y)/y for x,y in pairs)
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,formal_calls=282,gate_calls=len(gs),candidate_branches_audited=branches,unique_inputs=47,baseline_trace_pairs=baseline_pairs,replay_trace_pairs=replay_pairs,repeated_seed_trace_pairs=repeat_pairs,holdout=False,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
