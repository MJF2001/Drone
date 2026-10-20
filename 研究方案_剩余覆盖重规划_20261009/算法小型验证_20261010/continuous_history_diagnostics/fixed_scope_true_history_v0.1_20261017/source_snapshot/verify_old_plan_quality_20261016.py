"""Saved evidence verification, no planning calls and no holdout access."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,math,statistics
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
RUN=ALGO/'old_plan_quality_diagnostics/run_v0.1_20261016'
OUT=ALGO/'old_plan_quality_diagnostics/verification_v0.1_20261016'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def manifest(p):assert all(sha(p/n)==h for n,h in read(p/'sha256.json').items())
def main():
    manifest(RUN);protocol=read(RUN/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    rows=[json.loads(s) for s in (RUN/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    jobs=protocol['preparation_jobs']+protocol['comparison_jobs'];assert len(rows)==len(jobs)==108
    assert [r['run_id'] for r in rows]==[j['run_id'] for j in jobs]
    assert len({r['run_id'] for r in rows})==108
    spec=importlib.util.spec_from_file_location('_frozen_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    from verify_road_range_diagnostic_20261015 import independent_plan
    audits=[];cores=0;structural=0;lookup={};payloads={}
    for row,job in zip(rows,jobs):
        assert all(row[k]==v for k,v in job.items());c=read(Path(job['case']))
        assert c['metadata']['split']=='development' and c['metadata']['event']=='no_change'
        assert c['metadata']['range_diagnostic']['role']=='control'
        path=RUN/'runs'/(row['run_id']+'.json')
        if not path.exists() or row['worker_status']!='returned':assert not row['valid'];continue
        p=read(path);raw=p['raw'];payloads[row['run_id']]=p
        assert p['case_sha256']==sha(Path(job['case']))
        assert p['seed']==c['metadata']['range_diagnostic']['paired_seed']==raw['seed']
        assert p['method']==job['method'] and p['budget']==raw['budget']==job['budget']
        assert raw['seconds']==row['seconds']<=p['solve_plus_audits_seconds']+.000001
        assert row['overrun_gt_10ms']==(raw['seconds']>job['budget']+.01)
        s=SimpleNamespace(free=set(map(tuple,c['free'])),targets=set(map(tuple,c['targets'])),covered=set(map(tuple,c['covered'])),
            current=tuple(c['current']),base=tuple(c['base']),radius=0,distance_budget=c['distance_budget'])
        route=tuple(map(tuple,raw['route']))
        if route:
            a=auditor.audit(s,route);assert a['valid'] and not row['watchdog_timeout'] and row['valid']
            assert a==raw['independent_audit'] and a['length']==row['steps']
            assert p['independent_route_check']==dict(valid=True,steps=len(route)-1)
            audits.append(dict(run_id=row['run_id'],steps=a['length'],valid=True))
        else:assert not row['valid']
        if job['method']=='KEEP_EMPTY':
            d=raw['detail'];plan=independent_plan(c)
            if d['range_plan'] is not None:
                assert d['range_plan']==plan;structural+=1
                cfg=plan['plans']['R_SEED'];assert cfg['left']==cfg['right']==0 and cfg['required']==[]
            for k in ('acceptances','core_acceptances'):assert all(0<=e['seconds']<=job['budget'] for e in d[k])
            if raw['core_route']:
                core=tuple(map(tuple,raw['core_route']));assert core==tuple(map(tuple,c['old_route']))
                assert tuple(map(tuple,raw['core_patch']))==(s.current,)
                assert auditor.audit(s,core)==raw['core_independent_audit'] and raw['core_independent_audit']['valid'];cores+=1
        if job['phase']=='comparison':lookup[job['map_id'],job['reference'],job['budget'],job['method']]=row
    refs=read(RUN/'reference_ledger.json');reference_checks=[]
    for i,e in enumerate(refs):
        source=read(Path(e['source_case']));raw=read(RUN/'inputs'/f'c{i:02d}_RAW.json');strong=read(RUN/'inputs'/f'c{i:02d}_P2_REF.json')
        assert raw==source and sha(Path(e['source_case']))==e['source_sha256']
        assert raw.keys()==strong.keys() and all(raw[k]==strong[k] for k in raw if k!='old_route')
        assert strong['old_route']==payloads[e['preparation_run_id']]['raw']['route']
        assert sha(RUN/'inputs'/f'c{i:02d}_RAW.json')==e['raw_case_sha256']
        assert sha(RUN/'inputs'/f'c{i:02d}_P2_REF.json')==e['reference_case_sha256']
        for c in (raw,strong):
            s=SimpleNamespace(free=set(map(tuple,c['free'])),targets=set(map(tuple,c['targets'])),covered=set(map(tuple,c['covered'])),
                current=tuple(c['current']),base=tuple(c['base']),radius=0,distance_budget=c['distance_budget'])
            assert auditor.audit(s,tuple(map(tuple,c['old_route'])))['valid']
            plan=independent_plan(c);assert plan['plans']['R_SEED']['left']==plan['plans']['R_SEED']['right']==0
        reference_checks.append(dict(map_id=e['map_id'],raw_steps=e['raw_steps'],reference_steps=e['reference_steps'],
            preparation_seconds=payloads[e['preparation_run_id']]['raw']['seconds'],only_old_route_changed=True))
    maps=[e['map_id'] for e in refs];assert len(set(maps))==12
    paired=[]
    for budget in (1,20):
        for reference in ('RAW','P2_REF'):
            vals=[];fails=[]
            for mid in maps:
                x=lookup.get((mid,reference,budget,'KEEP_EMPTY'));y=lookup.get((mid,reference,budget,'P2_MULTI'))
                if x and y and x['valid'] and y['valid']:
                    vals.append(dict(map_id=mid,keep_steps=x['steps'],P2_steps=y['steps'],difference=x['steps']-y['steps'],
                        relative=x['steps']/y['steps']-1 if y['steps'] else None))
                else:fails.append(mid)
            paired.append(dict(budget=budget,reference=reference,paired=len(vals),unpaired_maps=fails,
                shorter=sum(v['difference']<0 for v in vals),equal=sum(v['difference']==0 for v in vals),longer=sum(v['difference']>0 for v in vals),
                sum_difference=sum(v['difference'] for v in vals),mean_relative=statistics.mean(v['relative'] for v in vals if v['relative'] is not None),per_map=vals))
    stats=[]
    for reference in ('RAW','P2_REF'):
        for b in (1,20):
            for m in ('KEEP_EMPTY','P2_MULTI'):
                rr=[r for r in rows if r['phase']=='comparison' and r['reference']==reference and r['budget']==b and r['method']==m]
                times=sorted(r['seconds'] for r in rr if r['seconds'] is not None)
                stats.append(dict(reference=reference,budget=b,method=m,attempts=len(rr),valid=sum(r['valid'] for r in rr),
                    sum_steps_valid_only=sum(r['steps'] for r in rr if r['valid']),mean_seconds=statistics.mean(times) if times else None,
                    p95_seconds=times[math.ceil(.95*len(times))-1] if times else None,max_seconds=max(times) if times else None,
                    overrun_gt_10ms=sum(r['overrun_gt_10ms'] for r in rr)))
    sensitivity=[]
    for b in (1,20):
        for m in ('KEEP_EMPTY','P2_MULTI'):
            vals=[]
            for mid in maps:
                a=lookup[mid,'RAW',b,m];z=lookup[mid,'P2_REF',b,m]
                if a['valid'] and z['valid']:vals.append(dict(map_id=mid,raw_steps=a['steps'],reference_steps=z['steps'],difference=z['steps']-a['steps']))
            sensitivity.append(dict(budget=b,method=m,reference_shorter=sum(v['difference']<0 for v in vals),equal=sum(v['difference']==0 for v in vals),
                reference_longer=sum(v['difference']>0 for v in vals),sum_difference=sum(v['difference'] for v in vals),per_map=vals))
    summary=dict(status='independently_verified',calls=108,preparation_calls=12,comparison_calls=96,
        saved_final_audits=len(audits),core_audits=cores,empty_scope_checks=structural,reference_pair_checks=len(reference_checks),
        valid_comparison=sum(r['valid'] for r in rows[12:]),holdout_used=False,solver_called=False,
        preparation_overruns=sum(r['overrun_gt_10ms'] for r in rows[:12]),comparison_overruns=sum(r['overrun_gt_10ms'] for r in rows[12:]),
        max_overrun_seconds=max(0,max(r['seconds']-r['budget'] for r in rows if r['seconds'] is not None)),
        preparation_seconds_sum=sum(r['seconds'] for r in rows[:12]),
        caveat='References add 20s preparation allowance; not equal-total-budget quality ranking, not new maps, not interface/order relaxation.')
    OUT.mkdir(parents=True,exist_ok=False)
    for name,o in [('summary',summary),('paired_summary',paired),('method_summary',stats),('reference_checks',reference_checks),('sensitivity',sensitivity),('route_checks',audits)]:write(OUT/(name+'.json'),o)
    write(OUT/'sha256.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps(summary,ensure_ascii=False));print(json.dumps(paired,ensure_ascii=False))
if __name__=='__main__':main()
