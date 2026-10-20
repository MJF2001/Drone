"""Predeclared 16x12 development weight check; no holdout or baseline reruns."""
from pathlib import Path
from fractions import Fraction
import contextlib
import hashlib
import io
import itertools
import json
import os
import subprocess
import sys
import time
import traceback
import unittest

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
FROZEN=ALGO/'frozen_baselines/v2_20261012'
PRE=ALGO/'development_preflights/v1_20261014'
SPEC=ALGO/'candidate_specs/PPCPP_CORE4_v0.1_20261014.json'
OUT=ALGO/'development_preflights/ppcpp_weight_grid_v0.1_20261014'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,data):
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def snapshot(data):
    from model import Snapshot
    pts=lambda key:frozenset(map(tuple,data[key]))
    return Snapshot(data['name'],pts('free'),pts('targets'),pts('covered'),tuple(data['current']),
        tuple(data['base']),tuple(map(tuple,data['old_route'])),data['radius'],data['distance_budget'])


def worker(case_file,ws,wb,destination):
    try:
        import candidate_ppcpp_core4_20261014 as candidate
        data=json.loads(case_file.read_text(encoding='utf-8'))
        s=snapshot(data);initial=set(map(tuple,data['metadata']['initial_targets']))
        begin=time.perf_counter()
        result=candidate.solve(s,initial,20,data['metadata']['repeat_seed_0'],(ws,wb))
        write(destination,dict(status='returned',case=s.name,weights=[ws,wb],
            solve_plus_audits_seconds=time.perf_counter()-begin,raw=result))
        return 0
    except BaseException:
        write(destination,dict(status='exception',traceback=traceback.format_exc()))
        return 1


def common_reference(data):
    # Separate construction, sharing only the fixed geometry and independent
    # auditor with the candidate. This is not a new planner nor an optimum.
    from unified_geometry import UnifiedGeometry
    from audit import audit
    s=snapshot(data);g=UnifiedGeometry(s);accepted=[]
    old_check=audit(s,s.old_route)
    if old_check['valid']:accepted.append((len(s.old_route)-1,'old_suffix',s.old_route))
    pending=set(s.targets)-set(s.covered);visits=[]
    for cell in s.old_route:
        if cell in pending and cell in s.free:visits.append(cell);pending.remove(cell)
    visits+=sorted(pending,key=lambda cell:(cell[1],cell[0] if cell[1]%2==0 else -cell[0]))
    expanded=g.expand(visits);checked=audit(s,expanded)
    assert checked['valid'];accepted.append((len(expanded)-1,'common_fallback',expanded))
    best=min(enumerate(accepted),key=lambda item:(item[1][0],item[0]))[1]
    assert best[0]>0
    return dict(case=s.name,steps=best[0],source=best[1],route=best[2],audit=audit(s,best[2]))


def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    import candidate_ppcpp_core4_20261014
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    grid=list(itertools.product(spec['development_weight_grid']['omega_s'],spec['development_weight_grid']['omega_b']))
    pre_protocol=json.loads((PRE/'protocol.json').read_text(encoding='utf-8'))
    cases=[PRE/'cases'/(sid+'.json') for sid in pre_protocol['case_ids']]
    assert len(grid)==16 and len(cases)==12
    payloads=[json.loads(p.read_text(encoding='utf-8')) for p in cases]
    assert all(s['metadata']['split']=='development' for s in payloads)
    protected={p:sha(p) for p in cases+[SPEC,ALGO/'candidate_ppcpp_core4_20261014.py',
        ALGO/'test_candidate_ppcpp_core4_20261014.py',Path(__file__)]}
    manifest=json.loads((FROZEN/'manifest.json').read_text(encoding='utf-8'))
    protected.update({FROZEN/'source'/k:v for k,v in manifest['source_sha256'].items()})
    protected[FROZEN/'runtime_profile.json']=manifest['runtime_profile_sha256']
    assert all(sha(p)==value for p,value in protected.items())
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'runs').mkdir()
    # Persist the protocol before any tuning execution or weight-dependent run.
    protocol=dict(version='ppcpp_weight_grid_v0.1_20261014',purpose='development parameter selection only',
        weights=grid,case_ids=pre_protocol['case_ids'],budget_seconds=20,expected_runs=192,
        eligibility='all 12 core routes legal and validated before deadline; fallback success is insufficient',
        objective='exact rational mean(core_steps / independent common_reference_steps), map equal weight',
        tie_rule='omega_s+omega_b, then omega_s, then omega_b',
        watchdog_seconds=50,holdout_used=False,comparison_to_other_methods=False,
        thread_environment={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
        hashes={str(p):value for p,value in protected.items()})
    write(OUT/'protocol.json',protocol)
    suite=unittest.defaultTestLoader.loadTestsFromName('test_candidate_ppcpp_core4_20261014')
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        tested=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    with (OUT/'unit_tests.log').open('x',encoding='utf-8') as f:f.write(stream.getvalue())
    assert tested.wasSuccessful()
    references=[common_reference(s) for s in payloads];write(OUT/'common_references.json',references)
    rows=[];begin=time.perf_counter();env=dict(os.environ,**protocol['thread_environment'])
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
            for case_index,case_file in enumerate(cases):
                # Rotate pair order to avoid always measuring the same weights first.
                order=list(range(case_index%16,16))+list(range(case_index%16))
                for pair_index in order:
                    ws,wb=grid[pair_index];run_id=f'c{case_index:02d}_w{pair_index:02d}'
                    destination=OUT/'runs'/(run_id+'.json');log_file=OUT/'runs'/(run_id+'.log')
                    command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',
                             str(case_file),str(ws),str(wb),str(destination)]
                    start=time.perf_counter();timeout=False
                    with log_file.open('x',encoding='utf-8') as log:
                        try:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=env,timeout=50).returncode
                        except subprocess.TimeoutExpired:timeout=True;code=None
                    raw_file=json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else {}
                    raw=raw_file.get('raw',{});detail=raw.get('detail',{})
                    core_check=raw.get('core_independent_audit') or {}
                    selected_check=raw.get('independent_audit') or {}
                    core_attempt=next((r for r in detail.get('candidate_attempts',[]) if r['source']=='PPCPP_core4'),None)
                    core_valid=bool(detail.get('core_valid_before_deadline') and core_check.get('valid') and
                                    core_attempt and core_attempt['seconds']<=20 and not timeout)
                    row=dict(run_id=run_id,case=payloads[case_index]['name'],case_index=case_index,
                        pair_index=pair_index,weights=[ws,wb],returncode=code,watchdog_timeout=timeout,
                        worker_status=raw_file.get('status','no_file'),process_wall_seconds=time.perf_counter()-start,
                        solver_seconds=raw.get('seconds'),status=raw.get('status'),core_valid=core_valid,
                        selected_valid=bool(selected_check.get('valid')) and not timeout,
                        core_steps=detail.get('core_steps') if core_valid else None,
                        selected_steps=selected_check.get('length'),reference_steps=references[case_index]['steps'],
                        source=raw.get('source'),overrun_gt_10ms=raw.get('overrun_gt_10ms'),
                        recovery_count=detail.get('recovery_count'))
                    rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
                print(json.dumps(dict(case=payloads[case_index]['name'],runs=len(rows),core_valid=sum(r['core_valid'] for r in rows)),ensure_ascii=False),flush=True)
        assert len(rows)==192
        scores=[]
        for pair_index,weights in enumerate(grid):
            group=[r for r in rows if r['pair_index']==pair_index]
            assert len(group)==12
            eligible=all(r['core_valid'] for r in group)
            ratio=sum((Fraction(r['core_steps'],r['reference_steps']) for r in group),Fraction())/12 if eligible else None
            scores.append(dict(pair_index=pair_index,weights=weights,eligible=eligible,
                core_valid=sum(r['core_valid'] for r in group),mean_ratio=float(ratio) if ratio is not None else None,
                ratio_fraction=str(ratio) if ratio is not None else None))
        eligible=[r for r in scores if r['eligible']]
        winner=min(eligible,key=lambda r:(Fraction(r['ratio_fraction']),sum(r['weights']),*r['weights'])) if eligible else None
        assert all(sha(p)==value for p,value in protected.items())
        summary=dict(status='finished_development_tuning_not_test_benchmark',runs=192,
            unit_tests=tested.testsRun,core_valid=sum(r['core_valid'] for r in rows),
            selected_valid=sum(r['selected_valid'] for r in rows),eligible_pairs=len(eligible),
            worker_exceptions=sum(r['worker_status']=='exception' for r in rows),
            watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),
            overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),
            wall_seconds=time.perf_counter()-begin,selected_pair=winner,hashes_unchanged=True,holdout_used=False)
        write(OUT/'weight_scores.json',scores);write(OUT/'completion.json',summary)
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(summary,ensure_ascii=False))
    except BaseException:
        write(OUT/'aborted.json',dict(status='aborted',runs=len(rows),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        sys.exit(worker(Path(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),Path(sys.argv[5])))
    main()
