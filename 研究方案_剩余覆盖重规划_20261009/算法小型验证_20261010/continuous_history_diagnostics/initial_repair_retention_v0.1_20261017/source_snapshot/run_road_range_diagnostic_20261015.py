"""Fixed development diagnostic, five logical methods, 22 states, budgets 1/20."""
from pathlib import Path
import hashlib,itertools,json,os,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
INPUT=ALGO/'range_diagnostics/inputs_v0.1_20261015'
OUT=ALGO/'range_diagnostics/run_v0.1_20261015'
METHODS=('R_SEED','R_PLUS1','R_PLUS2','R_ALL','P2_MULTI')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def worker(case,method,budget,dest):
    try:
        import portable_frozen
        from prepare_road_range_diagnostic_20261015 import snapshot
        from road_range_candidate_20261015 import solve
        from scale_baseline_preflight_20261014 import metrics
        c=read(case);s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']));seed=c['metadata']['range_diagnostic']['paired_seed']
        start=time.perf_counter()
        raw=portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE) if method=='P2_MULTI' else solve(s,initial,method,budget,seed)
        outer=time.perf_counter()-start
        m=metrics(raw['route'],s.targets,s.covered) if raw['route'] else None
        if m:
            route=raw['route'];vec=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(route,route[1:])]
            m['turns90']=sum(a[0]*b[0]+a[1]*b[1]==0 for a,b in zip(vec,vec[1:]))
            m['turns180']=sum(a[0]*b[0]+a[1]*b[1]==-1 for a,b in zip(vec,vec[1:]))
            left=set(s.targets-s.covered)-{route[0]};completed=0 if not left else None
            for i,p in enumerate(route[1:],1):
                left.discard(p)
                if not left and completed is None:completed=i
            m['completion_step']=completed;m['return_tail_steps']=len(route)-1-completed if completed is not None else None
        write(dest,dict(worker_status='returned',case=s.name,method=method,budget=budget,seed=seed,
            raw=raw,metrics=m,solve_plus_audits_seconds=outer));return 0
    except BaseException:
        write(dest,dict(worker_status='exception',traceback=traceback.format_exc()));return 1

def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    assert read(INPUT/'independent_input_check.json')['valid']
    complete=read(INPUT/'completion.json');references=read(INPUT/'structural_references.json')
    protect={p:sha(p) for p in list(INPUT.rglob('*.json'))+[ROOT/n for n in (
        'portable_frozen.py','road_range_candidate_20261015.py','range_p2_engine_20261015.py',
        'prepare_road_range_diagnostic_20261015.py','run_road_range_diagnostic_20261015.py',
        'verify_road_range_diagnostic_20261015.py','test_road_range_diagnostic_20261015.py','scale_baseline_preflight_20261014.py')]}
    design_doc=ROOT/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/57_道路重排范围有界诊断协议_20261015.md'
    protect[design_doc]=sha(design_doc)
    base=ALGO/'frozen_baselines/v2_20261012';bm=read(base/'manifest.json')
    protect.update({base/'source'/n:h for n,h in bm['source_sha256'].items()});protect[base/'runtime_profile.json']=bm['runtime_profile_sha256']
    candidate=ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014'
    protect.update({candidate/n:h for n,h in read(candidate/'manifest.json')['files_sha256'].items()})
    assert all(sha(p)==h for p,h in protect.items())
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'runs').mkdir();jobs=[];logical=[]
    for ci,sid in enumerate(complete['case_ids']):
        aliases=dict(references[sid]['aliases'],P2_MULTI='P2_MULTI')
        order=METHODS[ci%5:]+METHODS[:ci%5]
        if ci%2:order=tuple(reversed(order))
        for budget in ((1,20) if ci%2==0 else (20,1)):
            for m in order:
                if aliases[m]!=m:continue
                jobs.append(dict(run_id=f'c{ci:02d}_b{budget}_{m}',case=sid,case_file=str(INPUT/'cases'/(sid+'.json')),method=m,budget=budget))
            for m in METHODS:logical.append(dict(case=sid,method=m,budget=budget,canonical_method=aliases[m],run_id=f'c{ci:02d}_b{budget}_{aliases[m]}'))
    assert len(logical)==220
    limits={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    write(OUT/'protocol.json',dict(version='road_range_development_v0.1_20261015',methods=METHODS,budgets=[1,20],repeats=1,
        cases=complete['case_ids'],jobs=jobs,logical_settings=logical,expected_physical_runs=len(jobs),logical_settings_count=220,
        aliases='Only identical precomputed left/right cuts, same state/seed/budget. Reuse one saved execution, no best-of-runs choice.',
        paired_seed='Anchor seed shared with same-history no-change control; source seed preserved in provenance.',
        input_reference='Untimed structural references never passed to solve; every range worker recomputes all plans inside solve.',
        core='Frozen P2 multi search order, only optional full-route acceptance callback added in separate source copy.',
        timing='All range geometry/fallback/planning/search/splicing/candidate audits charged; final independent audits outside; no probe/solver time reset.',
        order='Predeclared cyclic/reversed method order and alternating budgets; not a claim of perfectly balanced permutations.',
        thread_environment=limits,watchdog='budget+30s external wall; not extra solver allowance',holdout_used=False,
        objective='Same-budget actual complete-route quality; times separate; no fitted scope thresholds or online oracle.',
        analysis=dict(relative_direction='range_steps/P2_steps - 1',cluster='repeat then state within base map then 12 base maps equally',
            subsets=['all','event','control'],tolerance_steps=0,secondary_within_2percent_descriptive=True,
            failures='Report all attempted/logical settings and unilateral failures; paired lengths only if both valid.',
            oracle='Posthoc minimum over fixed scopes is diagnostic only, not online selector performance.',
            stop='No additional tuning or repeats after results. Poor gains/ALL-wrapper weakness or fallback-dominated results require explanation, not cherry-picking.'),
        protected_hashes={str(p):h for p,h in protect.items()}))
    rows=[];begin=time.perf_counter();env=dict(os.environ,**limits)
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as f:
            for j in jobs:
                dest=OUT/'runs'/(j['run_id']+'.json');log=OUT/'runs'/(j['run_id']+'.log');start=time.perf_counter();timeout=False
                with log.open('x',encoding='utf-8') as output:
                    try:code=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',j['case_file'],j['method'],str(j['budget']),str(dest)],
                        cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
                    except subprocess.TimeoutExpired:timeout=True;code=None
                payload=read(dest) if dest.exists() else {};raw=payload.get('raw',{})
                row=dict(j,returncode=code,watchdog_timeout=timeout,process_wall_seconds=time.perf_counter()-start,
                    worker_status=payload.get('worker_status','no_result'),valid=bool((raw.get('independent_audit') or {}).get('valid')) and not timeout,
                    solver_seconds=raw.get('seconds'),solver_status=raw.get('status'),source=raw.get('source'),
                    fallback_selected=raw.get('fallback_selected'),overrun_gt_10ms=raw.get('overrun_gt_10ms'),metrics=payload.get('metrics'))
                rows.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
                if len(rows)%20==0:print(json.dumps(dict(runs=len(rows),expected=len(jobs),valid=sum(r['valid'] for r in rows))),flush=True)
        assert len(rows)==len(jobs) and all(sha(p)==h for p,h in protect.items())
        write(OUT/'completion.json',dict(status='finished_bounded_range_development',physical_runs=len(rows),logical_settings=220,
            valid_physical_runs=sum(r['valid'] for r in rows),exceptions=sum(r['worker_status']=='exception' for r in rows),
            watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),overrun_gt_10ms=sum(bool(r['overrun_gt_10ms']) for r in rows),
            wall_seconds=time.perf_counter()-begin,protected_unchanged=True,holdout_used=False))
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(read(OUT/'completion.json')))
    except BaseException:
        write(OUT/'aborted.json',dict(completed=len(rows),traceback=traceback.format_exc()));raise

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),Path(sys.argv[5])))
    main()
