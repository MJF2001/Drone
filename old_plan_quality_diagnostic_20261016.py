"""Bounded no-event old-tail sensitivity diagnostic; frozen solvers unchanged."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time,traceback

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'range_diagnostics/inputs_v0.1_20261015'
OUT=ALGO/'old_plan_quality_diagnostics/run_v0.1_20261016'
DOC=ROOT/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/62_旧剩余计划质量配对诊断协议_20261016.md'
METHODS=('KEEP_EMPTY','P2_MULTI')
REFS=('RAW','P2_REF')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def route_check(c,route):
    """Ledger-only independent audit, not using planner geometry or audit."""
    r=tuple(map(tuple,route));free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));covered=set(map(tuple,c['covered']))
    return dict(valid=bool(r) and r[0]==tuple(c['current']) and r[-1]==tuple(c['base'])
        and set(r)<=free and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]))
        and targets<=covered|set(r) and len(r)-1<=c['distance_budget'],steps=len(r)-1 if r else None)
def reference_case(original,route):
    if not route_check(original,route)['valid']:raise ValueError('invalid reference')
    c=copy.deepcopy(original);c['old_route']=[list(p) for p in route]
    assert all(c[k]==original[k] for k in c if k!='old_route')
    return c
def precheck(c):
    assert c['metadata']['split']=='development'
    assert c['metadata']['event']=='no_change' and c['metadata']['range_diagnostic']['role']=='control'
    assert set(map(tuple,c['targets']))==set(map(tuple,c['metadata']['initial_targets']))
    assert c['radius']==0 and route_check(c,c['old_route'])['valid']

def worker(case,method,budget,dest):
    try:
        import portable_frozen
        from prepare_road_range_diagnostic_20261015 import snapshot
        from road_range_candidate_20261015 import solve
        c=read(case);precheck(c);s=snapshot(c);seed=c['metadata']['range_diagnostic']['paired_seed']
        initial=set(map(tuple,c['metadata']['initial_targets']));begin=time.perf_counter()
        raw=portable_frozen.solve(s,initial,'P2_MULTI',budget,seed,portable_frozen.PROFILE) if method=='P2_MULTI' else solve(s,initial,'R_SEED',budget,seed)
        outer=time.perf_counter()-begin
        write(dest,dict(worker_status='returned',method=method,budget=budget,seed=seed,case_sha256=sha(case),raw=raw,
            independent_route_check=route_check(c,raw['route']),solve_plus_audits_seconds=outer))
        return 0
    except BaseException:
        write(dest,dict(worker_status='exception',traceback=traceback.format_exc()));return 1

def protected_sources():
    paths=[DOC,Path(__file__),ROOT/'verify_old_plan_quality_20261016.py',ROOT/'test_old_plan_quality_20261016.py',
        ROOT/'portable_frozen.py',ROOT/'road_range_candidate_20261015.py',ROOT/'range_p2_engine_20261015.py',
        ROOT/'prepare_road_range_diagnostic_20261015.py',ROOT/'verify_road_range_diagnostic_20261015.py']
    paths+=list(SOURCE.rglob('*.json'))
    result={str(p):sha(p) for p in paths}
    base=ALGO/'frozen_baselines/v2_20261012';m=read(base/'manifest.json')
    result.update({str(base/'source'/n):h for n,h in m['source_sha256'].items()})
    result[str(base/'runtime_profile.json')]=m['runtime_profile_sha256']
    candidate=ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014'
    result.update({str(candidate/n):h for n,h in read(candidate/'manifest.json')['files_sha256'].items()})
    assert all(sha(Path(p))==h for p,h in result.items())
    return result

def main():
    assert Path(sys.executable).resolve()==ROOT/'运行环境/python/python.exe'
    assert all(sha(SOURCE/n)==h for n,h in read(SOURCE/'sha256.json').items())
    families=read(SOURCE/'families.json');assert len(families)==12
    cases=[SOURCE/'cases'/(f['control']+'.json') for f in families]
    for p in cases:precheck(read(p))
    protected=protected_sources();OUT.mkdir(parents=True,exist_ok=False)
    for n in ('inputs','runs','source_snapshot'):(OUT/n).mkdir()
    for p in (DOC,Path(__file__),ROOT/'verify_old_plan_quality_20261016.py',ROOT/'test_old_plan_quality_20261016.py'):
        (OUT/'source_snapshot'/p.name).write_bytes(p.read_bytes())
    prep=[dict(run_id=f'prep_c{i:02d}',case=str(p),map_id=families[i]['map_id'],method='P2_MULTI',budget=20,phase='reference') for i,p in enumerate(cases)]
    jobs=[]
    for i,p in enumerate(cases):
        order=[(ref,m) for ref in REFS for m in METHODS]
        order=order[i%4:]+order[:i%4]
        if i%2:order.reverse()
        for b in ((1,20) if i%2==0 else (20,1)):
            for ref,m in order:jobs.append(dict(run_id=f'c{i:02d}_{ref}_b{b}_{m}',case=str(OUT/'inputs'/f'c{i:02d}_{ref}.json'),
                map_id=families[i]['map_id'],method=m,reference=ref,budget=b,phase='comparison'))
    assert len(jobs)==96
    write(OUT/'protocol.json',dict(version='old_tail_quality_v0.1_20261016',preparation_jobs=prep,comparison_jobs=jobs,
        expected_calls=108,protected_hashes=protected,holdout_used=False,preparation_charged_separately=True,
        limitation='Counterfactual tail quality at fixed control snapshot, not regenerated initial strong-plan history; not equal-total-budget ranking across references.',
        stop='12 preparation plus 96 comparison calls only; no retuning, event runs or extra seeds.'))
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[];begin=time.perf_counter()
    def execute(j,ledger):
        dest=OUT/'runs'/(j['run_id']+'.json');start=time.perf_counter();timeout=False
        with (OUT/'runs'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
            try:code=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',j['case'],j['method'],str(j['budget']),str(dest)],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
            except subprocess.TimeoutExpired:code=None;timeout=True
        payload=read(dest) if dest.exists() else {};raw=payload.get('raw',{})
        row=dict(j,returncode=code,watchdog_timeout=timeout,process_wall_seconds=time.perf_counter()-start,
            worker_status=payload.get('worker_status','no_result'),valid=bool(payload.get('independent_route_check',{}).get('valid')) and not timeout,
            steps=payload.get('independent_route_check',{}).get('steps'),seconds=raw.get('seconds'),source=raw.get('source'),
            overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01,core_steps=len(raw['core_route'])-1 if raw.get('core_route') else None)
        ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush();rows.append(row)
        return row,payload
    try:
        with (OUT/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
            references=[]
            for i,j in enumerate(prep):
                row,payload=execute(j,ledger)
                if not row['valid']:raise RuntimeError('reference failed; comparison not started')
                original=read(cases[i]);strong=reference_case(original,payload['raw']['route'])
                write(OUT/'inputs'/f'c{i:02d}_RAW.json',original);write(OUT/'inputs'/f'c{i:02d}_P2_REF.json',strong)
                references.append(dict(map_id=j['map_id'],source_case=str(cases[i]),source_sha256=sha(cases[i]),preparation_run_id=j['run_id'],
                    raw_steps=len(original['old_route'])-1,reference_steps=len(strong['old_route'])-1,
                    raw_case_sha256=sha(OUT/'inputs'/f'c{i:02d}_RAW.json'),reference_case_sha256=sha(OUT/'inputs'/f'c{i:02d}_P2_REF.json')))
                print(json.dumps(dict(reference=i+1,total=12,raw=references[-1]['raw_steps'],optimized=references[-1]['reference_steps'])),flush=True)
            write(OUT/'reference_ledger.json',references)
            for i,j in enumerate(jobs):
                execute(j,ledger)
                if (i+1)%16==0:print(json.dumps(dict(comparison=i+1,total=96)),flush=True)
        assert all(sha(Path(p))==h for p,h in protected.items())
        write(OUT/'completion.json',dict(status='bounded_old_plan_quality_finished',calls=len(rows),preparation=12,comparison=96,
            valid_preparation=sum(r['valid'] for r in rows[:12]),valid_comparison=sum(r['valid'] for r in rows[12:]),
            exceptions=sum(r['worker_status']=='exception' for r in rows),watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),
            wall_seconds=time.perf_counter()-begin,protected_unchanged=True,holdout_used=False))
        write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
        print(json.dumps(read(OUT/'completion.json')),flush=True)
    except BaseException:
        write(OUT/'aborted.json',dict(completed_calls=len(rows),traceback=traceback.format_exc()));raise

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),Path(sys.argv[5])))
    main()
