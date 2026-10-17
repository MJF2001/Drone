"""Independent saved-output audit of development preflight; never calls solve."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import hashlib
import importlib.util
import json

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_preflights/v1_20261014'
OUT=ALGO/'development_preflights/v1_20261014_verification'


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes=json.loads((SOURCE/'sha256.json').read_text(encoding='utf-8'))
    assert all(sha(SOURCE/name)==value for name,value in hashes.items())
    protocol=json.loads((SOURCE/'protocol.json').read_text(encoding='utf-8'))
    assert all(sha(Path(name))==value for name,value in protocol['inputs_and_frozen_sha256'].items())
    spec=importlib.util.spec_from_file_location('_frozen_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    rows=[json.loads(x) for x in (SOURCE/'execution_ledger.jsonl').open(encoding='utf-8')]
    assert len(rows)==protocol['expected_runs']==72
    checks=[];oarp_no_tour=[]
    for row in rows:
        s=json.loads((SOURCE/'cases'/(row['case']+'.json')).read_text(encoding='utf-8'))
        assert s['metadata']['split']=='development'
        payload=json.loads((SOURCE/'runs'/(row['run_id']+'.json')).read_text(encoding='utf-8'))
        assert payload['worker_status']=='returned' and not row['watchdog_timeout']
        raw=payload['raw'];route=tuple(map(tuple,raw['route']))
        pts=lambda key:frozenset(map(tuple,s[key]))
        snapshot=SimpleNamespace(free=pts('free'),targets=pts('targets'),covered=pts('covered'),
            current=tuple(s['current']),base=tuple(s['base']),radius=s['radius'],distance_budget=s['distance_budget'])
        check=auditor.audit(snapshot,route)
        assert check==raw['independent_audit'] and check['valid']
        assert raw['method']==row['method'] and raw['budget']==row['budget']
        assert raw['seed']==s['metadata']['repeat_seed_0']
        assert raw['seconds']<=payload['solve_plus_external_audit_seconds']+.000001
        m=payload['metrics'];assert check['length']==m['steps']==row['route_steps']
        assert m['fresh']+m['historical_repeat']+m['current_repeat']+m['non_target']==m['steps']
        counts=[0,0,0,0];seen=set(snapshot.covered)|({route[0]}&snapshot.targets)
        for cell in route[1:]:
            category=(3 if cell not in snapshot.targets else 1 if cell in snapshot.covered else 2 if cell in seen else 0)
            counts[category]+=1;seen.add(cell)
        assert counts==[m[k] for k in ('fresh','historical_repeat','current_repeat','non_target')]
        denominator=sum(counts[:3]);overlap=(counts[1]+counts[2])/denominator if denominator else None
        assert overlap==m['overlap_ratio']
        checks.append(dict(run_id=row['run_id'],valid=True,steps=check['length']))
        if row['method']=='OARP_CORE2' and not row['core_tour_obtained']:
            detail=raw['detail'];rank=detail.get('rank',{})
            oarp_no_tour.append(dict(run_id=row['run_id'],case=row['case'],budget=row['budget'],
                rank_cap=detail.get('rank_cap'),old_rank_count=detail.get('old_rank_count'),
                rank_status=rank.get('status'),attempts=rank.get('attempts'),
                fractional_lp=rank.get('fractional_lp'),used_integer_fallback=rank.get('used_integer_fallback'),
                route_valid=check['valid'],source=raw['source']))
    maximum=max(rows,key=lambda r:r['solver_seconds']-r['budget'])
    summary=dict(status='independently_verified_development_preflight',runs=72,valid=72,
        cases=len({r['case'] for r in rows}),max_overrun_seconds=maximum['solver_seconds']-maximum['budget'],
        max_overrun_run_id=maximum['run_id'],overrun_gt_10ms=sum(r['overrun_gt_10ms'] for r in rows),
        oarp_core_tour_missing=len(oarp_no_tour),hashes_verified=True,holdout_used=False,solver_called=False,
        verifier_sha256=sha(Path(__file__)))
    for name,data in [('summary.json',summary),('per_run_audit.json',checks),('oarp_core_missing.json',oarp_no_tour)]:
        with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
