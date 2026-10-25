"""Up to three preserved no-real-solve integration rounds; new bound PASS."""
from pathlib import Path
import sys,os,json,ast,subprocess,runpy,copy,time,types,hashlib
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with Path(p).open('xb') as f:f.write(b)
def b1(mode,out):
    import common,worker
    rt,ca=worker.dependencies(mode);original=rt.native.solve;codes={original.__code__,ca.solve.__code__,rt.run_payload.__code__};registrations=[];reads=[]
    before={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()}
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in codes:raise AssertionError('real entry/core forbidden on import')
    def observer(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and any(q in p.parts for q in ('inputs','jobs','outputs','logs','receipts')):reads.append(str(p));raise AssertionError('task access on import')
    sys.addaudithook(observer)
    def reject(hook):registrations.append(repr(hook));raise AssertionError('audit registration on import')
    sys.addaudithook=reject;sys.setprofile(profile);sys.argv=['ordinary_import_no_task']
    import run,seal,generate,input_audit,decision_audit,evaluation,analyze,verify,deliver,assemble,technical_helpers,drawing
    sys.setprofile(None);assert rt.native.solve is original and not registrations and not reads
    after={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};assert before==after
    save(out,dict(passed=True,mode=mode,paths=worker.imported(rt),task_reads=reads,audit_registrations=registrations,core_identity_unchanged=True,real_entries=0,real_cores=0))
def reference_cases(out):
    from reference_contract import references,NAMES
    d=out.parent/'reference_fixtures';d.mkdir();src=d/'sources';src.mkdir()
    for n in NAMES:put(src/n,('# frozen '+n).encode())
    expected={str((src/n).resolve()):sha(src/n) for n in NAMES};rows=[]
    for case in ('absent','identical','different','source_drift'):
        target=d/case/'frozen_source_bytes';target.mkdir(parents=True)
        if case in ('identical','different'):
            for n in NAMES:put(target/n,(src/n).read_bytes())
        if case=='different':
            with (target/'runtime.py').open('ab') as f:f.write(b'BAD')
        before={str(p):[p.read_bytes().hex(),p.stat().st_mtime_ns] for p in target.glob('*')};e=expected.copy()
        if case=='source_drift':e[str((src/'runtime.py').resolve())]='0'*64
        try:result=references(src,target,e);assert case in ('absent','identical');rows.append(dict(case=case,passed=True,result=result))
        except AssertionError:
            assert case in ('different','source_drift');assert before=={str(p):[p.read_bytes().hex(),p.stat().st_mtime_ns] for p in target.glob('*')};rows.append(dict(case=case,passed=True,blocked_without_changes=True))
    assert all(sha(src/n)==expected[str((src/n).resolve())] for n in NAMES);save(out,dict(passed=True,cases=rows,real_entries=0))
def fixture(f):
    f=Path(f).resolve();f.mkdir(parents=True);assert f.name=='SYNTHETIC_NOT_EXPERIMENT'
    for folder in ('inputs','jobs','outputs','logs','receipts','frozen_source_bytes','REFERENCES','OLD'):(f/folder).mkdir()
    for p in H.glob('*.py'):put(f/p.name,p.read_bytes())
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(f/'REFERENCES'/n,b'# SYNTHETIC reference only\n')
    put(f/'stub_reward.py',b'# SYNTHETIC reward placeholder\n')
    save(f/'SYNTHETIC_NOT_EXPERIMENT.json',dict(synthetic_only=True,real_planners_allowed=False));save(f/'plan.json',dict(counts=dict(prep=1,gate=2,formal=6),entry_cap=9,entry_budget=20,watchdog=90,threads=1))
    save(f/'OLD/preseal.json',dict(files={str(p.resolve()):sha(p) for p in (f/'REFERENCES').glob('*')}))
    return f
def stub_modules(f):
    import technical_helpers as old
    c,rt,ca=old.stub_modules(f);c.D=Path(f)/'OLD'
    original=rt.run_payload
    def entry(payload,mode,budget,seed,*,geometry,diagnostic_mode=None,**kw):
        requested=rt.synthetic_requested_mode
        x=original(payload,mode,budget,seed,diagnostic_mode='OFF' if requested=='FROZEN' else diagnostic_mode,geometry=geometry,**kw)
        if requested=='FROZEN':
            del x['diagnostic_entry'];del x['diagnostic_mode'];p=x['raw']['branches']['P0'];del p['diagnostic'];p['version']='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019';p['method']='PPCPP_INDEPENDENT'
        return x
    rt.run_payload=entry;return c,rt,ca
def boot(f,args):
    c,*_=stub_modules(f);sys.argv=[str(c.H/'worker.py')]+args;runpy.run_path(str(c.H/'worker.py'),run_name='__main__')
def chain(f,out):
    f=fixture(f);c,rt,ca=stub_modules(f);import technical_helpers as old
    save(f/'inputs/tiny.json',old.tiny());st=dict(id='SYNTHETIC_STATE',index=0,geometry='SYNTHETIC',group='SYNTHETIC',condition='MIXED_SIDE',L=2,w=2,boundary_count=1,input='inputs/tiny.json',A=[[0,1]])
    save(f/'states_metadata.json',[st]);prep=[dict(id='prep_SYNTHETIC',phase='prep',mode='FROZEN',state=st['id'],input=st['input'],seed=20261021,budget=20,seal='seal1.json')]
    gate=[dict(id=f'gate_{st["id"]}_{mode}',phase='gate',mode=mode,state=st['id'],input=st['input'],seed=20261020,budget=20,seal='seal2.json') for mode in ('FROZEN','OFF')]
    formal=[dict(id=f'formal_{st["id"]}_{seed}_{mode}',phase='formal',mode=mode,state=st['id'],input=st['input'],seed=seed,budget=20,seal='seal2.json') for i,seed in enumerate((20261020,20261021,20261022)) for mode in (('OFF','ON') if i%2==0 else ('ON','OFF'))]
    for j in prep+gate+formal:save(f/'jobs'/f'{j["id"]}.json',j)
    save(f/'prep_order.json',prep)
    save(f/'binding_files.json',sorted([p.name for p in f.glob('*.py')]+['plan.json','binding_files.json','SYNTHETIC_NOT_EXPERIMENT.json','prep_order.json','states_metadata.json','inputs/tiny.json']))
    c.receipt('technical',[f/'SYNTHETIC_NOT_EXPERIMENT.json']);c.receipt('action_stubs',[f/'SYNTHETIC_NOT_EXPERIMENT.json'])
    # Full real controllers; only solver interface and post-history geometry
    # construction/audit are explicit tiny handwritten fixtures.
    real_run=subprocess.run
    def launch(argv,**kwargs):
        if len(argv)>4 and Path(argv[4]).name=='worker.py':argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--boot',str(f),*argv[5:]]
        return real_run(argv,**kwargs)
    subprocess.run=launch;sealer=runpy.run_path(str(H/'seal.py'),run_name='SYNTHETIC_SEAL');runner=runpy.run_path(str(H/'run.py'),run_name='SYNTHETIC_RUN')
    sealer['main']('seal1');runner['run']('prep')
    # Stand-in for actual 6-history/48-state generator, never a claimed map test.
    save(f/'gate_order.json',gate);save(f/'order.json',formal);save(f/'synthetic_generated.json',dict(synthetic_only=True,geometry_generation_not_tested_by_this_fixture=True))
    c.receipt('generated',[f/'gate_order.json',f/'order.json',f/'synthetic_generated.json'])
    try:sealer['main']('seal2');raise RuntimeError('missing input audit accepted')
    except FileNotFoundError:pass
    assert not (f/'seal2.json').exists();c.receipt('inputs_audited',[f/'synthetic_generated.json']);sealer['main']('seal2')
    try:runner['run']('formal');raise RuntimeError('missing gate accepted')
    except FileNotFoundError:pass
    runner['run']('gate');runner['run']('formal');runpy.run_path(str(H/'analyze.py'),run_name='__main__')
    p=real_run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--readonly',str(f)],capture_output=True);assert p.returncode==0,p.stderr.decode('utf8');print(p.stdout.decode('utf8'),flush=True)
    j=formal[-1];target=f/'outputs'/f'{j["id"]}.json';before=sha(target)
    p=launch([sys.executable,'-B','-X','utf8',str(f/'worker.py'),str(f/'jobs'/f'{j["id"]}.json'),str(target)],capture_output=True);assert p.returncode!=0 and b'ENTRY_START ' not in p.stdout and before==sha(target)
    save(out,dict(passed=True,synthetic_only=True,actual_controllers=['seal1','prep run/worker','generated/audit receipts','seal2','gate run/worker','interleaved formal run/worker','analyze export','readonly verify'],stub_entry_calls=9,stub_core_calls=9,real_entry_calls=0,real_core_calls=0,missing_audit_blocked=True,missing_gate_blocked=True,existing_output_blocked=True,substitutions=['handwritten tiny geometry/post-history artifacts','fixed synthetic runtime/core return; no real runtime imports'],production_geometry_not_claimed=True))
def negative(f,out):
    f=fixture(f);c,*_=stub_modules(f);save(f/'binding_files.json',['common.py','plan.json']);c.receipt('technical',[f/'SYNTHETIC_NOT_EXPERIMENT.json']);c.receipt('action_stubs',[f/'SYNTHETIC_NOT_EXPERIMENT.json'])
    put(f/'frozen_source_bytes/runtime.py',b'BAD_REFERENCE');sealer=runpy.run_path(str(H/'seal.py'),run_name='NEGATIVE')
    try:sealer['main']('seal1');raise RuntimeError('inconsistent reference accepted')
    except AssertionError:pass
    assert not (f/'seal1.json').exists()
    with (f/'plan.json').open('ab') as z:z.write(b' ')
    try:c.require('technical');raise RuntimeError('stale PASS accepted')
    except AssertionError:pass
    assert not (f/'actual_order.jsonl').exists();save(out,dict(passed=True,inconsistent_reference_blocks_seal=True,stale_PASS_blocks=True,stub_and_real_calls=0))
def csv_case(out):
    import common,verify
    f=out.parent/'CSV_SYNTHETIC';f.mkdir();rows=[dict(name='合成',v=None,nested={'x':'中文",\n'+'长'*150000}),dict(name='zero',v=0,nested=[])];common.csvsave(f/'long.csv',rows);verify.H=f;verify.csvcheck('long.csv',rows);save(out,dict(passed=True,long_CSV_actual_roundtrip=True))
def run_round():
    import common,technical_helpers as old
    n=len(list((H/'technical_rounds').glob('round_*')))+1;assert n<=3;d=H/'technical_rounds'/f'round_{n:02d}';d.mkdir();assert not (H/'actual_order.jsonl').exists()
    for p in H.glob('*.py'):put(d/('source_'+p.name),p.read_bytes())
    save(d/'native_structure.json',old.native_structure());paths=list(H.glob('*.py'))+list((H/'frozen_source_bytes').glob('*.py'))
    save(d/'A_source_parse.json',old.syntax(paths))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    cases=[('B1_FROZEN',['--b1','FROZEN',str(d/'B1_FROZEN.json')]),('B1_DIAG',['--b1','OFF',str(d/'B1_DIAG.json')]),('actions',['--actions',str(d/'actions.json')]),('references',['--references',str(d/'references.json')]),('negative',['--negative',str(d/'negative/SYNTHETIC_NOT_EXPERIMENT'),str(d/'negative.json')]),('csv',['--csv',str(d/'csv.json')]),('chain',['--chain',str(d/'chain/SYNTHETIC_NOT_EXPERIMENT'),str(d/'chain.json')])];rows=[]
    for name,args in cases:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'technical.py'),*args],env=env,capture_output=True,timeout=240);put(d/(name+'.stdout.log'),p.stdout);put(d/(name+'.stderr.log'),p.stderr);rows.append(dict(case=name,passed=p.returncode==0,exit_code=p.returncode));print('TECH',n,name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
        if p.returncode:print(p.stderr.decode('utf8',errors='replace')[-5000:],flush=True)
    for name in ('B1_FROZEN','B1_DIAG'):
        if (d/(name+'.json')).exists():paths += [Path(p) for p in read(d/(name+'.json'))['paths'] if Path(p).suffix=='.py']
    save(d/'A_actual_dependencies_parse.json',old.syntax(paths));assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*'))
    save(d/'round_result.json',dict(round=n,passed=all(r['passed'] for r in rows),cases=rows,real_entries=0,real_cores=0))
    if not all(r['passed'] for r in rows):return 2
    common.save(H/'action_stub_results.json',read(d/'actions.json'));common.receipt('action_stubs',[H/'action_stub_results.json']);common.receipt('technical',[p for p in d.rglob('*') if p.is_file()]);print('PASS new final-bound technical gate; real calls0',flush=True);return 0
if __name__=='__main__':
    a=sys.argv[1:]
    if not a:sys.exit(run_round())
    elif a[0]=='--b1':b1(a[1],Path(a[2]))
    elif a[0]=='--actions':
        import technical_helpers;technical_helpers.action_stubs(Path(a[1]))
    elif a[0]=='--references':reference_cases(Path(a[1]))
    elif a[0]=='--negative':negative(a[1],Path(a[2]))
    elif a[0]=='--csv':csv_case(Path(a[1]))
    elif a[0]=='--boot':boot(a[1],a[2:])
    elif a[0]=='--chain':chain(a[1],Path(a[2]))
    elif a[0]=='--readonly':
        import common
        common.H=Path(a[1]);common.R=common.H;common.D=common.H/'OLD';common.P=common.H/'REFERENCES'
        runpy.run_path(str(H/'verify.py'),run_name='__main__')
