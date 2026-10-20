"""Four-method paired development check, 12 states x 3 budgets x 2 x 4.
Never reads holdout; PPCPP was tuned on these states: no generalization claim.
"""
from pathlib import Path
import hashlib,importlib.util,itertools,json,os,subprocess,sys,time,traceback
from scale_baseline_preflight_20261014 import metrics

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
BASE=ALGO/'frozen_baselines/v2_20261012'
CANDIDATE=ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014'
PRE=ALGO/'development_preflights/v1_20261014'
OUT=ALGO/'development_preflights/four_method_paired_v1_20261015'
METHODS=('P2_MULTI','OARP_CORE2','TREE_MST','PPCPP_CORE4')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)

def worker(case_file,method,budget,repeat,destination):
    try:
        import portable_frozen,baseline_suite
        from model import Snapshot
        loader=None
        if method=='PPCPP_CORE4':
            spec=importlib.util.spec_from_file_location('_candidate_loader',CANDIDATE/'load_candidate.py')
            loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
        assert Path(baseline_suite.__file__).resolve()==BASE/'source/baseline_suite.py'
        data=json.loads(case_file.read_text(encoding='utf-8'));pts=lambda k:frozenset(map(tuple,data[k]))
        s=Snapshot(data['name'],pts('free'),pts('targets'),pts('covered'),tuple(data['current']),
            tuple(data['base']),tuple(map(tuple,data['old_route'])),data['radius'],data['distance_budget'])
        initial=set(map(tuple,data['metadata']['initial_targets']));seed=data['metadata'][f'repeat_seed_{repeat}']
        begin=time.perf_counter()
        raw=(loader.solve(s,initial,budget,seed) if loader else
             portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE))
        outer=time.perf_counter()-begin
        # Additional diagnostics occur after solver timing and independent audit.
        m=metrics(raw['route'],s.targets,s.covered) if raw['route'] else None
        if m:
            route=raw['route'];vectors=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
            m['turns90']=sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vectors,vectors[1:]))
            m['turns180']=sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vectors,vectors[1:]))
            left=set(s.targets-s.covered);left.discard(route[0]);completion=0 if not left else None
            for i,p in enumerate(route[1:],1):
                left.discard(p)
                if not left and completion is None:completion=i
            m['completion_step']=completion;m['return_tail_steps']=len(route)-1-completion if completion is not None else None
        write(destination,dict(worker_status='returned',case=s.name,method=method,budget=budget,
            repeat=repeat,seed=seed,implementation_file=loader.IMPLEMENTATION.__file__ if loader else baseline_suite.__file__,
            solve_plus_audits_seconds=outer,raw=raw,metrics=m))
        return 0
    except BaseException:
        write(destination,dict(worker_status='exception',traceback=traceback.format_exc()))
        return 1

def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    pp=json.loads((PRE/'protocol.json').read_text(encoding='utf-8'))
    cases=[PRE/'cases'/(sid+'.json') for sid in pp['case_ids']]
    protected={p:sha(p) for p in cases+[Path(__file__),ROOT/'scale_baseline_preflight_20261014.py',ROOT/'portable_frozen.py']}
    bm=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    protected.update({BASE/'source'/n:h for n,h in bm['source_sha256'].items()})
    protected[BASE/'runtime_profile.json']=bm['runtime_profile_sha256']
    cm=json.loads((CANDIDATE/'manifest.json').read_text(encoding='utf-8'))
    protected.update({CANDIDATE/n:h for n,h in cm['files_sha256'].items()})
    assert all(sha(p)==h for p,h in protected.items())
    assert all(json.loads(p.read_text(encoding='utf-8'))['metadata']['split']=='development' for p in cases)
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'runs').mkdir()
    permutations=list(itertools.permutations(METHODS));jobs=[]
    for ci,case in enumerate(cases):
        for rep in (0,1):
            block=2*ci+rep
            budgets=(1,5,20);budgets=budgets[block%3:]+budgets[:block%3]
            for budget in budgets:
                for method in permutations[block]:
                    jobs.append(dict(run_id=f'c{ci:02d}_r{rep}_b{budget}_{method}',case=case.stem,
                                     case_file=str(case),method=method,budget=budget,repeat=rep))
    assert len(jobs)==288
    env_limits={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    protocol=dict(version='four_method_paired_development_v1_20261015',methods=METHODS,budgets=[1,5,20],repeats=2,
        cases=pp['case_ids'],jobs=jobs,expected_runs=288,holdout_used=False,
        limitation='Same H/p50 states used for PPCPP tuning; development diagnostic, not independent test ranking.',
        fairness='fresh process/cold geometry; same paired seed; all 24 method permutations across case-repeat blocks; rotated budgets',
        thread_environment=env_limits,thread_caveat='Requested environment limits, not proof all libraries are single-threaded',
        timing='reported solver seconds exclude final independent audits; separate external process wall; library load outside solve',
        watchdog='budget+30 seconds external wall; not a free solver allowance',
        hashes={str(p):h for p,h in protected.items()})
    write(OUT/'protocol.json',protocol);rows=[];begin=time.perf_counter();env=dict(os.environ,**env_limits)
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
            for job in jobs:
                destination=OUT/'runs'/(job['run_id']+'.json');logfile=OUT/'runs'/(job['run_id']+'.log')
                command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',job['case_file'],
                         job['method'],str(job['budget']),str(job['repeat']),str(destination)]
                start=time.perf_counter();timeout=False
                with logfile.open('x',encoding='utf-8') as log:
                    try:code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=job['budget']+30).returncode
                    except subprocess.TimeoutExpired:timeout=True;code=None
                payload=json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else {}
                raw=payload.get('raw',{});check=raw.get('independent_audit') or {};detail=raw.get('detail',{})
                row=dict(job,returncode=code,watchdog_timeout=timeout,process_wall_seconds=time.perf_counter()-start,
                    worker_status=payload.get('worker_status','no_result'),valid=bool(check.get('valid')) and not timeout,
                    solver_status=raw.get('status'),solver_seconds=raw.get('seconds'),source=raw.get('source'),
                    fallback_selected=raw.get('fallback_selected'),overrun_gt_10ms=raw.get('overrun_gt_10ms'),
                    core_tour_obtained=('tour' in detail) if job['method']=='OARP_CORE2' else None,
                    core_valid_before_deadline=detail.get('core_valid_before_deadline') if job['method']=='PPCPP_CORE4' else None,
                    metrics=payload.get('metrics'))
                rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
                if len(rows)%24==0:print(json.dumps(dict(runs=len(rows),valid=sum(r['valid'] for r in rows)),ensure_ascii=False),flush=True)
        assert len(rows)==288 and all(sha(p)==h for p,h in protected.items())
        result=dict(status='finished_four_method_development_not_independent_test',runs=len(rows),valid=sum(r['valid'] for r in rows),
            watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),exceptions=sum(r['worker_status']=='exception' for r in rows),
            overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),wall_seconds=time.perf_counter()-begin,
            hashes_unchanged=True,holdout_used=False)
        write(OUT/'completion.json',result)
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(result,ensure_ascii=False))
    except BaseException:
        write(OUT/'aborted.json',dict(status='aborted',completed_runs=len(rows),traceback=traceback.format_exc()));raise

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),int(sys.argv[5]),Path(sys.argv[6])))
    main()
