"""Independent saved-route validation and paired descriptive development stats."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,itertools,json,statistics

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_preflights/four_method_paired_v1_20261015'
OUT=ALGO/'development_preflights/four_method_paired_v1_20261015_verification'
METHODS=('P2_MULTI','OARP_CORE2','TREE_MST','PPCPP_CORE4')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    hashes=json.loads((SOURCE/'sha256.json').read_text(encoding='utf-8'))
    assert all(sha(SOURCE/n)==h for n,h in hashes.items())
    protocol=json.loads((SOURCE/'protocol.json').read_text(encoding='utf-8'))
    assert all(sha(Path(p))==h for p,h in protocol['hashes'].items())
    spec=importlib.util.spec_from_file_location('_four_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    rows=[json.loads(line) for line in (SOURCE/'execution_ledger.jsonl').open(encoding='utf-8')]
    assert len(rows)==288 and len({r['run_id'] for r in rows})==288
    assert [r['run_id'] for r in rows]==[j['run_id'] for j in protocol['jobs']]
    checks=[];core_checks=0;lookup={}
    for r in rows:
        data=json.loads(Path(r['case_file']).read_text(encoding='utf-8'));assert data['metadata']['split']=='development'
        path=SOURCE/'runs'/(r['run_id']+'.json')
        if not path.exists() or r['worker_status']!='returned':
            assert not r['valid'];lookup[r['case'],r['repeat'],r['budget'],r['method']]=r;continue
        payload=json.loads(path.read_text(encoding='utf-8'));raw=payload['raw']
        assert raw['seed']==data['metadata'][f"repeat_seed_{r['repeat']}"]
        assert raw['method']==r['method'] and raw['budget']==r['budget']
        pts=lambda k:frozenset(map(tuple,data[k]))
        s=SimpleNamespace(free=pts('free'),targets=pts('targets'),covered=pts('covered'),current=tuple(data['current']),
            base=tuple(data['base']),radius=data['radius'],distance_budget=data['distance_budget'])
        if raw['route']:
            route=tuple(map(tuple,raw['route']));checked=auditor.audit(s,route)
            assert checked==raw['independent_audit'] and checked['valid']
            assert r['valid'] and not r['watchdog_timeout']
            m=payload['metrics'];counts=[0,0,0,0];seen=set(s.covered)|({route[0]}&s.targets)
            pending=set(s.targets)-seen;completion=0 if not pending else None
            for i,p in enumerate(route[1:],1):
                k=3 if p not in s.targets else 1 if p in s.covered else 2 if p in seen else 0
                counts[k]+=1;seen.add(p);pending.discard(p)
                if not pending and completion is None:completion=i
            assert counts==[m[k] for k in ('fresh','historical_repeat','current_repeat','non_target')]
            assert sum(counts)==m['steps']==checked['length']
            denominator=sum(counts[:3]);ratio=(counts[1]+counts[2])/denominator if denominator else None
            assert ratio==m['overlap_ratio']
            vectors=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
            assert m['turns90']==sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vectors,vectors[1:]))
            assert m['turns180']==sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vectors,vectors[1:]))
            assert m['completion_step']==completion and m['return_tail_steps']==len(route)-1-completion
            assert raw['seconds']<=payload['solve_plus_audits_seconds']+.000001
            checks.append(dict(run_id=r['run_id'],valid=True,steps=checked['length']))
        else:assert not r['valid']
        if r['method']=='PPCPP_CORE4' and raw['detail']['core_route']:
            core=auditor.audit(s,tuple(map(tuple,raw['detail']['core_route'])))
            assert core==raw['core_independent_audit'];core_checks+=1
            if raw['detail']['core_valid_before_deadline']:assert core['valid']
        lookup[r['case'],r['repeat'],r['budget'],r['method']]=r
    summaries=[]
    for budget in (1,5,20):
        for method in METHODS:
            group=[r for r in rows if r['budget']==budget and r['method']==method]
            valid=[r for r in group if r['valid']];times=[r['solver_seconds'] for r in group if r['solver_seconds'] is not None]
            target_arrivals=sum(r['metrics']['steps']-r['metrics']['non_target'] for r in valid)
            repeats=sum(r['metrics']['historical_repeat']+r['metrics']['current_repeat'] for r in valid)
            summaries.append(dict(budget=budget,method=method,runs=len(group),valid=len(valid),
                sum_steps=sum(r['metrics']['steps'] for r in valid),
                overlap_pooled=repeats/target_arrivals if target_arrivals else None,
                turns90=sum(r['metrics']['turns90'] for r in valid),turns180=sum(r['metrics']['turns180'] for r in valid),
                solver_seconds_mean=statistics.mean(times),solver_seconds_median=statistics.median(times),solver_seconds_max=max(times),
                fallback=sum(bool(r['fallback_selected']) for r in group),
                oarp_core_tours=sum(bool(r['core_tour_obtained']) for r in group) if method=='OARP_CORE2' else None,
                ppcpp_core_valid=sum(bool(r['core_valid_before_deadline']) for r in group) if method=='PPCPP_CORE4' else None,
                overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in group),
                max_overrun=max(r['solver_seconds']-budget for r in group if r['solver_seconds'] is not None)))
    paired=[];case_ids=protocol['cases']
    for budget in (1,5,20):
        for a,b in itertools.combinations(METHODS,2):
            deltas=[];ratios=[];a_only=b_only=both_fail=0;per_case=[]
            for sid in case_ids:
                cd=[];cr=[]
                for rep in (0,1):
                    x=lookup[sid,rep,budget,a];y=lookup[sid,rep,budget,b]
                    if x['valid'] and y['valid']:
                        lx=x['metrics']['steps'];ly=y['metrics']['steps'];delta=lx-ly
                        deltas.append(delta);cd.append(delta)
                        if ly:cr.append(lx/ly-1);ratios.append(lx/ly-1)
                    elif x['valid']:a_only+=1
                    elif y['valid']:b_only+=1
                    else:both_fail+=1
                if cd:per_case.append(dict(case=sid,mean_step_difference=statistics.mean(cd),
                    mean_relative_difference=statistics.mean(cr) if cr else None))
            paired.append(dict(budget=budget,a=a,b=b,paired_success=len(deltas),a_only_success=a_only,b_only_success=b_only,both_fail=both_fail,
                a_shorter=sum(d<0 for d in deltas),equal=sum(d==0 for d in deltas),a_longer=sum(d>0 for d in deltas),
                step_difference_sum=sum(deltas),relative_difference_map_equal=statistics.mean(
                    [c['mean_relative_difference'] for c in per_case if c['mean_relative_difference'] is not None]) if ratios else None,
                per_case=per_case))
    summary=dict(status='verified_four_method_development',runs=288,selected_route_audits=len(checks),
        ppcpp_core_audits=core_checks,hashes_verified=True,solver_called=False,holdout_used=False,
        caveat='12 development maps already used to tune PPCPP; two repeats are not new independent maps',verifier_sha256=sha(Path(__file__)))
    write(OUT/'summary.json',summary);write(OUT/'method_budget_summary.json',summaries)
    write(OUT/'paired_comparisons.json',paired);write(OUT/'per_run_audits.json',checks)
    print(json.dumps(summary,ensure_ascii=False));print(json.dumps(summaries,ensure_ascii=False))

if __name__=='__main__':main()
