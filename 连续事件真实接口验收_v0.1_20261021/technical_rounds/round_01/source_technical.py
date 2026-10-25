"""Bound no-real-solve preflight; <=24 new stub API starts across <=3 rounds."""
from pathlib import Path
import sys,os,json,hashlib,ast,subprocess,types,time,copy,runpy,traceback
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with Path(p).open('xb') as f:f.write(b)
def stamp_stub(case,method):
    journal=H/'technical_stub_journal.jsonl';past=journal.read_text(encoding='utf8').splitlines() if journal.exists() else [];assert len(past)<24
    with journal.open('a',encoding='utf8') as f:f.write(json.dumps(dict(sequence=len(past)+1,case=case,method=method,kind='HANDWRITTEN_STUB_API',real_core=False))+'\n')
def fake_api(root,method,route):
    root=Path(root);rt=types.SimpleNamespace(__file__=str(root/'synthetic_api.py'));p2=types.SimpleNamespace(__file__=str(root/'synthetic_api.py'));mod=types.SimpleNamespace(__file__=str(root/'synthetic_api.py'))
    class Geo:
        def __init__(self,*a,**kw):self.bfs_rows_built=0;self.searches=0
    native=types.SimpleNamespace(__file__=str(root/'synthetic_api.py'),core=types.SimpleNamespace(__file__=str(root/'synthetic_api.py')),UnifiedGeometry=Geo)
    rt.native=native;rt.validate=lambda c:None;mod.UnifiedGeometry=Geo
    def core(s,initial,budget,seed,predator,previous,**kw):
        kw['_geometry'](s,0)
        return dict(route=copy.deepcopy(route),status='core_complete',trace=[],version='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019',method='PPCPP_INDEPENDENT',budget=budget,seconds=0.,seed=seed)
    def p2core(s,budget,variant,seed):mod.UnifiedGeometry(s,0);return dict(route=copy.deepcopy(route),status='finished',source='SYNTHETIC_FIXED',seconds=0.,seed=seed)
    native.solve=core;p2.p2_solve=p2core
    def rtentry(payload,mode,budget,seed,*,geometry):
        c=json.loads(payload);p=native.solve(c,set(map(tuple,c['initial_targets'])),budget,seed,c['predator'],c['previous'],_geometry=geometry)
        return dict(raw=dict(route=p['route'],trace=[],status='core_complete',mode='PPCPP',branches={'P0':p}),budget=budget,entry_seconds=0.,method='PPCPP',seed=seed)
    def p2entry(payload,budget,seed):
        c=json.loads(payload);p=p2.p2_solve(c,budget,'multi',seed);p.update(method='P2_MULTI',budget=budget);return dict(raw=p,budget=budget,entry_seconds=0.,method='P2_MULTI',seed=seed)
    rt.run_payload=rtentry;p2.run_payload=p2entry
    return dict(runtime=rt,candidate=types.SimpleNamespace(__file__=str(root/'synthetic_api.py')),p2=p2,p2_module=mod)
def b1(method,out):
    import worker
    called=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','core_route','precheck') and '运行环境' not in frame.f_code.co_filename:
            called.append(frame.f_code.co_filename);raise AssertionError('solver/graph call during ordinary import')
    sys.setprofile(profile);api=worker.load_api(method);original=api['runtime'].native.solve;reads=[];hooks=[]
    before={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()}
    def observe(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and any(q in p.parts for q in ('inputs','jobs','outputs','sessions','receipts')):reads.append(str(p));raise AssertionError('task file access during import')
    sys.addaudithook(observe)
    def forbid(h):hooks.append(1);raise AssertionError('audit hook installed during import')
    sys.addaudithook=forbid;sys.argv=['ordinary_import_no_task'];import session,seal,real_audit,run,verify,deliver
    sys.setprofile(None);assert not called and not reads and not hooks and api['runtime'].native.solve is original
    after={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};assert before==after
    save(out,dict(passed=True,paths=worker.imported(api),real_calls=0,graph_calls=0,no_task_io=True,no_task_hook=True,native_unchanged=True))
def references_case(out):
    from reference_contract import references,NAMES
    d=out.parent/'reference_cases';d.mkdir();src=d/'source';src.mkdir()
    for n in NAMES:put(src/n,('# SYNTHETIC reference '+n).encode())
    expected={str((src/n).resolve()):sha(src/n) for n in NAMES};rows=[]
    for case in ('absent','identical','different','source_drift'):
        dst=d/case/'frozen_source_bytes';dst.mkdir(parents=True)
        if case in ('identical','different'):
            for n in NAMES:put(dst/n,(src/n).read_bytes())
        if case=='different':
            with (dst/'runtime.py').open('ab') as f:f.write(b'BAD')
        before={str(p):[sha(p),p.stat().st_mtime_ns] for p in dst.glob('*')};e=expected.copy()
        if case=='source_drift':e[str((src/'runtime.py').resolve())]='0'*64
        try:references(src,dst,e);assert case in ('absent','identical')
        except AssertionError:assert case in ('different','source_drift') and before=={str(p):[sha(p),p.stat().st_mtime_ns] for p in dst.glob('*')}
        rows.append(dict(case=case,passed=True))
    save(out,dict(passed=True,cases=rows,stub_calls=0,real_calls=0))
def units(out):
    from entry import invoke
    from contracts import admit
    rows=[]
    for c in read(H/'stub_fixture_spec.json')['units']:
        for method in ('PPCPP','P2_MULTI'):
            class Clock:
                def __init__(self):self.i=-1
                def __call__(self):self.i+=1;return [0.,.25,.5][self.i]
            api=fake_api(H,method,c['route']);stamp_stub(c['id'],method);x=invoke(json.dumps(c['input'],sort_keys=True,separators=(',',':')).encode(),method,20261021,api,api['runtime'].native.UnifiedGeometry,Clock())
            assert x['inner_budget']==19.75 and x['entry_seconds']==.5 and x['response']['route']==c['route'] and x['native_return']['budget']==19.75 and admit(c['input'],x['response'])[0]=='accepted'
            assert x['native_payload_utf8']==json.dumps(c['input'],sort_keys=True,separators=(',',':'),ensure_ascii=False)
            rows.append(dict(case=c['id'],method=method,passed=True,input=c['input'],result=x))
    save(out,dict(passed=True,stub_API_calls=len(rows),real_calls=0,actual_graph_searches=0,cases=rows))
def fixture(f):
    f=Path(f).resolve();f.mkdir(parents=True);assert f.name=='SYNTHETIC_TECHNICAL_NOT_REAL'
    for folder in ('inputs','jobs','outputs','logs','sessions','receipts','frozen_source_bytes','REFERENCES'):(f/folder).mkdir()
    for p in H.glob('*.py'):put(f/p.name,p.read_bytes())
    put(f/'synthetic_api.py',b'# Handwritten fake API only. No algorithm module imported.\n')
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(f/'REFERENCES'/n,b'# SYNTHETIC bytes reference\n')
    save(f/'source_lock.json',{str(p):sha(p) for p in (f/'REFERENCES').glob('*')})
    save(f/'config.json',dict(synthetic_only=True,real_entry_cap=6,entry_budget=20,watchdog=90,seed=20261021,threads=1))
    spec=read(H/'stub_fixture_spec.json')['pipeline'];world=spec['world'];save(f/'worlds.json',{'SYNTHETIC':world});order=[];slots=[];returns={}
    for method in ('PPCPP','P2_MULTI'):
        sid='SYNTHETIC_'+method;order.append(dict(id=sid,world='SYNTHETIC',method=method,seed=20261021))
        for tick,route in zip((0,1,3),spec['routes']):
            rid=sid+f'_t{tick:03d}';slots.append(dict(id=rid,session=sid,method=method,tick=tick,seed=20261021));returns[rid]=route
    save(f/'session_order.json',order);save(f/'call_slots.json',slots);save(f/'stub_returns.json',returns)
    save(f/'binding_files.json',sorted([p.name for p in f.glob('*.py')]+['binding_files.json','config.json','worlds.json','session_order.json','call_slots.json','stub_returns.json','source_lock.json']))
    import util
    util.H=f;util.R=H.parent;util.P=f/'REFERENCES';util.receipt('technical',[f/'config.json']);return f
def boot_worker(f,args):
    import util
    f=Path(f);util.H=f;util.R=f;util.P=f/'REFERENCES';import worker
    route=[]
    if args[0]!='inventory':j=read(args[0]);route=read(f/'stub_returns.json')[j['id']]
    def api_for(method):
        api=fake_api(f,method,route)
        if args[0]!='inventory':
            owner=api['runtime'] if method=='PPCPP' else api['p2'];original=owner.run_payload
            def counted(*a,**kw):stamp_stub(j['id'],method);return original(*a,**kw)
            owner.run_payload=counted
        return api
    worker.load_api=api_for;sys.argv=[str(f/'worker.py')]+args;worker.main()
def intercept_worker(real_run,f):
    def launch(argv,**kwargs):
        if len(argv)>4 and Path(argv[4]).name=='worker.py':argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--boot-worker',str(f),*argv[5:]]
        return real_run(argv,**kwargs)
    return launch
def boot_session(f,args):
    import util
    f=Path(f);util.H=f;util.R=f;util.P=f/'REFERENCES';subprocess.run=intercept_worker(subprocess.run,f);import session
    sys.argv=[str(f/'session.py')]+args;session.main()
def chain(f,out):
    f=fixture(f);real_run=subprocess.run;worker_launch=intercept_worker(real_run,f)
    def launch(argv,**kwargs):
        if len(argv)>4 and Path(argv[4]).name=='session.py':argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--boot-session',str(f),*argv[5:]]
        return worker_launch(argv,**kwargs)
    subprocess.run=launch;import seal,run
    seal.main();run.main()
    assert read(f/'acceptance.json')['interface_pass'];p=real_run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--readonly',str(f)],capture_output=True);assert p.returncode==0,p.stderr.decode('utf8')
    put(f/'readonly.stdout.log',p.stdout);put(f/'readonly.stderr.log',p.stderr)
    attempts=[json.loads(x) for x in (f/'actual_attempts.jsonl').read_text().splitlines()];assert len(attempts)==6
    # Explicitly blocked BEFORE any entry/core: output overwrite, stale PASS,
    # and missing seal. No extra stub invocation is authorized by these probes.
    j=read(f/'jobs'/(attempts[-1]['id']+'.json'));outpath=f/'outputs'/(j['id']+'.json');before=sha(outpath)
    argv=[sys.executable,'-B','-X','utf8',str(f/'worker.py'),str(f/'jobs'/(j['id']+'.json')),str(outpath)]
    p=worker_launch(argv,capture_output=True);assert p.returncode!=0 and b'ENTRY_START ' not in p.stdout and before==sha(outpath)
    with (f/'config.json').open('ab') as z:z.write(b' ')
    p=worker_launch(argv,capture_output=True);assert p.returncode!=0 and b'ENTRY_START ' not in p.stdout
    save(out,dict(passed=True,stub_API_calls=6,real_calls=0,main_BFS=read(f/'acceptance.json')['proofs'][0]['independent_log_audit']['main_environment_BFS']*2,independent_acceptance_BFS=read(f/'acceptance.json')['independent_audit_BFS'],readonly_BFS=json.loads((f/'readonly.stdout.log').read_text().strip().splitlines()[-1])['ordinary_BFS_this_verify'],existing_output_blocked=True,stale_PASS_blocked=True,full_control_chain=True,substitutions=['handwritten fake native API/geometry, never real algorithm','two one-method synthetic sessions using fixed old positive fixture'],proxy_geometry_attempts_are_not_actual_graph_searches=True))
def run_round():
    import util
    n=len(list((H/'technical_rounds').glob('round_*')))+1;assert n<=3 and not (H/'actual_attempts.jsonl').exists();d=H/'technical_rounds'/f'round_{n:02d}';d.mkdir()
    for p in H.glob('*.py'):put(d/('source_'+p.name),p.read_bytes())
    paths=list(H.glob('*.py'))
    for p in paths:ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    cases=[('B1_PPCPP',['--b1','PPCPP',str(d/'B1_PPCPP.json')]),('B1_P2',['--b1','P2_MULTI',str(d/'B1_P2.json')]),('references',['--references',str(d/'references.json')]),('units',['--units',str(d/'units.json')]),('chain',['--chain',str(d/'chain/SYNTHETIC_TECHNICAL_NOT_REAL'),str(d/'chain.json')])];rows=[]
    for name,args in cases:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'technical.py'),*args],env=util.env(),capture_output=True,timeout=240);put(d/(name+'.stdout.log'),p.stdout);put(d/(name+'.stderr.log'),p.stderr);rows.append(dict(case=name,passed=p.returncode==0,exit_code=p.returncode));print('TECH',n,name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
        if p.returncode:print(p.stderr.decode('utf8',errors='replace')[-5000:],flush=True)
    for name in ('B1_PPCPP','B1_P2'):
        if (d/(name+'.json')).exists():paths += [Path(p) for p in read(d/(name+'.json'))['paths'] if Path(p).suffix=='.py']
    for p in set(paths):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    save(d/'round_result.json',dict(round=n,passed=all(r['passed'] for r in rows),cases=rows,real_entries=0))
    assert not (H/'actual_attempts.jsonl').exists()
    if not all(r['passed'] for r in rows):return 2
    util.receipt('technical',[p for p in d.rglob('*') if p.is_file()]+[H/'technical_stub_journal.jsonl']);print('PASS newly bound technical gate; actual real calls0',flush=True);return 0
if __name__=='__main__':
    a=sys.argv[1:]
    if not a:sys.exit(run_round())
    elif a[0]=='--b1':b1(a[1],Path(a[2]))
    elif a[0]=='--references':references_case(Path(a[1]))
    elif a[0]=='--units':units(Path(a[1]))
    elif a[0]=='--chain':chain(a[1],Path(a[2]))
    elif a[0]=='--boot-worker':boot_worker(a[1],a[2:])
    elif a[0]=='--boot-session':boot_session(a[1],a[2:])
    elif a[0]=='--readonly':
        import util
        f=Path(a[1]);util.H=f;util.R=H.parent;util.P=f/'REFERENCES';import verify;verify.main()
