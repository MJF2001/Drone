"""Audit saved grid outcomes and replay local decision logic independently.

No candidate solve is called here. No holdout data is read. The frozen audit
checks routes; a separate implementation checks rewards and recovery decisions.
"""
from pathlib import Path
from collections import deque
from fractions import Fraction
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import math

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_preflights/ppcpp_weight_grid_v0.1_20261014'
CASES=ALGO/'development_preflights/v1_20261014/cases'
OUT=ALGO/'development_preflights/ppcpp_weight_grid_v0.1_20261014_verification'


def neighbors(p):
    x,y=p
    return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))


def bfs_distances(free,start):
    seen={start:0};queue=deque([start])
    while queue:
        p=queue.popleft()
        for q in neighbors(p):
            if q in free and q not in seen:seen[q]=seen[p]+1;queue.append(q)
    return seen


def check_core_decisions(s,route,detail,weights):
    free=s.free;pending=set(s.targets-s.covered)-{s.current}
    if s.targets:
        xmin=min(p[0] for p in s.targets);xmax=max(p[0] for p in s.targets)
        predator=(xmin-1 if 2*s.base[0]<=xmin+xmax else xmax+1,s.base[1])
    else:predator=None
    assert predator==tuple(detail['predator']) if predator is not None else detail['predator'] is None
    recoveries={r['route_end_index']-r['steps']:r for r in detail['recoveries']}
    i=0;local=0;recovery_steps=0;recovery_count=0
    while pending:
        p=route[i];options=sorted(q for q in neighbors(p) if q in pending and q in free)
        if options:
            assert i not in recoveries
            ds={q:math.hypot(q[0]-predator[0],q[1]-predator[1]) for q in options}
            low=min(ds.values());high=max(ds.values());scores={}
            for q in options:
                distance=(ds[q]-low)/(high-low) if high!=low else 0.
                if i==0:straight=0.
                else:
                    prev=route[i-1]
                    dot=(p[0]-prev[0])*(q[0]-p[0])+(p[1]-prev[1])*(q[1]-p[1])
                    straight=(dot+1)/2
                boundary=(4-sum(z in pending and z in free for z in neighbors(q)))/4
                scores[q]=distance+weights[0]*straight+weights[1]*boundary
            goal=min(options,key=lambda q:(-scores[q],q))
            assert route[i+1]==goal,(i,'wrong_reward_choice')
            i+=1;pending.discard(goal);local+=1
        else:
            recovery=recoveries[i];ds=bfs_distances(free,p)
            goal=min(pending,key=lambda q:(ds[q],q))
            assert tuple(recovery['goal'])==goal and tuple(recovery['start'])==p
            end=i+recovery['steps'];segment=route[i:end+1]
            assert segment[-1]==goal and len(segment)-1==ds[goal]
            fresh=len(pending & set(segment[1:]));assert fresh==recovery['fresh']
            pending-=set(segment[1:]);recovery_steps+=len(segment)-1;recovery_count+=1;i=end
    tail=route[i:];assert tail[-1]==s.base
    assert len(tail)-1==bfs_distances(free,tail[0])[s.base]
    assert local==detail['local_moves'] and recovery_count==detail['recovery_count']
    assert recovery_steps==detail['recovery_moves'] and len(tail)-1==detail['return_moves']
    assert local+recovery_steps+len(tail)-1==len(route)-1


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes=json.loads((SOURCE/'sha256.json').read_text(encoding='utf-8'))
    assert all(sha(SOURCE/name)==value for name,value in hashes.items())
    protocol=json.loads((SOURCE/'protocol.json').read_text(encoding='utf-8'))
    assert all(sha(Path(name))==value for name,value in protocol['hashes'].items())
    spec=importlib.util.spec_from_file_location('_grid_independent_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)
    rows=[json.loads(x) for x in (SOURCE/'execution_ledger.jsonl').open(encoding='utf-8')]
    references={r['case']:r for r in json.loads((SOURCE/'common_references.json').read_text(encoding='utf-8'))}
    assert len(rows)==192 and len({r['run_id'] for r in rows})==192
    checked=[];reference_checked=set();core_checked=selected_checked=decisions_checked=0
    for row in rows:
        data=json.loads((CASES/(row['case']+'.json')).read_text(encoding='utf-8'))
        assert data['metadata']['split']=='development'
        pts=lambda name:frozenset(map(tuple,data[name]))
        s=SimpleNamespace(free=pts('free'),targets=pts('targets'),covered=pts('covered'),current=tuple(data['current']),
            base=tuple(data['base']),radius=data['radius'],distance_budget=data['distance_budget'])
        if row['case'] not in reference_checked:
            reference=references[row['case']];ref_route=tuple(map(tuple,reference['route']))
            ref_audit=audit_module.audit(s,ref_route)
            assert ref_audit==reference['audit'] and ref_audit['valid']
            assert ref_audit['length']==reference['steps']
            reference_checked.add(row['case'])
        raw_path=SOURCE/'runs'/(row['run_id']+'.json')
        if not raw_path.exists():
            assert not row['core_valid'];continue
        payload=json.loads(raw_path.read_text(encoding='utf-8'))
        if payload['status']!='returned':
            assert not row['core_valid'];continue
        raw=payload['raw'];detail=raw['detail']
        assert raw['budget']==20 and detail['weights']==row['weights']
        assert raw['seed']==data['metadata']['repeat_seed_0']
        if raw['route']:
            selected_audit=audit_module.audit(s,tuple(map(tuple,raw['route'])))
            assert selected_audit==raw['independent_audit'] and selected_audit['valid'];selected_checked+=1
        if detail['core_route']:
            route=tuple(map(tuple,detail['core_route']));core_audit=audit_module.audit(s,route)
            assert core_audit==raw['core_independent_audit'];core_checked+=1
            if row['core_valid']:
                assert core_audit['valid'] and core_audit['length']==row['core_steps']
                check_core_decisions(s,route,detail,row['weights']);decisions_checked+=1
        assert row['reference_steps']==references[row['case']]['steps']
        checked.append(dict(run_id=row['run_id'],core_valid=row['core_valid'],selected_valid=row['selected_valid']))
    scores=[]
    for index,weights in enumerate(protocol['weights']):
        group=[r for r in rows if r['pair_index']==index];assert len(group)==12
        ratio=sum((Fraction(r['core_steps'],r['reference_steps']) for r in group),Fraction())/12 if all(r['core_valid'] for r in group) else None
        scores.append(dict(pair_index=index,weights=weights,eligible=ratio is not None,
            core_valid=sum(r['core_valid'] for r in group),mean_ratio=float(ratio) if ratio is not None else None,
            ratio_fraction=str(ratio) if ratio is not None else None))
    assert scores==json.loads((SOURCE/'weight_scores.json').read_text(encoding='utf-8'))
    eligible=[s for s in scores if s['eligible']]
    winner=min(eligible,key=lambda s:(Fraction(s['ratio_fraction']),sum(s['weights']),*s['weights'])) if eligible else None
    completion=json.loads((SOURCE/'completion.json').read_text(encoding='utf-8'))
    assert winner==completion['selected_pair']
    summary=dict(status='verified_development_grid_and_core_decisions',runs=len(rows),
        selected_route_audits=selected_checked,core_route_audits=core_checked,decision_replays=decisions_checked,
        common_reference_audits=len(reference_checked),selected_pair=winner,
        solver_called=False,holdout_used=False,hashes_verified=True,verifier_sha256=sha(Path(__file__)))
    for name,obj in [('summary.json',summary),('per_run_checks.json',checked)]:
        with (OUT/name).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
