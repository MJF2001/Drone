"""Bounded B1 experiment; no optimizer calls during preparation."""
from pathlib import Path
import copy,json,os,sys,time,subprocess,traceback
from old_plan_quality_diagnostic_20261016 import ROOT,ALGO,SOURCE,read,write,sha,route_check
BASE=ALGO/'outer_connector_diagnostics'
INPUT=BASE/'inputs_v0.1_20261016'
OUT=BASE/'run_v0.1_20261016'
A=ALGO/'old_plan_quality_diagnostics/run_v0.1_20261016'
DOC=ROOT/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/64_窗口外连接轨迹单变量诊断协议_20261016.md'
METHODS=('LITERAL','RECONNECT','P2_MULTI')
def manifest(p):
    assert all(sha(p/n)==h for n,h in read(p/'sha256.json').items()),str(p)
def protected():
    from old_plan_quality_diagnostic_20261016 import protected_sources
    result=protected_sources()
    paths=[DOC,Path(__file__),ROOT/'outer_connector_candidate_20261016.py',ROOT/'verify_outer_connector_diagnostic_20261016.py',ROOT/'test_outer_connector_20261016.py']
    paths+=list(A.rglob('*.json'))
    result.update({str(p):sha(p) for p in paths});return result
def prepare():
    import portable_frozen
    from prepare_road_range_diagnostic_20261015 import snapshot
    from outer_connector_candidate_20261016 import range_plan,responsibilities,outside_segments,UnifiedGeometry
    manifest(SOURCE);manifest(A)
    refs={e['map_id']:e for e in read(A/'reference_ledger.json')}
    INPUT.mkdir(parents=True,exist_ok=False);(INPUT/'cases').mkdir();records=[]
    for f in read(SOURCE/'families.json'):
        if f['anchor']==f['control']:continue
        i=len(records)//2;src=SOURCE/'cases'/(f['anchor']+'.json');original=read(src)
        e=refs[f['map_id']];prep=A/'runs'/(e['preparation_run_id']+'.json');refroute=read(prep)['raw']['route']
        assert original['metadata']['range_diagnostic']['role']=='event'
        for ref in ('RAW','P2_REF'):
            c=copy.deepcopy(original)
            if ref=='P2_REF':c['old_route']=refroute
            assert all(c[k]==original[k] for k in c if k!='old_route')
            p=INPUT/'cases'/f'c{i:02d}_{ref}.json';write(p,c);s=snapshot(c)
            plan=range_plan(s,set(map(tuple,c['metadata']['initial_targets'])),float('inf'));cfg=plan['plans']['R_PLUS1']
            assigned=responsibilities(s,cfg);g=UnifiedGeometry(s,float('inf'))
            segments={m:outside_segments(s,cfg,assigned,g,m) for m in METHODS[:2]}
            records.append(dict(case=str(p),map_id=f['map_id'],reference=ref,source_case=str(src),source_sha256=sha(src),
                saved_preparation=str(prep),saved_preparation_sha256=sha(prep),case_sha256=sha(p),plan=plan,responsibilities=assigned,segments=segments))
    assert len(records)==20;write(INPUT/'records.json',records)
    write(INPUT/'sha256.json',{str(p.relative_to(INPUT)):sha(p) for p in INPUT.rglob('*') if p.is_file()})
    print('Prepared 20 inputs; no optimizer called.',flush=True)
def worker(case,method,budget,dest):
    try:
        import portable_frozen
        from prepare_road_range_diagnostic_20261015 import snapshot
        from outer_connector_candidate_20261016 import solve
        c=read(case);s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']));seed=c['metadata']['range_diagnostic']['paired_seed']
        start=time.perf_counter()
        raw=portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE) if method=='P2_MULTI' else solve(s,initial,method,budget,seed)
        write(dest,dict(worker_status='returned',method=method,budget=budget,seed=seed,case_sha256=sha(case),raw=raw,
            independent_route_check=route_check(c,raw['route']),solve_plus_audits_seconds=time.perf_counter()-start));return 0
    except BaseException:
        write(dest,dict(worker_status='exception',traceback=traceback.format_exc()));return 1
def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    manifest(INPUT)
    from verify_outer_connector_diagnostic_20261016 import check_inputs
    checks=check_inputs();assert len(checks)==20
    p=protected();OUT.mkdir(parents=True,exist_ok=False);(OUT/'runs').mkdir();(OUT/'source_snapshot').mkdir()
    for path in [DOC,Path(__file__),ROOT/'outer_connector_candidate_20261016.py',ROOT/'verify_outer_connector_diagnostic_20261016.py',ROOT/'test_outer_connector_20261016.py']:
        (OUT/'source_snapshot'/path.name).write_bytes(path.read_bytes())
    test=subprocess.run([sys.executable,'-X','utf8','-m','unittest','test_outer_connector_20261016','-v'],cwd=ROOT,capture_output=True,text=True)
    (OUT/'unit_tests.log').write_text(test.stdout+test.stderr,encoding='utf-8');assert test.returncode==0
    jobs=[]
    for i,e in enumerate(read(INPUT/'records.json')):
        order=list(METHODS[i%3:]+METHODS[:i%3])
        if i%2:order.reverse()
        for b in ((1,20) if i%2==0 else (20,1)):
            for m in order:jobs.append(dict(run_id=Path(e['case']).stem+f'_b{b}_{m}',case=e['case'],map_id=e['map_id'],reference=e['reference'],budget=b,method=m))
    assert len(jobs)==120
    write(OUT/'protocol.json',dict(jobs=jobs,protected_hashes=p,input_manifest_sha256=sha(INPUT/'sha256.json'),expected_calls=120,holdout_used=False))
    write(OUT/'input_checks.json',checks)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[];start=time.perf_counter()
    with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
        for i,j in enumerate(jobs):
            dest=OUT/'runs'/(j['run_id']+'.json');t=time.perf_counter();timeout=False
            with (OUT/'runs'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
                try:code=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',j['case'],j['method'],str(j['budget']),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
                except subprocess.TimeoutExpired:code=None;timeout=True
            payload=read(dest) if dest.exists() else {};raw=payload.get('raw',{});check=payload.get('independent_route_check',{})
            row=dict(j,returncode=code,watchdog_timeout=timeout,worker_status=payload.get('worker_status','no_result'),
                valid=bool(check.get('valid')) and not timeout,steps=check.get('steps'),seconds=raw.get('seconds'),
                source=raw.get('source'),process_wall_seconds=time.perf_counter()-t,overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01)
            rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
            if (i+1)%12==0:print(json.dumps(dict(completed=i+1,total=120,valid=sum(r['valid'] for r in rows))),flush=True)
    assert all(sha(Path(k))==v for k,v in p.items());manifest(INPUT)
    write(OUT/'completion.json',dict(calls=len(rows),valid=sum(r['valid'] for r in rows),exceptions=sum(r['worker_status']=='exception' for r in rows),watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),wall_seconds=time.perf_counter()-start,protected_unchanged=True,holdout_used=False))
    write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()});print(read(OUT/'completion.json'),flush=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),Path(sys.argv[5])))
    elif len(sys.argv)>1 and sys.argv[1]=='--prepare':prepare()
    else:main()
