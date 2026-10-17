"""Small development-only subprocess preflight, not a ranking benchmark.

12 predeclared H/p50 states; all six events, all scales/geometries; two soft
budgets; one seed; fresh process per run; preserve every failed/timeout attempt.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import itertools
import json
import os
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
FROZEN=ALGO/'frozen_baselines/v2_20261012'
INPUT=ALGO/'scale_inputs/development_v0.1_20261014'
OUT=ALGO/'development_preflights/v1_20261014'
METHODS=('P2_MULTI','OARP_CORE2','TREE_MST')
EVENTS=('no_change','straight','corner','obstacle','straight_obstacle','corner_obstacle')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(path,obj):
    with path.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)


def metrics(route,targets,covered):
    seen=set(covered)|({route[0]}&targets)
    counts=dict(fresh=0,historical_repeat=0,current_repeat=0,non_target=0)
    for p in route[1:]:
        key=('non_target' if p not in targets else 'historical_repeat' if p in covered
             else 'current_repeat' if p in seen else 'fresh')
        counts[key]+=1;seen.add(p)
    denominator=len(route)-1-counts['non_target']
    counts['overlap_ratio']=(counts['historical_repeat']+counts['current_repeat'])/denominator if denominator else None
    counts['steps']=len(route)-1
    return counts


def worker(case_path,method,budget,result_path):
    try:
        import portable_frozen
        import baseline_suite
        from model import Snapshot
        assert Path(baseline_suite.__file__).resolve()==FROZEN/'source/baseline_suite.py'
        s=json.loads(case_path.read_text(encoding='utf-8'))
        points=lambda key:frozenset(map(tuple,s[key]))
        snapshot=Snapshot(s['name'],points('free'),points('targets'),points('covered'),
            tuple(s['current']),tuple(s['base']),tuple(map(tuple,s['old_route'])),
            s['radius'],s['distance_budget'])
        initial=set(map(tuple,s['metadata']['initial_targets']))
        seed=s['metadata']['repeat_seed_0']
        begin=time.perf_counter()
        raw=portable_frozen.solve(snapshot,initial,method,budget,seed,portable_frozen.PROFILE)
        outer=time.perf_counter()-begin
        record=dict(worker_status='returned',case=s['name'],method=method,budget=budget,seed=seed,
            implementation_file=baseline_suite.__file__,solve_plus_external_audit_seconds=outer,
            raw=raw,metrics=metrics(raw['route'],snapshot.targets,snapshot.covered) if raw['route'] else None)
        write(result_path,record)
        return 0
    except BaseException:
        write(result_path,dict(worker_status='exception',case_path=str(case_path),method=method,
            budget=budget,traceback=traceback.format_exc()))
        return 1


def main():
    validation=json.loads((ROOT/'运行环境/验证记录_20261014/03_runtime_verification.json').read_text(encoding='utf-8'))
    assert validation['status']=='verified_this_machine_runtime_and_regression'
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    frozen_manifest=json.loads((FROZEN/'manifest.json').read_text(encoding='utf-8'))
    expected={FROZEN/'source'/name:value for name,value in frozen_manifest['source_sha256'].items()}
    expected[FROZEN/'runtime_profile.json']=frozen_manifest['runtime_profile_sha256']
    input_manifest=json.loads((INPUT/'sha256.json').read_text(encoding='utf-8'))
    expected.update({INPUT/name:value for name,value in input_manifest['artifacts'].items()})
    assert all(sha(p)==value for p,value in expected.items())
    selected={}
    for line in (INPUT/'snapshots.jsonl').open(encoding='utf-8'):
        s=json.loads(line);m=s['metadata'];scale_index=('small','medium','large').index(m['scale'])
        event=EVENTS[(scale_index*4+m['stratum']-1)%6]
        if m['history']=='H' and m['progress_percent']==50 and m['event']==event:
            assert m['split']=='development'
            selected[scale_index,m['stratum']]=s
    assert len(selected)==12
    OUT.mkdir(parents=True,exist_ok=False)
    cases=OUT/'cases';cases.mkdir();records=OUT/'runs';records.mkdir()
    ordered=[selected[key] for key in sorted(selected)]
    for s in ordered:write(cases/(s['name']+'.json'),s)
    protocol=dict(version='development_preflight_v1_20261014',purpose='loader, scaling, recording and legal-output diagnosis; not ranking',
        baseline_version='v2_20261012',case_ids=[s['name'] for s in ordered],
        selection='H/p50; event=(scale_index*4+stratum-1)%6; one state per development base map',
        budgets=[1,5],repeats=1,expected_runs=72,profile='unchanged historical frozen profile, maximum cap32',
        per_run_process='fresh; imports/JSON before solve; final independent audit excluded from solver seconds',
        watchdog='budget+30 seconds wall; not a solver budget; timeout counted as no returned output',
        thread_environment={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
        thread_caveat='Environment limits are requests, not verified control of every native library.',
        holdout_used=False,ranking_report=False,driver_sha256=sha(Path(__file__)),
        inputs_and_frozen_sha256={str(p):value for p,value in expected.items()})
    write(OUT/'protocol.json',protocol)
    env=dict(os.environ,**protocol['thread_environment'])
    rows=[];begin=time.perf_counter();permutations=list(itertools.permutations(METHODS))
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
            for index,s in enumerate(ordered):
                budgets=(1,5) if index%2==0 else (5,1)
                for budget in budgets:
                    for method in permutations[index%6]:
                        run_id=f'{index:02d}_{method}_b{budget}'
                        destination=records/(run_id+'.json');log_path=records/(run_id+'.log')
                        command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',
                            str(cases/(s['name']+'.json')),method,str(budget),str(destination)]
                        start=time.perf_counter();timeout=False
                        with log_path.open('x',encoding='utf-8') as log:
                            try:
                                process=subprocess.run(command,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                                       timeout=budget+30)
                                code=process.returncode
                            except subprocess.TimeoutExpired:
                                timeout=True;code=None
                        wall=time.perf_counter()-start
                        payload=json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else None
                        raw=payload.get('raw',{}) if payload else {}
                        audit=raw.get('independent_audit') or {}
                        row=dict(run_id=run_id,case=s['name'],method=method,budget=budget,
                            worker_returncode=code,watchdog_timeout=timeout,process_wall_seconds=wall,
                            worker_status=payload.get('worker_status') if payload else 'no_result_file',
                            solver_status=raw.get('status'),valid_returned_route=bool(audit.get('valid')),
                            solver_seconds=raw.get('seconds'),source=raw.get('source'),
                            fallback_selected=raw.get('fallback_selected'),overrun_gt_10ms=raw.get('overrun_gt_10ms'),
                            rank_cap=raw.get('detail',{}).get('rank_cap'),
                            core_tour_obtained='tour' in raw.get('detail',{}),
                            route_steps=payload['metrics']['steps'] if payload and payload.get('metrics') else None)
                        if timeout:row['valid_returned_route']=False
                        rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
                print(json.dumps(dict(case=s['name'],completed_runs=len(rows),valid=sum(r['valid_returned_route'] for r in rows)),ensure_ascii=False),flush=True)
        assert len(rows)==72
        assert all(sha(p)==value for p,value in expected.items()),'input/frozen hashes changed'
        summary=dict(status='finished_development_preflight_not_formal_benchmark',runs=len(rows),
            valid_returned_routes=sum(r['valid_returned_route'] for r in rows),
            no_legal_output=sum(not r['valid_returned_route'] for r in rows),
            watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),
            worker_exceptions=sum(r['worker_status']=='exception' for r in rows),
            overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),
            wall_seconds=time.perf_counter()-begin,hashes_unchanged=True,holdout_used=False)
        summary['by_budget_method']=[dict(budget=b,method=m,runs=len(group),
            valid=sum(r['valid_returned_route'] for r in group),
            fallback_selected=sum(bool(r['fallback_selected']) for r in group),
            core_tours=sum(r['core_tour_obtained'] for r in group),
            overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in group))
            for b in (1,5) for m in METHODS
            for group in [[r for r in rows if r['budget']==b and r['method']==m]]]
        write(OUT/'completion.json',summary)
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(summary,ensure_ascii=False))
    except BaseException:
        write(OUT/'aborted.json',dict(status='aborted',runs_written=len(rows),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),Path(sys.argv[5])))
    main()
