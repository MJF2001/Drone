"""Bounded matched-history screening: four fixed methods, budgets 1/20, one seed."""
from pathlib import Path
import itertools,json,os,subprocess,sys,time,traceback
from compare_four_development_20261015 import ROOT,ALGO,BASE,CANDIDATE,METHODS,sha,write

INPUT=ALGO/'scale_inputs/matched_history_v2_20261015'
OUT=ALGO/'development_preflights/matched_history_v2_20261015'
WORKER=ROOT/'compare_four_development_20261015.py'

def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    assert read(INPUT/'independent_input_verification.json')['valid']
    complete=read(INPUT/'completion.json');cases=[INPUT/'cases'/(sid+'.json') for sid in complete['case_ids']]
    protected={p:sha(p) for p in [Path(__file__),WORKER,ROOT/'scale_baseline_preflight_20261014.py',
        ROOT/'portable_frozen.py',ROOT/'verify_matched_history_20261015.py']+list(INPUT.rglob('*.json'))}
    bm=read(BASE/'manifest.json');protected.update({BASE/'source'/n:h for n,h in bm['source_sha256'].items()})
    protected[BASE/'runtime_profile.json']=bm['runtime_profile_sha256']
    cm=read(CANDIDATE/'manifest.json');protected.update({CANDIDATE/n:h for n,h in cm['files_sha256'].items()})
    assert all(sha(p)==h for p,h in protected.items())
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'runs').mkdir();jobs=[]
    perms=list(itertools.permutations(METHODS))
    for ci,p in enumerate(cases):
        for bi,budget in enumerate((1,20) if ci%2==0 else (20,1)):
            for method in perms[(2*ci+bi)%24]:
                jobs.append(dict(run_id=f'c{ci:02d}_r0_b{budget}_{method}',case=p.stem,case_file=str(p),
                    method=method,budget=budget,repeat=0))
    env_limits={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    write(OUT/'protocol.json',dict(version='matched_history_development_v2_20261015',methods=METHODS,
        budgets=[1,20],repeats=1,cases=complete['case_ids'],jobs=jobs,expected_runs=len(jobs),
        attempted_input_states=48,infeasible_input_states=complete['infeasible'],holdout_used=False,
        limitation='Same 12 development maps, correlated states; H50 tuned anchors. One seed: not a timing stability estimate.',
        fairness='Fresh process; shared family seed and event geometry; method permutations cycle, budget order alternates.',
        thread_environment=env_limits,watchdog='budget+30s external wall; not additional solve time',
        hashes={str(p):h for p,h in protected.items()}))
    rows=[];start=time.perf_counter();env=dict(os.environ,**env_limits)
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
            for job in jobs:
                dest=OUT/'runs'/(job['run_id']+'.json');log=OUT/'runs'/(job['run_id']+'.log')
                begin=time.perf_counter();timeout=False
                with log.open('x',encoding='utf-8') as f:
                    try:
                        code=subprocess.run([sys.executable,'-X','utf8',str(WORKER),'--worker',job['case_file'],
                            job['method'],str(job['budget']),'0',str(dest)],cwd=ROOT,env=env,stdout=f,
                            stderr=subprocess.STDOUT,timeout=job['budget']+30).returncode
                    except subprocess.TimeoutExpired:timeout=True;code=None
                data=read(dest) if dest.exists() else {};raw=data.get('raw',{});detail=raw.get('detail',{})
                row=dict(job,returncode=code,watchdog_timeout=timeout,process_wall_seconds=time.perf_counter()-begin,
                    worker_status=data.get('worker_status','no_result'),valid=bool((raw.get('independent_audit') or {}).get('valid')) and not timeout,
                    solver_status=raw.get('status'),solver_seconds=raw.get('seconds'),source=raw.get('source'),
                    fallback_selected=raw.get('fallback_selected'),overrun_gt_10ms=raw.get('overrun_gt_10ms'),
                    core_tour_obtained=('tour' in detail) if job['method']=='OARP_CORE2' else None,
                    core_valid_before_deadline=detail.get('core_valid_before_deadline') if job['method']=='PPCPP_CORE4' else None,
                    metrics=data.get('metrics'))
                rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
                if len(rows)%32==0:print(json.dumps(dict(runs=len(rows),valid=sum(r['valid'] for r in rows))),flush=True)
        assert len(rows)==len(jobs) and all(sha(p)==h for p,h in protected.items())
        result=dict(status='finished_matched_development_not_independent_test',runs=len(rows),valid=sum(r['valid'] for r in rows),
            input_infeasible=complete['infeasible'],watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),
            exceptions=sum(r['worker_status']=='exception' for r in rows),overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),
            wall_seconds=time.perf_counter()-start,hashes_unchanged=True,holdout_used=False)
        write(OUT/'completion.json',result)
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(result,ensure_ascii=False))
    except BaseException:
        write(OUT/'aborted.json',dict(completed=len(rows),traceback=traceback.format_exc()));raise

if __name__=='__main__':main()
