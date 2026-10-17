"""Ten pre-event P2 calls only. No event geometry enters a worker."""
from run_outer_connector_diagnostic_20261016 import *
from continuous_history_inputs_20261016 import DEST as PREF
import hashlib
PREP=ALGO/'continuous_history_diagnostics/preparation_v0.1_20261016'
def worker(case,seed,dest):
    try:
        import portable_frozen
        from prepare_road_range_diagnostic_20261015 import snapshot
        c=read(case);assert c['metadata']['stage']=='pre_event'
        assert set(c['metadata'])=={'map_id','split','stage','initial_policy'}
        start=time.perf_counter();raw=portable_frozen.solve(snapshot(c),set(map(tuple,c['targets'])),'P2_MULTI',20,seed,portable_frozen.PROFILE)
        write(dest,dict(worker_status='returned',seed=seed,case_sha256=sha(case),raw=raw,independent_route_check=route_check(c,raw['route']),solve_plus_audits_seconds=time.perf_counter()-start));return 0
    except BaseException:write(dest,dict(worker_status='exception',traceback=traceback.format_exc()));return 1
def main():
    manifest(PREF)
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    PREP.mkdir(exist_ok=False);(PREP/'runs').mkdir();(PREP/'source_snapshot').mkdir()
    paths=[Path(__file__),ROOT/'continuous_history_inputs_20261016.py',ROOT/'test_continuous_history_20261016.py',ROOT/'verify_continuous_preparation_20261016.py',
        DOC.parent/'67_连续执行历史开发验证协议与输入预检_20261016.md']
    hashes=protected();hashes.update({str(p):sha(p) for p in paths});hashes.update({str(p):sha(p) for p in PREF.rglob('*') if p.is_file()})
    for p in paths:(PREP/'source_snapshot'/p.name).write_bytes(p.read_bytes())
    jobs=[]
    for i,e in enumerate(read(PREF/'records.json')):
        seed=int(hashlib.sha256((e['map_id']+':initial_only_v1').encode()).hexdigest()[:8],16)
        jobs.append(dict(run_id=f'initial_{i:02d}',case=e['initial_case'],map_id=e['map_id'],seed=seed,budget=20))
    write(PREP/'protocol.json',dict(jobs=jobs,protected_hashes=hashes,max_calls=10,comparison_calls=0,holdout_used=False,seed_policy='SHA256(map_id+:initial_only_v1) first8hex',interruption='Do not rerun completed results; incomplete attempts separately archived before explicit recovery.'))
    test=subprocess.run([sys.executable,'-X','utf8','-m','unittest','test_continuous_history_20261016','-v'],cwd=ROOT,capture_output=True,text=True)
    (PREP/'unit_tests.log').write_text(test.stdout+test.stderr,encoding='utf-8');assert test.returncode==0
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[]
    with (PREP/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
        for j in jobs:
            dest=PREP/'runs'/(j['run_id']+'.json');t=time.perf_counter();timeout=False
            with (PREP/'runs'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
                try:code=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',j['case'],str(j['seed']),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50).returncode
                except subprocess.TimeoutExpired:code=None;timeout=True
            p=read(dest) if dest.exists() else {};raw=p.get('raw',{});r=dict(j,worker_status=p.get('worker_status','no_result'),returncode=code,watchdog_timeout=timeout,
                valid=bool(p.get('independent_route_check',{}).get('valid')) and not timeout,seconds=raw.get('seconds'),process_wall_seconds=time.perf_counter()-t,
                overrun_gt_10ms=raw.get('seconds',0)>20.01)
            rows.append(r);ledger.write(json.dumps(r,ensure_ascii=False)+'\n');ledger.flush();print(j['run_id'],r['valid'],flush=True)
    assert all(sha(Path(p))==h for p,h in hashes.items())
    write(PREP/'completion.json',dict(calls=len(rows),valid=sum(r['valid'] for r in rows),overruns=sum(r['overrun_gt_10ms'] for r in rows),comparison_calls=0,protected_unchanged=True,holdout_used=False))
    write(PREP/'sha256.json',{str(p.relative_to(PREP)):sha(p) for p in PREP.rglob('*') if p.is_file()})
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),int(sys.argv[3]),Path(sys.argv[4])))
    main()
