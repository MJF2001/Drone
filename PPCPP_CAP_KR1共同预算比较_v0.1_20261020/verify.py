"""Read-only independent all-route/decision, source and summary verification."""
import json,hashlib
from pathlib import Path
from run import protect,common,audit_kr1,pa
from analyze import stat
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=protect();freeze=read(H/'freeze.json');assert freeze['method_id']=='CAP_KR1' and not freeze['paper_equivalent'] and not freeze['replaces_CAP']
    old=H.parent/'CAP完整接续候选_v0.1_20261020/runtime'
    for name,h in freeze['runtime_sha256'].items():assert sha(H/name)==h==sha(old/Path(name).name)
    rows=read(H/'execution/checks.json');jobs={j['run_id']:j for j in p['jobs']}
    assert len(rows)==len(jobs)==80 and len({x['run_id'] for x in rows})==80
    allrows=read(H/'preflight/checks.json')+rows
    for x in allrows:
        if x['technical_failure']:continue
        r=read(H/('execution' if x['run_id'] in jobs else 'preflight')/'results'/(x['run_id']+'.json'))
        if x['run_id'] in jobs:assert r['job']==jobs[x['run_id']]
        c=read(Path(r['job']['input']));raw=r['raw'];a=common(c,dict(route=raw['route'] if raw else []))
        assert r['complete']==bool(raw and raw['status']==('core_complete' if x['method']=='PPCPP' else 'complete'))
        assert a['valid']==x['valid'] and a['steps']==x['steps']
        if raw:
            if x['method']=='CAP_KR1':audit_kr1(c,raw)
            elif raw['route']:pa.audit(c,raw)
        eligible=r['complete'] and r['entry_seconds']<r['job']['budget'] and r['independent_call_seconds']<r['job']['budget']
        assert r['eligible']==eligible and x['timely']==bool(eligible and a['valid'])
        assert sha(H/('execution' if x['run_id'] in jobs else 'preflight')/'results'/(x['run_id']+'.json'))==x['result_sha256']
    assert all(x['complete'] and not x['eligible'] and not x['accepted_route'] for x in read(H/'preflight/deadline.json'))
    a=read(H/'analysis.json');assert stat(a['pairs'])==a['call_pairs'] and stat(a['states'])==a['unique_state_pairs']
    lookup={(x['case_id'],x['seed'],x['method']):x for x in rows}
    for pair in a['pairs']:
        for m in p['methods']:
            row=lookup[pair['case_id'],pair['seed'],m];assert row['timely'] and row['steps']==pair[m+'_steps']
    for state in a['states']:
        own=[x for x in a['pairs'] if x['case_id']==state['case_id']];assert len(own)==2
        for m in p['methods']:assert state[m+'_steps']==sum(x[m+'_steps'] for x in own)/2
    for m,s in a['methods'].items():
        own=[x for x in rows if x['method']==m];assert s['calls']==len(own) and s['timely']==sum(x['timely'] for x in own) and s['valid']==sum(x['valid'] for x in own)
        assert s['late_valid']==sum(x['valid'] and not x['timely'] for x in own) and s['technical_failures']==sum(x['technical_failure'] for x in own)
        assert s['max_entry_seconds']==max(x['entry_seconds'] for x in own)
    for field,group in (('state','state_groups'),('scale','scale_groups')):
        for key,value in a[group].items():assert stat([x for x in a['states'] if x[field]==key])==value
    identical=0
    for c in p['cases']:
        for method in p['methods']:
            rr=[]
            for seed in p['seeds']:
                x=lookup[c['case_id'],seed,method]
                rr.append(read(H/'execution/results'/(x['run_id']+'.json'))['raw']['route'])
            identical+=rr[0]==rr[1]
    assert identical==a['repeated_routes_identical']==40
    for c in p['cases']:assert sha(Path(c['input']))==sha(Path(c['prior_input']))==c['input_sha256']
    if (H/'manifest.json').exists():
        manifest=read(H/'manifest.json');assert set(manifest)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in manifest.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,formal_calls=80,preflight_calls=4,call_pairs=a['call_pairs']['n'],unique_state_pairs=a['unique_state_pairs']['n'],holdout=False,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
