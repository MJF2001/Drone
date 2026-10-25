"""Saved-file verification only. Does not invoke the planner or generate cases."""
import json,statistics
from common import H,R,read,sha,protect
from checks import audit,norm
from verify_inputs import check
from analyze import TOTAL_KEYS,percentile
from crosscheck import calculate
from metrics import metrics
from spec import SEEDS,METHODS
from strata import summarize
def main():
    p=protect(True);inp=check();assert len(inp)==36 and read(H/'input_audit.json')['rows']==inp
    gs=[json.loads(l) for l in (H/'gates.jsonl').read_text(encoding='utf-8').splitlines()];assert len(gs)==72 and read(H/'gate_PASS.json')['all_pass']
    for x in gs:audit(x['input'],x['result'])
    for i in range(0,72,2):
        n,o=gs[i:i+2];assert n['method']=='PPCPP' and o['method']=='ONE' and n['case_id']==o['case_id']
        assert n['result']['route']==o['result']['route'] and n['result']['trace']==o['result']['trace']
    rows=read(H/'execution/checks.json');assert len(rows)==540 and [x['job'] for x in rows]==p['jobs'];lookup={};branches=0
    for x in rows:
        j=x['job'];path=H/'execution/results'/(j['run_id']+'.json');r=read(path);c=read(j['input']);raw=r['raw'];audit(c,raw)
        assert sha(path)==x['result_sha256'] and r['job']==j and r['entry_seconds']==x['entry_seconds']
        assert r['eligible']==x['eligible']==(raw['status']=='core_complete' and r['entry_seconds']<20 and r['independent_seconds']<20)
        assert 0<=raw['seconds']<=r['entry_seconds']<=r['independent_seconds']
        if raw['route']:assert metrics(c,raw['route'])==calculate(c,raw['route'])==x['metrics']
        else:assert x['metrics'] is None
        for b in raw.get('branches',[]):
            if b['route']:assert metrics(c,b['route'])==calculate(c,b['route']);branches+=1
        lookup[j['case_id'],j['seed'],j['method']]=raw
    pairs=0;repeat_groups=0
    for c in p['cases']:
        for seed in SEEDS:
            n=lookup[c['case_id'],seed,'PPCPP'];good=n['status']=='core_complete'
            for m in ('FIRST','STRUCT'):
                r=lookup[c['case_id'],seed,m]
                if good and r['branches'] and r['branches'][0]['status']=='core_complete':
                    b=r['branches'][0];assert norm(b['route'])==norm(n['route']) and norm(b['trace'])==norm(n['trace'])
                else:good=False
            pairs+=good
        for m in METHODS:
            rs=[lookup[c['case_id'],seed,m] for seed in SEEDS if lookup[c['case_id'],seed,m]['status']=='core_complete']
            assert not rs or all(norm(r['route'])==norm(rs[0]['route']) and norm(r['trace'])==norm(rs[0]['trace']) for r in rs)
            repeat_groups+=bool(rs)
    a=read(H/'analysis.json');assert len(a['states'])==36 and a['formal_calls']==540
    for s in a['states']:
        for m,v in s['methods'].items():
            xs=[x for x in rows if x['job']['case_id']==s['case_id'] and x['job']['method']==m]
            assert len(xs)==5 and all(x['metrics']==v['metrics'] for x in xs if x['metrics'] is not None) and v['eligible']==all(x['eligible'] for x in xs)
            if m!='PPCPP':
                rs=[lookup[s['case_id'],seed,m] for seed in SEEDS];raw=next((r for r in rs if r['status']=='core_complete'),rs[0])
                assert v['triggered']==(raw['branch_state'] is not None) and v['selected']==raw['selected_branch'] and v['candidates']==len(raw['branches'])
                if m=='STRUCT':assert norm(v['windows'])==norm(raw['structural_windows']) and v['trigger_recovery']==raw['override_recovery']
                if raw['status']=='core_complete':assert sum(v['cost'].values())==v['metrics']['length']
    s=a['summary']['newdev36']
    for m,v in s['methods'].items():
        ms=[x['methods'][m]['metrics'] for x in a['states'] if x['methods'][m]['eligible']]
        for key in TOTAL_KEYS:assert v['totals'][key]==sum(x[key] for x in ms)
        ts=[x['entry_seconds'] for x in rows if x['job']['method']==m]
        assert v['time_mean']==statistics.mean(ts) and v['time_median']==statistics.median(ts) and v['time_p95']==percentile(ts) and v['time_max']==max(ts)
        assert v['calls']==180 and v['eligible']==sum(x['eligible'] for x in rows if x['job']['method']==m)
    for name,v in s['pairs'].items():
        ma,mb=name.split('_vs_');xs=[x for x in a['states'] if x['methods'][ma]['eligible'] and x['methods'][mb]['eligible']];ds=[x['methods'][ma]['metrics']['length']-x['methods'][mb]['metrics']['length'] for x in xs]
        assert v['common_states']==len(xs) and v['shorter']==sum(d<0 for d in ds) and v['equal']==sum(d==0 for d in ds) and v['longer']==sum(d>0 for d in ds) and v['difference']==sum(ds)
    st=read(H/'strata.json');assert st['overall']==summarize(a['states'],rows)
    for key in ('event','size','progress','layout'):
        for value,v in st[key].items():
            states=[x for x in a['states'] if str(x[key])==value];ids={x['case_id'] for x in states};assert v==summarize(states,[r for r in rows if r['job']['case_id'] in ids])
    if (H/'manifest.json').exists():
        seal=read(H/'manifest.json');assert set(seal)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in seal.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,preparation_calls=6,input_gate_calls=72,formal_calls=540,base_maps=6,snapshots=36,history_witnesses=36,future_witnesses=36,candidate_branches=branches,baseline_trace_groups=pairs,five_repeat_groups=repeat_groups,holdout=False,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
