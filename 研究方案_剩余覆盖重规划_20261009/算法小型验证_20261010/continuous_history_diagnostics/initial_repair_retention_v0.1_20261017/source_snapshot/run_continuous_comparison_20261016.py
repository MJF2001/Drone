"""Frozen 80-job response comparison; no new initial planning."""
from verify_continuous_preparation_20261016 import *
RUN=ALGO/'continuous_history_diagnostics/comparison_v0.1_20261016'
def worker(case,method,budget,seed,dest):
    try:
        import portable_frozen
        from prepare_road_range_diagnostic_20261015 import snapshot
        from outer_connector_candidate_20261016 import solve
        c=read(case);s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']));start=time.perf_counter()
        raw=portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE) if method=='P2_MULTI' else solve(s,initial,method,budget,seed)
        write(dest,dict(worker_status='returned',case_sha256=sha(case),method=method,budget=budget,seed=seed,raw=raw,
            independent_route_check=route_check(c,raw['route']),solve_plus_audits_seconds=time.perf_counter()-start));return 0
    except BaseException:write(dest,dict(worker_status='exception',traceback=traceback.format_exc()));return 1
def main():
    manifest(PREP);manifest(CHECK);assert read(CHECK/'summary.json')['event_status_counts']=={'gates_passed':10}
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    hashes=read(PREP/'protocol.json')['protected_hashes'];assert all(sha(Path(p))==h for p,h in hashes.items())
    paths=[Path(__file__),ROOT/'verify_continuous_comparison_20261016.py',ROOT/'outer_connector_candidate_20261016.py']
    paths+=list(PREP.rglob('*'))+list(CHECK.rglob('*'))
    hashes.update({str(p):sha(p) for p in paths if p.is_file()})
    RUN.mkdir(exist_ok=False);(RUN/'runs').mkdir();(RUN/'source_snapshot').mkdir()
    for p in paths[:3]:(RUN/'source_snapshot'/p.name).write_bytes(p.read_bytes())
    jobs=[]
    for i,e in enumerate(read(CHECK/'checks.json')):
        for rep in (0,1):
            for b in ((1,20) if (i+rep)%2==0 else (20,1)):
                for m in (('LITERAL','P2_MULTI') if (i+rep)%2==0 else ('P2_MULTI','LITERAL')):
                    jobs.append(dict(run_id=f'c{i:02d}_r{rep}_b{b}_{m}',case=str(CHECK/'cases'/(e['map_id']+'.json')),map_id=e['map_id'],repeat=rep,budget=b,seed=e[f'seed{rep}'],method=m))
    assert len(jobs)==80
    write(RUN/'protocol.json',dict(jobs=jobs,protected_hashes=hashes,expected_calls=80,initial_calls_reused=10,holdout_used=False,stop='80 responses only; no retuning or extra repeats.'))
    test=subprocess.run([sys.executable,'-X','utf8','-m','unittest','test_continuous_history_20261016','test_outer_connector_20261016','-v'],cwd=ROOT,capture_output=True,text=True)
    (RUN/'unit_tests.log').write_text(test.stdout+test.stderr,encoding='utf-8');assert test.returncode==0
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[];begin=time.perf_counter()
    with (RUN/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
        for j in jobs:
            dest=RUN/'runs'/(j['run_id']+'.json');t=time.perf_counter();timeout=False
            with (RUN/'runs'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
                try:code=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',j['case'],j['method'],str(j['budget']),str(j['seed']),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
                except subprocess.TimeoutExpired:code=None;timeout=True
            p=read(dest) if dest.exists() else {};raw=p.get('raw',{});check=p.get('independent_route_check',{})
            row=dict(j,worker_status=p.get('worker_status','no_result'),returncode=code,watchdog_timeout=timeout,valid=bool(check.get('valid')) and not timeout,
                steps=check.get('steps'),seconds=raw.get('seconds'),source=raw.get('source'),overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01,process_wall_seconds=time.perf_counter()-t)
            rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
            if len(rows)%8==0:print('completed',len(rows),'valid',sum(r['valid'] for r in rows),flush=True)
    assert all(sha(Path(p))==h for p,h in hashes.items())
    write(RUN/'completion.json',dict(calls=len(rows),valid=sum(r['valid'] for r in rows),exceptions=sum(r['worker_status']=='exception' for r in rows),watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),wall_seconds=time.perf_counter()-begin,protected_unchanged=True,holdout_used=False))
    write(RUN/'sha256.json',{str(p.relative_to(RUN)):sha(p) for p in RUN.rglob('*') if p.is_file()})
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),int(sys.argv[5]),Path(sys.argv[6])))
    main()
