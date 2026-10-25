"""Isolated technical cases. Synthetic interfaces never import real planners."""
from pathlib import Path
import sys,os,json,hashlib,types,runpy,subprocess,ast,shutil,importlib,time
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def file_state():return {str(p.relative_to(H)):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()}
def b1(out):
    before=file_state();sys.path.insert(0,str(H.parent/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'))
    import runtime,candidate,p2_adapter
    pp=runtime.native.solve;p2=p2_adapter.p2_solve;events=[];registrations=[]
    forbidden={f.__code__ for f in (pp,p2,runtime.run_payload,p2_adapter.run_payload,p2_adapter.solve,candidate.solve)}
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in forbidden:raise AssertionError('real solver/entry forbidden in B1')
    def monitor(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and any(x in p.parts for x in ('inputs','jobs','outputs','logs','receipts')):events.append([event,str(p),str(args[1])]);raise AssertionError('task artifact access in import')
    register=sys.addaudithook;register(monitor)
    def reject(hook):registrations.append(repr(hook));raise AssertionError('task audit hook installed by import')
    sys.addaudithook=reject;sys.setprofile(profile);sys.argv=['ordinary_import_without_task_arguments']
    for name in ('worker','run','analysis','verify','generate','seal','reference_contract'):importlib.import_module(name)
    sys.setprofile(None)
    assert runtime.native.solve is pp and p2_adapter.p2_solve is p2 and not registrations and not events
    assert file_state()==before
    paths=sorted({str(Path(m.__file__).resolve()) for m in sys.modules.values() if getattr(m,'__file__',None) and Path(m.__file__).is_file()}|{str(Path(runtime.native.__file__).resolve()),str(Path(runtime.native.core.__file__).resolve()),str(Path(runtime.validate.__code__.co_filename).resolve())})
    save(out,dict(status='PASS',native_solve_identity_unchanged=True,p2_solve_identity_unchanged=True,
         native_source=pp.__code__.co_filename,p2_source=p2.__code__.co_filename,audit_registration_attempts=registrations,task_accesses=events,before=before,after=file_state(),paths=paths,real_entry_core_calls=0,method='own audit observer installed using saved original; public addaudithook rejects; profile forbids real entry/core functions'))
    print('PASS B1 ordinary real-dependency import; zero task effects / solve / hook registration')
def setup_fixture(f):
    f=Path(f);f.mkdir();p=f/'STUB_FROZEN_NOT_REAL';p.mkdir()
    for n in ('inputs','jobs','outputs','logs','receipts','frozen_source_bytes','history','witnesses','figures'):(f/n).mkdir()
    for src in H.glob('*.py'):put(f/src.name,src.read_bytes())
    for n in ('protocol.md','maps.json'):put(f/n,(H/n).read_bytes())
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(p/n,b'# SYNTHETIC_NOT_EXPERIMENT: stub provenance placeholder\n');put(f/'frozen_source_bytes'/n,(p/n).read_bytes())
    put(f/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',b'# SYNTHETIC_NOT_EXPERIMENT native stub source\n')
    put(p/'reward_stub.py',b'# SYNTHETIC_NOT_EXPERIMENT reward stub source\n')
    put(f/'PPCPP侧向拓宽固定批诊断执行稿_给sol_20261021.md',b'SYNTHETIC_NOT_EXPERIMENT protocol placeholder')
    put(f/'PPCPP场景证据只读整理_20261021/整理结论.md',b'SYNTHETIC_NOT_EXPERIMENT provenance placeholder')
    save(f/'PPCPP场景证据只读整理_20261021/54状态读取核对.json',dict(synthetic=True))
    save(f/'formal_seal.json',{str(x.resolve()):sha(x) for x in p.glob('*.py')})
    save(f/'binding_files.json',sorted([x.name for x in f.glob('*.py')]+['protocol.md','maps.json','binding_files.json']))
    save(f/'SYNTHETIC_NOT_EXPERIMENT.json',dict(real_planner_allowed=False,production_protocol_unchanged=True))
    return f
def stub_environment(f):
    # Real common I/O/hash/receipt implementation; only root/source directories
    # and the planner module interfaces are replaced in this child process.
    import common
    f=Path(f).resolve();common.H=f;common.R=f;common.P=f/'STUB_FROZEN_NOT_REAL';common.S=f
    runtime=types.ModuleType('runtime');runtime.__file__=str(common.P/'runtime.py')
    candidate=types.ModuleType('candidate');candidate.__file__=str(common.P/'candidate.py')
    adapter=types.ModuleType('p2_adapter');adapter.__file__=str(common.P/'p2_adapter.py')
    native=types.ModuleType('SYNTHETIC_NOT_EXPERIMENT_native');native.__file__=str(f/'基线复现准备_20261019/独立版_v0.2/ppcpp.py');native.core=types.SimpleNamespace(__file__=str(common.P/'reward_stub.py'))
    calls=[]
    def pp_original(c):calls.append('PP_STUB');return dict(route=c['SYNTHETIC_FIXED_RETURN'],status='core_complete',mode='PPCPP',branches={'P0':{}},source='SYNTHETIC_NOT_EXPERIMENT')
    def p2_original(c):calls.append('P2_STUB');return dict(route=c['SYNTHETIC_FIXED_RETURN'],status='core_complete',source='SYNTHETIC_NOT_EXPERIMENT')
    native.solve=pp_original;adapter.p2_solve=p2_original;runtime.native=native
    def pp_entry(payload,mode,budget,seed):
        assert mode=='PPCPP' and budget==20
        return dict(raw=native.solve(json.loads(payload)),entry_seconds=.001,budget=budget,seed=seed,method=mode)
    def p2_entry(payload,budget,seed):
        assert budget==20
        return dict(raw=adapter.p2_solve(json.loads(payload)),entry_seconds=.001,budget=budget,seed=seed,method='P2_MULTI')
    runtime.run_payload=pp_entry;adapter.run_payload=p2_entry
    sys.modules.update(runtime=runtime,candidate=candidate,p2_adapter=adapter)
    return common,calls,pp_original,p2_original
def synthetic_input():
    return dict(name='SYNTHETIC_NOT_EXPERIMENT',free=[[0,0],[1,0],[0,1],[1,1]],targets=[[1,0]],published_targets=[[1,0]],initial_targets=[[1,0]],covered=[],deferred_targets=[],current=[0,0],base=[0,0],previous=None,predator=[-1,0],distance_budget=100,old_route=[],SYNTHETIC_FIXED_RETURN=[[0,0],[1,0],[0,0]])
def synthetic_credentials(c,jobs):
    # Fresh test-only receipts use the actual hash/require code and fixture files.
    c.receipt('technical',[c.H/'SYNTHETIC_NOT_EXPERIMENT.json'])
    runpy.run_path(str(H/'stat_stubs.py'),run_name='__main__')
    for j in jobs:save(c.H/'jobs'/f'{j["id"]}.json',j)
    files={str(Path(m.__file__).resolve()):sha(m.__file__) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
    for p in c.H.rglob('*'):
        if p.is_file():files[str(p.resolve())]=sha(p)
    save(c.H/'seal1.json',dict(complete=True,binding=c.binding(),critical={},files=files))
    c.receipt('seal1',[c.H/'seal1.json'])
def worker_child(f,args):
    c,calls,original_pp,original_p2=stub_environment(f);closure={}
    def profile(frame,event,arg):
        if event=='return' and frame.f_code.co_name=='main' and Path(frame.f_code.co_filename).name=='worker.py':
            loc=frame.f_locals
            if 'counts' in loc:
                closure.update(j_local=loc['j']['id'],inp=str(loc['inp']),reads_same_object=True,counts=loc['counts'],original_pp_identity=loc['original_pp'] is original_pp,original_p2_identity=loc['original_p2'] is original_p2)
                for name,expect in [('pp',{'counts','original_pp'}),('p2',{'counts','original_p2'}),('audit',{'inp','reads'})]:
                    fn=loc[name];assert set(fn.__code__.co_freevars)==expect,(name,fn.__code__.co_freevars)
                    cells=dict(zip(fn.__code__.co_freevars,[x.cell_contents for x in fn.__closure__]));assert cells.get('counts',loc['counts']) is loc['counts'];assert cells.get('reads',loc['reads']) is loc['reads'];closure[name+'_freevars']=list(fn.__code__.co_freevars)
    sys.setprofile(profile);sys.argv=[str(c.H/'worker.py')]+args
    try:runpy.run_path(str(c.H/'worker.py'),run_name='__main__')
    finally:
        sys.setprofile(None);print('SYNTHETIC_CLOSURE '+json.dumps(dict(closure=closure,stub_calls=calls,real_planners_loaded=False)),file=sys.stderr if args==['inventory'] else sys.stdout,flush=True)
def worker_fixture(mode,f,out):
    setup_fixture(f);c,calls,pp,p2=stub_environment(f)
    save(c.H/'inputs/tiny.json',synthetic_input())
    job=dict(id='SYNTHETIC_'+mode,phase='prep',case='tiny',input='inputs/tiny.json',method='P2_MULTI' if mode=='P2' else 'PPCPP',seed=20261021,budget=20,seal='seal1.json')
    synthetic_credentials(c,[job])
    if mode=='stale':
        with (c.H/'protocol.md').open('ab') as z:z.write(b'\nSYNTHETIC_STALE_BINDING')
    argv=['inventory'] if mode=='inventory' else [str(c.H/'jobs'/f'{job["id"]}.json'),str(c.H/'outputs/result.json')]
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'worker_child',str(c.H),*argv],capture_output=True)
    put(c.H/'fixture_stdout.log',p.stdout);put(c.H/'fixture_stderr.log',p.stderr)
    count=dict(entries=p.stdout.count(b'ENTRY_START '),cores=p.stdout.count(b'CORE_START '))
    if mode in ('PP','P2'):
        assert p.returncode==0,p.stderr.decode();assert count==dict(entries=1,cores=1)
        x=read(c.H/'outputs/result.json');assert x['job']==job and len(x['actual_core_calls'])==1 and set(x['runtime_reads'])=={str(c.H/'inputs/tiny.json')}
        assert x['actual_core_calls'][0]['kind']==('P2_multi_core' if mode=='P2' else 'PPCPP_native')
        info=json.loads(next(x for x in p.stdout.decode().splitlines() if x.startswith('SYNTHETIC_CLOSURE ')).split(' ',1)[1]);assert info['closure']['original_pp_identity'] and info['closure']['original_p2_identity'];assert info['stub_calls']==(['P2_STUB'] if mode=='P2' else ['PP_STUB'])
    else:
        assert count==dict(entries=0,cores=0) and not (c.H/'outputs/result.json').exists()
        assert (p.returncode==0) if mode=='inventory' else (p.returncode!=0 and b'AssertionError' in p.stderr)
    save(out,dict(status='PASS',synthetic=True,mode=mode,child_exit=p.returncode,markers=count,actual_worker_source_sha256=sha(c.H/'worker.py'),real_entry_core_calls=0))
def reference_tests(f,out):
    from reference_contract import references,NAMES
    f=Path(f);f.mkdir();rows=[]
    for mode in ('absent','identical','different','source_drift'):
        d=f/mode;d.mkdir();src=d/'source';src.mkdir();dst=d/'frozen_source_bytes';dst.mkdir()
        for n in NAMES:put(src/n,('SYNTHETIC_NOT_EXPERIMENT '+n).encode())
        expected={str((src/n).resolve()):sha(src/n) for n in NAMES}
        if mode!='absent':
            for n in NAMES:put(dst/n,(src/n).read_bytes())
        if mode=='different':
            with (dst/NAMES[0]).open('ab') as z:z.write(b'BAD')
        if mode=='source_drift':
            with (src/NAMES[0]).open('ab') as z:z.write(b'DRIFT')
        before={str(p):[sha(p),p.stat().st_mtime_ns] for p in d.rglob('*') if p.is_file()}
        try:r=references(src,dst,expected);error=None
        except AssertionError as ex:r=None;error=repr(ex)
        assert bool(error)==(mode in ('different','source_drift'))
        for p,v in before.items():assert [sha(p),Path(p).stat().st_mtime_ns]==v
        assert not (d/'seal1.json').exists()
        rows.append(dict(case=mode,passed=True,error=error,result=r))
    save(out,dict(status='PASS',cases=rows,real_entry_core_calls=0))
def export_case(f,out):
    import analysis,verify
    f=Path(f);f.mkdir();analysis.H=f;verify.H=f
    nested=dict(中文='引号"，逗号,\n第二行',nested=[None,False,{'x':'长'*180000}])
    rows=[dict(id='SYNTHETIC_NOT_EXPERIMENT_'+str(i),condition='CONTROL' if i==1 else 'H_SIDE',valid=i!=2,timely=i!=2,metrics=None if i==2 else dict(length=3+i),visits_A=dict(classification='not_applicable') if i==1 else nested,pp_first_A_event=nested) for i in range(4)]
    a=dict(rows=rows,pairs=[dict(id='SYNTHETIC',nested=nested)],views={v:dict(all={},events={},controls={},states=[{'synthetic':nested}],groups=[{'synthetic':nested}],contrasts=[{'synthetic':nested}],strata={'synthetic':{'x':{'synthetic':nested}}}) for v in ('timely','legal')},signal={'synthetic':True},detailed_examples=[],time_summary={})
    analysis.compute=lambda:a;analysis.export()
    tree=ast.parse((H/'analysis.py').read_text(encoding='utf8'))
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='csvsave' and any(isinstance(k,ast.Constant) and k.value=='288正式调用完整指标.csv' for k in ast.walk(n.args[0])))
    expected=eval(compile(ast.Expression(body=call.args[1]),'<actual export flatten AST>','eval'),analysis.__dict__,{'a':a})
    verify.csvcheck('288正式调用完整指标.csv',expected);verify.csvcheck('144全部配对与不可用原因.csv',a['pairs'])
    import csv
    with (f/'288正式调用完整指标.csv').open(encoding='utf-8-sig',newline='') as z:actual=list(csv.DictReader(z))
    assert len(actual)==4 and actual[2]['length']=='' and actual[2]['valid']=='False' and json.loads(actual[1]['visits_A'])['classification']=='not_applicable'
    assert json.loads(actual[0]['visits_A'])==nested and max(len(v) for r in actual for v in r.values())>131072
    save(out,dict(status='PASS',synthetic=True,rows=4,actual_export_and_csvcheck=True,flatten_expression=ast.unparse(call.args[1]),long_field=True,failed_metric_empty_not_zero=True,real_entry_core_calls=0))
def negatives(f,out):
    from tech_lib import syntax_gate
    f=Path(f);f.mkdir();bad=f/'INTENTIONALLY_INVALID_NOT_ACTIVE.py';put(bad,b'def broken(:\n')
    sentinel=f/'UNREACHABLE_AFTER_SYNTAX.json'
    try:syntax_gate([bad],lambda:save(sentinel,dict(bad=True)));raise AssertionError('syntax allowed')
    except SyntaxError:pass
    assert not sentinel.exists()
    d=f/'stale';setup_fixture(d);c,*_=stub_environment(d);c.receipt('technical',[d/'SYNTHETIC_NOT_EXPERIMENT.json'])
    with (d/'protocol.md').open('ab') as z:z.write(b'INVALIDATE')
    try:c.require('technical');save(f/'UNREACHABLE_AFTER_HASH.json',{});raise RuntimeError('stale accepted')
    except AssertionError:pass
    assert not (f/'UNREACHABLE_AFTER_HASH.json').exists()
    save(out,dict(status='PASS',syntax_negative=True,stale_hash_negative=True,post_gate_sentinels=0,real_entry_core_calls=0))
def integration(f,out):
    blocked=[]
    for kind in ('mismatch_reference','stale_PASS'):
        neg=Path(f).parent/(Path(f).name+'_'+kind);setup_fixture(neg);cc,*_=stub_environment(neg)
        cc.receipt('technical',[neg/'SYNTHETIC_NOT_EXPERIMENT.json']);cc.receipt('stat_stubs',[neg/'SYNTHETIC_NOT_EXPERIMENT.json'])
        target=neg/'frozen_source_bytes/runtime.py' if kind=='mismatch_reference' else neg/'protocol.md'
        with target.open('ab') as z:z.write(b'SYNTHETIC_NEGATIVE')
        before=target.read_bytes();control=runpy.run_path(str(H/'seal.py'),run_name='synthetic_negative_seal')
        try:control['run'](1);raise RuntimeError('invalid seal accepted')
        except AssertionError:pass
        assert target.read_bytes()==before and not (neg/'seal1.json').exists() and not (neg/'actual_order.jsonl').exists()
        blocked.append(kind)
    setup_fixture(f);c,*_=stub_environment(f);f=c.H
    save(f/'inputs/tiny.json',synthetic_input());jobs={}
    for phase,n in [('prep',6),('gate',12),('formal',2)]:
        order=[]
        for i in range(n):
            j=dict(id=f'SYNTHETIC_{phase}_{i:02d}',phase=phase,case='tiny',input='inputs/tiny.json',method='PPCPP' if phase=='prep' or i%2==0 else 'P2_MULTI',seed=20261021,budget=20,seal='seal1.json' if phase=='prep' else 'seal2.json');order.append(j);save(f/'jobs'/f'{j["id"]}.json',j)
        jobs[phase]=order;save(f/({'prep':'prep_order.json','gate':'gate_order.json','formal':'order.json'}[phase]),order)
    c.receipt('technical',[f/'SYNTHETIC_NOT_EXPERIMENT.json']);runpy.run_path(str(H/'stat_stubs.py'),run_name='__main__')
    # Preserve real control code. Only launching the worker is redirected to a
    # child which injects the clearly labelled stub modules before run_path.
    real_run=subprocess.run
    def launch(argv,**kw):
        if len(argv)>4 and Path(argv[4]).name=='worker.py':argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'worker_child',str(f),*argv[5:]]
        return real_run(argv,**kw)
    subprocess.run=launch
    seal=runpy.run_path(str(H/'seal.py'),run_name='synthetic_seal_control')
    runner=runpy.run_path(str(H/'run.py'),run_name='synthetic_run_control')
    seal['run'](1);runner['run']('prep')
    # Synthetic generation stand-in: no geometry claim; stage products and
    # generated receipt use actual common I/O/hash code, not production inputs.
    save(f/'states.json',[dict(synthetic=True)]);c.receipt('generated',[f/'states.json']);c.receipt('inputs_audited',[f/'states.json'])
    seal['run'](2)
    before=(f/'actual_order.jsonl').read_bytes()
    try:runner['run']('formal');raise RuntimeError('missing gate accepted')
    except FileNotFoundError:pass
    assert (f/'actual_order.jsonl').read_bytes()==before
    runner['run']('gate');runner['run']('formal')
    for stage in ('technical','stat_stubs','seal1','prep','generated','seal2','gate','formal'):c.require(stage)
    for name in ('seal1.json','seal2.json'):
        for p,h in c.check_seal(name)['files'].items():assert sha(p)==h,p
    order=[json.loads(x) for x in (f/'actual_order.jsonl').read_text(encoding='utf8').splitlines()];assert len(order)==20
    import analysis,verify
    analysis.H=f;verify.H=f
    rows=[analysis.job_row(j) for j in jobs['formal']];a=dict(rows=rows,pairs=[{'synthetic':True}],views={v:dict(all={},events={},controls={},states=[],groups=[],contrasts=[],strata={}) for v in ('timely','legal')},signal={'synthetic':True},detailed_examples=[],time_summary={})
    analysis.compute=lambda:a;analysis.export()
    flatten=[{**{k:v for k,v in r.items() if k not in ('metrics','visits_A','pp_first_A_event')},**(r['metrics'] or {}),'visits_A':r['visits_A'],'pp_first_A_event':r['pp_first_A_event']} for r in rows]
    verify.csvcheck('288正式调用完整指标.csv',flatten);assert all(r['valid'] and r['timely'] for r in rows)
    # Existing-output failure at the real runner, before any new subprocess.
    # Clone the initial controls; do not remove, mutate or reuse old evidence.
    neg=f.parent/(f.name+'_EXISTING_OUTPUT');setup_fixture(neg);c.H=neg
    save(neg/'inputs/tiny.json',synthetic_input());j=jobs['prep'][0];save(neg/'prep_order.json',[j]);save(neg/'jobs'/f'{j["id"]}.json',j);put(neg/'outputs'/f'{j["id"]}.json',b'SYNTHETIC_EXISTING_RESULT_DO_NOT_OVERWRITE')
    c.receipt('technical',[neg/'SYNTHETIC_NOT_EXPERIMENT.json']);c.receipt('stat_stubs',[neg/'SYNTHETIC_NOT_EXPERIMENT.json']);save(neg/'seal1.json',dict(complete=True,binding=c.binding(),critical={},files={}));c.receipt('seal1',[neg/'seal1.json'])
    r2=runpy.run_path(str(H/'run.py'),run_name='synthetic_existing_output_control')
    try:r2['run']('prep');raise RuntimeError('output overwrite allowed')
    except AssertionError:pass
    assert not (neg/'actual_order.jsonl').exists() and (neg/'outputs'/f'{j["id"]}.json').read_bytes()==b'SYNTHETIC_EXISTING_RESULT_DO_NOT_OVERWRITE'
    save(out,dict(status='PASS',synthetic=True,actual_control_sources=['seal.py','run.py','worker.py','analysis.export','verify.csvcheck','common.require/check_seal'],simulation_counts=dict(prep=6,gate=12,formal=2,stub_entries=20,stub_cores=20),production_counts_unchanged=[6,12,288],negative_seals_blocked=blocked,missing_gate_blocked=True,existing_output_blocked_before_entry=True,interfaces_replaced=['planner runtime/candidate/p2_adapter','worker subprocess bootstrap','synthetic generation stage product and input-audit receipt','analysis.compute synthetic selection only'],real_entry_core_calls=0))
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='b1':b1(Path(sys.argv[2]))
    elif mode=='worker_child':worker_child(sys.argv[2],sys.argv[3:])
    elif mode=='worker':worker_fixture(sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]))
    elif mode=='refs':reference_tests(Path(sys.argv[2]),Path(sys.argv[3]))
    elif mode=='export':export_case(Path(sys.argv[2]),Path(sys.argv[3]))
    elif mode=='negatives':negatives(Path(sys.argv[2]),Path(sys.argv[3]))
    elif mode=='integration':integration(Path(sys.argv[2]),Path(sys.argv[3]))
