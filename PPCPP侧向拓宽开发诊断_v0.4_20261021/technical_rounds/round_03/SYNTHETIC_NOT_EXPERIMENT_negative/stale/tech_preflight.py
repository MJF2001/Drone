"""At most three no-solve integration rounds; no production PASS on any failure."""
from pathlib import Path
import sys,os,json,subprocess,hashlib,ast,datetime,difflib
from tech_lib import syntax_gate,guarded_worker
H=Path(__file__).resolve().parent;R=H.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def initial():
    assert not (H/'binding_files.json').exists()
    deps={'technical':[], 'stat_stubs':[], 'seal1':['technical','stat_stubs'], 'prep':['technical','stat_stubs','seal1'], 'generated':['prep'], 'seal2':['technical','stat_stubs','seal1','prep','generated'], 'gate':['technical','stat_stubs','seal2','prep','generated'], 'formal':['technical','stat_stubs','seal2','prep','generated','gate']}
    save(H/'stage_dependencies.json',dict(dependencies=deps,production_counts=[6,12,288],cap=306,clock=dict(warm_entry_seconds=20,watchdog_seconds=90,threads=1),synthetic_plan='6 prep +12 gate +2 formal tests existing fixed past-count assertions; does not alter production orders'))
    names=[str(p.relative_to(H)) for p in H.glob('*.py')]+['binding_files.json','protocol.md','maps.json','prep_order.json','stage_dependencies.json','source_manifest_initial.json','old_v03_hashes.json']
    names += [str(p.relative_to(H)) for folder in ('inputs','jobs','frozen_source_bytes') for p in (H/folder).glob('*') if p.is_file()]
    names += ['../PPCPP侧向拓宽固定批诊断执行稿_给sol_20261021.md','../PPCPP侧向拓宽v0.2技术修复接续执行稿_给sol_20261021.md','../PPCPP侧向拓宽v0.3入口守卫修复接续执行稿_给sol_20261021.md','../PPCPP侧向拓宽v0.4准备链集成修复执行稿_给sol_20261021.md']
    save(H/'binding_files.json',sorted(names))
def main():
    if not (H/'binding_files.json').exists():initial()
    rounds=sorted((H/'technical_rounds').glob('round_*'));number=len(rounds)+1;assert number<=3,'three-round limit reached'
    d=H/'technical_rounds'/f'round_{number:02d}';d.mkdir()
    assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*'))
    for p,h in read(H/'old_v03_hashes.json').items():assert sha(p)==h,p
    save(d/'source_snapshot.json',{str(p.relative_to(H)):sha(p) for p in H.glob('*.py')})
    for p in H.glob('*.py'):
        with (d/('source_'+p.name)).open('xb') as f:f.write(p.read_bytes())
    structure=guarded_worker(H/'worker.py',R/'PPCPP侧向拓宽开发诊断_v0.2_20261021/worker.py');save(d/'worker_structure.json',structure)
    paths=list(H.glob('*.py'))+list((H/'frozen_source_bytes').glob('*.py'))
    oldinv=R/'PPCPP侧向拓宽开发诊断_v0.1_20261021/import_inventory.json'
    if oldinv.exists():paths += [Path(p) for p in read(oldinv)['paths'] if Path(p).suffix=='.py']
    syntax=syntax_gate(paths);save(d/'A_initial_syntax.json',dict(files=syntax,passed=True))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    cases=[('B1',['b1',str(d/'B1.json')])]
    cases += [('B2_'+m,['worker',m,str(d/('SYNTHETIC_NOT_EXPERIMENT_'+m)),str(d/('B2_'+m+'.json'))]) for m in ('inventory','PP','P2','stale')]
    cases += [('references',['refs',str(d/'SYNTHETIC_NOT_EXPERIMENT_references'),str(d/'references.json')]),('C',['export',str(d/'SYNTHETIC_NOT_EXPERIMENT_export'),str(d/'C.json')]),('negative_gates',['negatives',str(d/'SYNTHETIC_NOT_EXPERIMENT_negative'),str(d/'negative_gates.json')]),('integration',['integration',str(d/'SYNTHETIC_NOT_EXPERIMENT_INTEGRATION'),str(d/'integration.json')])]
    results=[]
    for label,args in cases:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'tech_child.py'),*args],env=env,capture_output=True,timeout=180)
        for suffix,b in [('stdout',p.stdout),('stderr',p.stderr)]:
            with (d/f'{label}.{suffix}.log').open('xb') as f:f.write(b)
        success=p.returncode==0;results.append(dict(case=label,passed=success,exit_code=p.returncode))
        print('TECH',number,label,'PASS' if success else 'FAIL',flush=True)
        if not success:print(p.stderr.decode('utf8',errors='replace')[-3500:],flush=True)
    # Eight original statistic cases run afresh, even if another independent
    # technical stage failed; no production receipt is emitted in this call.
    p=subprocess.run([sys.executable,'-B','-X','utf8','-c',"import stat_stubs,json; print(json.dumps(stat_stubs.run(),ensure_ascii=False))"],cwd=H,env=env,capture_output=True)
    with (d/'eight_statistical_stubs.stdout.log').open('xb') as f:f.write(p.stdout)
    with (d/'eight_statistical_stubs.stderr.log').open('xb') as f:f.write(p.stderr)
    results.append(dict(case='eight_statistical_stubs',passed=p.returncode==0,exit_code=p.returncode))
    if p.returncode==0:save(d/'eight_statistical_stubs.json',json.loads(p.stdout))
    if (d/'B1.json').exists():paths += [Path(p) for p in read(d/'B1.json')['paths'] if Path(p).suffix=='.py']
    save(d/'A_final_syntax.json',dict(files=syntax_gate(paths),passed=True))
    assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*'))
    expected=read(R/'复杂障碍压力开发测试_v0.1_20261021/formal_seal.json');frozen=[]
    for p in [R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'/n for n in ('runtime.py','candidate.py','p2_adapter.py')]+[R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py']:
        key=str(p.resolve());assert key in expected and sha(p)==expected[key],('frozen_drift',str(p));frozen.append(dict(path=key,sha256=sha(p)))
    save(d/'frozen_and_zero_real_check.json',dict(frozen=frozen,real_entries=0,real_cores=0,actual_order_exists=False))
    save(d/'round_result.json',dict(round=number,passed=all(x['passed'] for x in results),stages=results,complete_to_endpoint=any(x['case']=='integration' and x['passed'] for x in results),real_entry_core_calls=0))
    if not all(x['passed'] for x in results):
        print('ROUND FAILED; no production PASS/seal; preserve evidence and repair only authorized helper scope',flush=True);return 2
    import common
    x=read(d/'eight_statistical_stubs.json');common.save(H/'stat_stub_results.json',x);common.receipt('stat_stubs',[H/'stat_stub_results.json'])
    artifacts=[p for p in d.rglob('*') if p.is_file()]
    common.receipt('technical',artifacts)
    print('PASS FULL NO-SOLVE TECHNICAL ROUND',number,'final hash-bound receipts created; real entries/cores=0',flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
