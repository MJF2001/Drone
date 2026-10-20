"""Read saved comparison evidence; independently check routes and scope."""
import statistics,importlib.util
from run_continuous_comparison_20261016 import *
RESULT=ALGO/'continuous_history_diagnostics/comparison_verification_v0.1_20261016'
def main():
    manifest(RUN);protocol=read(RUN/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    from verify_road_range_diagnostic_20261015 import independent_plan
    from verify_outer_connector_diagnostic_20261016 import assignment
    spec=importlib.util.spec_from_file_location('_continuous_frozen_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py');aud=importlib.util.module_from_spec(spec);spec.loader.exec_module(aud)
    from prepare_road_range_diagnostic_20261015 import snapshot
    rows=[json.loads(v) for v in (RUN/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==len(protocol['jobs'])==80 and len({r['run_id'] for r in rows})==80
    core_count=structures=0;audits=[];fallback_checks=[]
    for j,r in zip(protocol['jobs'],rows):
        assert all(r[k]==v for k,v in j.items());c=read(Path(j['case']));p=RUN/'runs'/(j['run_id']+'.json')
        if r['worker_status']!='returned':assert not r['valid'];continue
        payload=read(p);raw=payload['raw'];s=snapshot(c)
        assert payload['case_sha256']==sha(Path(j['case'])) and payload['seed']==raw['seed']==j['seed']
        assert payload['method']==j['method'] and payload['budget']==raw['budget']==j['budget']
        assert raw['seconds']==r['seconds']<=payload['solve_plus_audits_seconds']+1e-6
        assert r['overrun_gt_10ms']==(raw['seconds']>j['budget']+.01)
        route=tuple(map(tuple,raw['route']));a=aud.audit(s,route) if route else None;valid=bool(a and a['valid'])
        assert valid==r['valid'] and payload['independent_route_check']==route_check(c,route)
        if valid:assert a==raw['independent_audit'] and a['length']==r['steps']
        audits.append(dict(run_id=j['run_id'],valid=valid,steps=r['steps']))
        if j['method']=='P2_MULTI':continue
        d=raw['detail'];plan=independent_plan(c);cfg=plan['plans']['R_PLUS1'];old=c['old_route'];l,rr=cfg['left'],cfg['right']
        if d['range_plan'] is not None:assert d['range_plan']==plan;structures+=1
        if d['responsibilities'] is not None:assert d['responsibilities']==assignment(c,cfg)
        if d['outside'] is not None:assert d['outside']['prefix']==old[:l+1] and d['outside']['suffix']==old[rr:]
        for key in ('acceptances','core_acceptances'):assert all(0<=e['seconds']<=j['budget'] for e in d[key])
        if raw['core_route']:
            core=tuple(map(tuple,raw['core_route']));patch=raw['core_patch'];assert patch[0]==old[l] and patch[-1]==old[rr:][0]
            assert set(map(tuple,cfg['required']))<=set(map(tuple,patch))
            assert list(map(list,core))==old[:l]+patch+old[rr+1:]
            assert aud.audit(s,core)==raw['core_independent_audit'] and raw['core_independent_audit']['valid'];core_count+=1
        entries=d['acceptances'];fallback=next((e['steps'] for e in entries if e['label']=='common_fallback'),None)
        fallback_checks.append(dict(run_id=j['run_id'],global_fallback_steps=fallback,selected_steps=r['steps'],source=r['source'],improves_recorded_fallback=fallback is not None and r['steps']<fallback))
    paired=[]
    for b in (1,20):
        vals=[]
        for mid in sorted({r['map_id'] for r in rows}):
            for rep in (0,1):
                x=next(r for r in rows if (r['map_id'],r['budget'],r['repeat'],r['method'])==(mid,b,rep,'LITERAL'))
                y=next(r for r in rows if (r['map_id'],r['budget'],r['repeat'],r['method'])==(mid,b,rep,'P2_MULTI'))
                vals.append(dict(map_id=mid,repeat=rep,valid_pair=x['valid'] and y['valid'],local_steps=x['steps'],P2_steps=y['steps'],difference=x['steps']-y['steps'] if x['valid'] and y['valid'] else None,relative=x['steps']/y['steps']-1 if x['valid'] and y['valid'] else None))
        valid=[v for v in vals if v['valid_pair']]
        paired.append(dict(budget=b,paired=len(valid),shorter=sum(v['difference']<0 for v in valid),equal=sum(v['difference']==0 for v in valid),longer=sum(v['difference']>0 for v in valid),mean_relative=statistics.mean(v['relative'] for v in valid) if valid else None,sum_difference=sum(v['difference'] for v in valid),per_pair=vals))
    stats=[]
    for b in (1,20):
        for m in ('LITERAL','P2_MULTI'):
            r=[r for r in rows if (r['budget'],r['method'])==(b,m)];t=[v['seconds'] for v in r if v['seconds'] is not None]
            stats.append(dict(budget=b,method=m,valid=sum(v['valid'] for v in r),sum_steps=sum(v['steps'] for v in r if v['valid']),mean_seconds=statistics.mean(t) if t else None,overruns=sum(v['overrun_gt_10ms'] for v in r),sources={str(s):sum(v['source']==s for v in r) for s in {v['source'] for v in r}}))
    RESULT.mkdir(exist_ok=False)
    summary=dict(calls=80,valid=sum(v['valid'] for v in rows),final_audits=len(audits),core_audits=core_count,structural_checks=structures,overruns=sum(v['overrun_gt_10ms'] for v in rows),max_overrun_seconds=max(v['seconds']-v['budget'] for v in rows if v['seconds'] is not None),protected_unchanged=True,holdout_used=False)
    for n,o in [('summary',summary),('route_checks',audits),('paired_summary',paired),('method_summary',stats),('fallback_checks',fallback_checks)]:write(RESULT/(n+'.json'),o)
    write(RESULT/'sha256.json',{str(p.relative_to(RESULT)):sha(p) for p in RESULT.rglob('*') if p.is_file()});print(json.dumps(summary,ensure_ascii=False));print(json.dumps([{k:v for k,v in p.items() if k!='per_pair'} for p in paired],ensure_ascii=False))
if __name__=='__main__':main()
