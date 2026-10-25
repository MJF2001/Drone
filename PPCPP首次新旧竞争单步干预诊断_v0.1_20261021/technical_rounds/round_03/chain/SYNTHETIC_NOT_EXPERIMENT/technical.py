"""At most three isolated no-real-solve integration rounds; all failures retained."""
from pathlib import Path
import sys,json,os,ast,hashlib,subprocess,types,runpy,collections,copy,datetime,time
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def syntax(paths):
    rows=[]
    for p in sorted(set(map(Path,paths))):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p));rows.append(dict(path=str(p),sha256=sha(p)))
    return rows
def native_structure():
    old=ast.parse((H.parent/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_text(encoding='utf8'));new=ast.parse((H/'native_diag.py').read_text(encoding='utf8'))
    original=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='solve');fn=copy.deepcopy(next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='solve'))
    class Strip(ast.NodeTransformer):
        def visit_Assign(self,node):
            if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('intervention_used','intervention_log','forced'):return None
            return self.generic_visit(node)
        def visit_If(self,node):
            if ast.unparse(node.test)=='forced is not None':return None
            return self.generic_visit(node)
        def visit_Call(self,node):
            self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='dict':
                node.keywords=[k for k in node.keywords if k.arg!='diagnostic']
                for k in node.keywords:
                    if k.arg=='method' and isinstance(k.value,ast.Constant) and k.value.value=='PPCPP_FIRST_NEW_STEP_DIAG':k.value.value='PPCPP_INDEPENDENT'
            return node
    fn=Strip().visit(fn);assert ast.dump(fn)==ast.dump(original),'native core changed outside exact declared hook/output metadata'
    return dict(original_core_AST_equal_after_exact_declared_hook_removal=True,unchanged_move_pending_deadline_recovery_return_and_audit=True)
def action_stubs(out):
    from intervention import first_new_step,ProtocolMismatch,exception_budget
    old={(1,0)};new={(0,1),(0,-1)};o=[dict(cell=(1,0),score=3.5),dict(cell=(0,1),score=1.5)];before=copy.deepcopy(o);rows=[]
    assert first_new_step(False,False,o,old,new,(1,0)) is None;rows.append('OFF never changes')
    z=first_new_step(True,False,o,old,new,(1,0));assert z['forced_selected']==(0,1);rows.append('ON both classes unique new')
    assert first_new_step(True,False,o[:1],old,new,(1,0)) is None;rows.append('old only no trigger')
    assert first_new_step(True,False,o[1:],old,new,(0,1)) is None;rows.append('new only no trigger')
    assert first_new_step(True,False,[],old,new,(1,0)) is None;rows.append('no local options no trigger')
    assert first_new_step(True,True,o,old,new,(1,0)) is None;rows.append('used once never again')
    try:first_new_step(True,False,o+[dict(cell=(0,-1),score=1.5)],old,new,(1,0));raise RuntimeError('multi-new silently accepted')
    except ProtocolMismatch:pass
    rows.append('multiple new explicitly rejected')
    tree=ast.parse((H/'native_diag.py').read_text(encoding='utf8'));move=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='move');env=dict(route=[(0,0)],tick=lambda:None);exec(compile(ast.Module(body=[move],type_ignores=[]),'<actual native move AST with synthetic state>','exec'),env);pending={(1,0),(0,1)};env['move'](((0,0),z['forced_selected']),pending);assert env['route']==[(0,0),(0,1)] and pending=={(1,0)} and env['route'][-2]==(0,0) and 100-(len(env['route'])-1)==99;rows.append('actual move AST: new credit/previous/resource one step')
    assert o==before
    try:exception_budget([{},{}]);raise RuntimeError('second exception allowed')
    except AssertionError:pass
    exception_budget([]);exception_budget([{}]);save(out,dict(passed=True,tests=[dict(case=i+1,purpose=s,passed=True) for i,s in enumerate(rows)],extra_checks=dict(no_options_or_trace_mutation=True,one_exception_budget_rejects_two=True),real_entries=0,real_cores=0,graph_searches=0))
    print('PASS8 pure action stubs plus no-mutation and one-exception guard')
def b1(out):
    before={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};import runtime,candidate
    original=runtime.native.solve;registration=[];reads=[];codes={original.__code__,candidate.solve.__code__,runtime.run_payload.__code__}
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in codes:raise AssertionError('real entry/core forbidden during import')
    def observer(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and any(x in p.parts for x in ('inputs','jobs','outputs','logs','receipts')):reads.append(str(p));raise AssertionError('task read/write on ordinary import')
    install=sys.addaudithook;install(observer)
    def reject(h):registration.append(repr(h));raise AssertionError('task audit hook installed during import')
    sys.addaudithook=reject;sys.setprofile(profile);sys.argv=['ordinary_import_no_task_args']
    import worker,run,seal,decision_audit,analyze,verify
    sys.setprofile(None);assert runtime.native.solve is original and not registration and not reads
    after={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};assert before==after
    paths=sorted(set(worker.imported()));save(out,dict(passed=True,paths=paths,native_identity_unchanged=True,no_task_audit_registration=True,task_reads_or_writes=reads,before=before,after=after,real_entries=0,real_cores=0));print('PASS real diagnostic dependency ordinary import, no tasks/hook/mutation')
def fixture(f):
    f=Path(f);f.mkdir(parents=True);assert f.name=='SYNTHETIC_NOT_EXPERIMENT'
    for folder in ('inputs','jobs','outputs','logs','receipts','frozen_source_bytes','REFERENCES','SOURCE_REFERENCE/outputs','SOURCE_REFERENCE/inputs'):(f/folder).mkdir(parents=True)
    for p in H.glob('*.py'):put(f/p.name,p.read_bytes())
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(f/'REFERENCES'/n,b'# SYNTHETIC_NOT_EXPERIMENT frozen reference placeholder\n');put(f/'frozen_source_bytes'/n,(f/'REFERENCES'/n).read_bytes())
    put(f/'stub_reward.py',b'# SYNTHETIC_NOT_EXPERIMENT reward placeholder; never executed\n')
    save(f/'SYNTHETIC_NOT_EXPERIMENT.json',dict(synthetic_only=True,real_planners_allowed=False));save(f/'plan.json',dict(counts=dict(OFF=3,ON=3),entry_cap=6));save(f/'old_v04_hashes.json',{})
    save(f/'SOURCE_REFERENCE/seal2.json',dict(files={str(p.resolve()):sha(p) for p in (f/'REFERENCES').glob('*')}));return f.resolve()
def tiny():return dict(name='SYNTHETIC_NOT_EXPERIMENT',free=[[0,0],[1,0],[0,1],[1,1]],targets=[[1,0],[0,1]],published_targets=[[1,0],[0,1]],initial_targets=[[1,0]],covered=[],deferred_targets=[],current=[0,0],base=[0,0],previous=[-1,0],predator=[-1,0],distance_budget=100,old_route=[])
def stub_modules(f):
    import common
    common.H=Path(f).resolve();common.R=common.H;common.B=common.H/'SOURCE_REFERENCE';common.P=common.H/'REFERENCES';f=common.H
    runtime=types.ModuleType('runtime');runtime.__file__=str(f/'runtime.py');candidate=types.ModuleType('candidate');candidate.__file__=str(f/'candidate.py');native=types.ModuleType('SYNTHETIC_DIAG_NATIVE');native.__file__=str(f/'native_diag.py');native.core=types.SimpleNamespace(__file__=str(f/'stub_reward.py'))
    class Geo:
        def __init__(self,*a,**kw):self.bfs_rows_built=0;self.searches=0
    native.UnifiedGeometry=Geo;runtime.validate=lambda c:None
    def core(s,initial,budget,seed,predator,previous,**kwargs):
        kwargs['_geometry'](None);mode=runtime.synthetic_mode;on=mode=='ON';opts=[dict(cell=[0,1],distance_reward=0.,straight_reward=.5,boundary_reward=1.,score=1.5),dict(cell=[1,0],distance_reward=1.,straight_reward=1.,boundary_reward=1.,score=3.5)];goal=[0,1] if on else [1,0];other=[1,0] if on else [0,1];route=[[0,0],goal,[1,1],other,[0,0]]
        trace=[dict(index=0,current=[0,0],previous=[-1,0],pending_count=2,kind='local',options=opts,goal=goal),dict(index=1,current=goal,previous=[0,0],pending_count=1,kind='recovery',goal=other),dict(index=3,current=other,pending_count=0,kind='return',goal=[0,0])]
        log=[dict(index=0,current=[0,0],previous=[-1,0],pending_count=2,old_pending_count=1,new_pending_count=1,original_selected=[1,0],forced_selected=[0,1],options=opts,old_options=[opts[1]],new_options=[opts[0]],before_pending=[[0,1],[1,0]],after_pending=[[1,0]],after_current=[0,1],after_previous=[0,0],resource_before=100,resource_after=99,reason='first_local_both_classes_unique_new_one_step')] if on else []
        return dict(version=common.LABEL,method='PPCPP_FIRST_NEW_STEP_DIAG',route=route,status='core_complete',reason=None,seconds=.0005,budget=budget,seed=seed,seed_used=False,predator=predator,initial_previous=previous,weights=[2.,.5],trace=trace,accepted_seconds=.0004,fallback_selected=False,overrun_gt_10ms=False,diagnostic=dict(mode=mode,intervention_used=on,trigger_count=len(log),log=log))
    native.solve=core;runtime.native=native
    def entry(payload,mode,budget,seed,*,diagnostic_mode,geometry,**kwargs):
        start=time.perf_counter();assert mode=='PPCPP' and budget==20;runtime.synthetic_mode=diagnostic_mode;c=json.loads(payload);p0=native.solve(None,set(map(tuple,c['initial_targets'])),19.99,seed,c['predator'],c['previous'],_geometry=geometry);raw=dict(version='PPCPP_LAST_RESERVE_v0.2',mode='PPCPP',status='core_complete',route=p0['route'],trace=p0['trace'],selected='P0',e=None,branches={'P0':p0},reason=None);return dict(diagnostic_entry=common.LABEL,diagnostic_mode=diagnostic_mode,raw=raw,entry_seconds=time.perf_counter()-start,phase_seconds={},eligible=True,budget=20,method='PPCPP',seed=seed,injection_events=[])
    runtime.run_payload=entry;sys.modules.update(runtime=runtime,candidate=candidate);return common,runtime,candidate
def boot(f,args):
    c,*_=stub_modules(f);sys.argv=[str(c.H/'worker.py')]+args;runpy.run_path(str(c.H/'worker.py'),run_name='__main__')
def chain(f,out):
    f=fixture(f);c,rt,ca=stub_modules(f);save(f/'inputs/input_000.json',tiny());save(f/'SOURCE_REFERENCE/inputs/input_000.json',tiny());st=dict(id='SYNTHETIC_STATE',index=0,geometry='SYNTHETIC',group='SYNTHETIC',condition='MIXED_SIDE',L=2,w=2,boundary_count=1,input='inputs/input_000.json',A=[[0,1]]);save(f/'states_metadata.json',[st]);jobs=[]
    for mode in ('OFF','ON'):
        for seed in (20261020,20261021,20261022):
            j=dict(id=f'{mode}_000_{seed}',mode=mode,state=st['id'],input='inputs/input_000.json',seed=seed,budget=20);jobs.append(j);save(f/'jobs'/f'{j["id"]}.json',j)
    save(f/'order.json',jobs);save(f/'binding_files.json',sorted([p.name for p in f.glob('*.py')]+['binding_files.json','plan.json','order.json','states_metadata.json','inputs/input_000.json','SYNTHETIC_NOT_EXPERIMENT.json']))
    # Baseline is a predetermined synthetic return, not a planner run. Calling
    # the stub directly here is explicitly counted as fixture construction.
    for seed in (20261020,20261021,20261022):
        x=rt.run_payload(json.dumps(tiny()).encode(),'PPCPP',20,seed,diagnostic_mode='OFF',geometry=rt.native.UnifiedGeometry);x=copy.deepcopy(x);del x['diagnostic_entry'];del x['diagnostic_mode'];p=x['raw']['branches']['P0'];del p['diagnostic'];p['version']='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019';p['method']='PPCPP_INDEPENDENT';save(f/'SOURCE_REFERENCE/outputs'/f'formal_{st["id"]}_{seed}_PPCPP.json',dict(result=x))
    c.receipt('technical',[f/'SYNTHETIC_NOT_EXPERIMENT.json']);c.receipt('action_stubs',[f/'SYNTHETIC_NOT_EXPERIMENT.json'])
    real_run=subprocess.run
    def launch(argv,**kwargs):
        if len(argv)>4 and Path(argv[4]).name=='worker.py':argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--boot',str(f),*argv[5:]]
        return real_run(argv,**kwargs)
    subprocess.run=launch;seal=runpy.run_path(str(H/'seal.py'),run_name='SYNTHETIC_SEAL');seal['main']();runner=runpy.run_path(str(H/'run.py'),run_name='SYNTHETIC_RUN')
    try:runner['run']('ON');raise RuntimeError('missing OFF accepted')
    except FileNotFoundError:pass
    runner['run']('OFF');runner['run']('ON');runpy.run_path(str(H/'analyze.py'),run_name='__main__')
    verification=real_run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--readonly',str(f)],capture_output=True);assert verification.returncode==0,verification.stderr.decode('utf8');print(verification.stdout.decode('utf8'),flush=True)
    j=jobs[-1];old=sha(f/'outputs'/f'{j["id"]}.json');p=launch([sys.executable,'-B','-X','utf8',str(f/'worker.py'),str(f/'jobs'/f'{j["id"]}.json'),str(f/'outputs'/f'{j["id"]}.json')],capture_output=True);assert p.returncode!=0 and b'ENTRY_START ' not in p.stdout and sha(f/'outputs'/f'{j["id"]}.json')==old
    save(out,dict(passed=True,synthetic_only=True,actual_controls=['seal','run','worker','independent decision audit','analyze.export','verify.main'],stub_entry_calls=6,stub_native_core_calls=6,synthetic_reference_core_calls=3,no_real_planners_imported=True,missing_OFF_blocked=True,existing_output_blocked_before_entry=True))
def negative(f,out):
    f=fixture(f);c,*_=stub_modules(f);save(f/'binding_files.json',['common.py','plan.json']);c.receipt('technical',[f/'SYNTHETIC_NOT_EXPERIMENT.json']);c.receipt('action_stubs',[f/'SYNTHETIC_NOT_EXPERIMENT.json'])
    before=(f/'frozen_source_bytes/runtime.py').read_bytes()
    with (f/'frozen_source_bytes/runtime.py').open('ab') as z:z.write(b'BAD_REFERENCE')
    control=runpy.run_path(str(H/'seal.py'),run_name='SYNTHETIC_NEGATIVE_SEAL')
    try:control['main']();raise RuntimeError('bad reference accepted')
    except AssertionError:pass
    assert not (f/'preseal.json').exists() and not (f/'actual_order.jsonl').exists()
    with (f/'plan.json').open('ab') as z:z.write(b' ')
    try:c.require('technical');raise RuntimeError('stale PASS accepted')
    except AssertionError:pass
    assert not list((f/'outputs').glob('*'));save(out,dict(passed=True,inconsistent_reference_blocks_seal=True,stale_PASS_blocks=True,stub_entry_core_calls=0))
def csv_case(out):
    import common,verify
    f=out.parent/'CSV_SYNTHETIC';f.mkdir();rows=[dict(id='SYNTHETIC_NOT_EXPERIMENT',metric=None,nested={'中文':'引号",\n'+'长'*150000}),dict(id='CONTROL',metric=0,nested=['NA'])];common.csvsave(f/'long.csv',rows);verify.H=f;verify.csvcheck('long.csv',rows);save(out,dict(passed=True,actual_csv_roundtrip=True,long_field=True))
def run_round():
    rounds=list((H/'technical_rounds').glob('round_*'));n=len(rounds)+1;assert n<=3,'three-round limit';d=H/'technical_rounds'/f'round_{n:02d}';d.mkdir();assert not (H/'actual_order.jsonl').exists()
    save(d/'native_structure.json',native_structure());paths=list(H.glob('*.py'))+list((H/'frozen_source_bytes').glob('*.py'));old=read(H.parent/'PPCPP侧向拓宽开发诊断_v0.4_20261021/import_inventory.json')['paths'];paths += [Path(p) for p in old if Path(p).suffix=='.py'];save(d/'A_source_parse.json',syntax(paths))
    for p in H.glob('*.py'):put(d/('source_'+p.name),p.read_bytes())
    if not (H/'binding_files.json').exists():save(H/'binding_files.json',sorted([p.name for p in H.glob('*.py')]+['binding_files.json','plan.json','order.json','states_metadata.json','copy_manifest.json','stage_dependencies.json','minimal.diff','只读核验.ps1']+[str(p.relative_to(H)) for folder in ('inputs','jobs','frozen_source_bytes') for p in (H/folder).glob('*')]))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');cases=[('B1',['--b1',str(d/'B1.json')]),('action_stubs',['--stubs',str(d/'action_stubs.json')]),('negative',['--negative',str(d/'negative/SYNTHETIC_NOT_EXPERIMENT'),str(d/'negative.json')]),('csv',['--csv',str(d/'csv.json')]),('chain',['--chain',str(d/'chain/SYNTHETIC_NOT_EXPERIMENT'),str(d/'chain.json')])];results=[]
    for name,args in cases:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),*args],env=env,capture_output=True,timeout=180);put(d/f'{name}.stdout.log',p.stdout);put(d/f'{name}.stderr.log',p.stderr);results.append(dict(case=name,passed=p.returncode==0,exit_code=p.returncode));print('TECH',n,name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
        if p.returncode:print(p.stderr.decode('utf8',errors='replace')[-4000:],flush=True)
    if (d/'B1.json').exists():paths += [Path(p) for p in read(d/'B1.json')['paths'] if Path(p).suffix=='.py']
    save(d/'A_final_source_parse.json',syntax(paths));assert not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*'));save(d/'round_result.json',dict(round=n,passed=all(x['passed'] for x in results),stages=results,real_entry_core_calls=0))
    if not all(x['passed'] for x in results):print('FAIL round; no production PASS/seal; preserve and repair only allowed helper scope',flush=True);return 2
    import common
    common.save(H/'action_stub_results.json',read(d/'action_stubs.json'));common.receipt('action_stubs',[H/'action_stub_results.json']);common.receipt('technical',[p for p in d.rglob('*') if p.is_file()]);print('PASS final hash-bound technical/action gates; no real entry/core calls',flush=True);return 0
if __name__=='__main__':
    args=sys.argv[1:]
    if not args:sys.exit(run_round())
    elif args[0]=='--stubs':action_stubs(Path(args[1]))
    elif args[0]=='--b1':b1(Path(args[1]))
    elif args[0]=='--boot':boot(args[1],args[2:])
    elif args[0]=='--chain':chain(Path(args[1]),Path(args[2]))
    elif args[0]=='--negative':negative(Path(args[1]),Path(args[2]))
    elif args[0]=='--csv':csv_case(Path(args[1]))
    elif args[0]=='--readonly':
        import common
        f=Path(args[1]);common.H=f;common.R=f;common.B=f/'SOURCE_REFERENCE';common.P=f/'REFERENCES';runpy.run_path(str(H/'verify.py'),run_name='__main__')
