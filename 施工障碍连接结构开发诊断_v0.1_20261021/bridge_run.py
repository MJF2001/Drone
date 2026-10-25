"""Fresh-process orchestration reusing exactly the previous formal adapters."""
import os,sys,json,time,hashlib,subprocess,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
PRIOR=R/'PPCPP四方向共同预算正式比较_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def adapters():
    sys.path.insert(0,str(P))
    import runtime,p2_adapter,candidate
    return runtime,p2_adapter
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def metrics(c,r):
    d=R/'评价指标完整补算与数据审计_v0.1_20261020'
    a=load('bridge_metric_a',d/'metrics.py').metrics(c,r)
    b=load('bridge_metric_b',d/'crosscheck.py').calculate(c,r)
    assert a==b and a['complete_legal'];return a
def seal_prep():
    runtime,p2=adapters();prior=read(PRIOR/'seal.json')
    for p,h in prior.items():assert sha(p)==h,p
    # Same adapter files and native references as prior experiment.py branches.
    assert 'runtime.run_payload(payload,\'PPCPP\',20,j[\'seed\'])' in (PRIOR/'experiment.py').read_text(encoding='utf8')
    files=dict(prior)
    for p in H.rglob('*'):
        if p.is_file():files[str(p.resolve())]=sha(p)
    save(H/'prep_seal.json',dict(stage='before_six_history_entries',created_utc=time.time(),files=files,prior_seal_sha256=sha(PRIOR/'seal.json'),adapters=dict(PPCPP=str(Path(runtime.__file__).resolve()),P2_MULTI=str(Path(p2.__file__).resolve()),native=str(Path(runtime.native.__file__).resolve())),limitations='Python and relevant project/dependency bytes inherited; Windows system DLLs are not a full machine image. No independent runtime argument receipt beyond sealed adapter/job/input evidence.'))
    print('PREP SEALED',len(files),flush=True)
def worker(jobpath,outpath):
    j=read(jobpath);runtime,p2=adapters();seal=read(H/j['seal'])['files'];imports={}
    paths={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
    paths|={str(Path(runtime.native.__file__).resolve()),str(Path(runtime.native.core.__file__).resolve())}
    for p in sorted(paths):
        if Path(p).is_relative_to(R):assert p in seal and sha(p)==seal[p],p;imports[p]=sha(p)
    inp=H/j['input'];assert sha(inp)==seal[str(inp.resolve())]
    c=read(inp)['input'] if j.get('base_record') else read(inp)
    payload=json.dumps(c,ensure_ascii=False,allow_nan=False).encode('utf8')
    called=time.time()
    if j['method']=='PPCPP':x=runtime.run_payload(payload,'PPCPP',20,j['seed'])
    else:x=p2.run_payload(payload,20,j['seed'])
    save(outpath,dict(job=j,input_sha256=sha(inp),imports=imports,native_file=str(Path(runtime.native.__file__).resolve()),native_sha256=sha(runtime.native.__file__),call_utc=called,result=x))
def run_phase(phase):
    jobs=read(H/(phase+'_order.json')) if phase!='prep' else [read(H/'prep_jobs'/f'{id}.json') for id in read(H/'base_order.json')]
    outdir=H/('prep_outputs' if phase=='prep' else 'gate_outputs' if phase=='gate' else 'outputs')
    logdir=H/('prep_logs' if phase=='prep' else 'gate_logs' if phase=='gate' else 'logs')
    outdir.mkdir(exist_ok=True);logdir.mkdir(exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for i,j in enumerate(jobs):
        out=outdir/(j['id']+'.json');assert not out.exists();jp=H/('prep_jobs' if phase=='prep' else 'jobs')/(j['id']+'.json')
        started=time.time()
        try:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jp),str(out)],env=env,capture_output=True,timeout=90)
            (logdir/(j['id']+'.txt')).write_bytes(p.stdout+p.stderr);code=p.returncode
        except subprocess.TimeoutExpired as e:
            code='watchdog';(logdir/(j['id']+'.txt')).write_text(str(e),encoding='utf8')
        record=dict(id=j['id'],phase=phase,method=j['method'],code=code,started_utc=started,finished_utc=time.time())
        with (H/'actual_order.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(record)+'\n')
        if code!=0:raise RuntimeError(('technical_stop',record))
        x=read(out)['result'];c=read(H/j['input']);c=c['input'] if j.get('base_record') else c
        route=x['raw'].get('route')
        if route:metrics(c,route)
        if phase=='prep':assert route and x['eligible'],('prep_failed',j,x)
        if phase=='gate':
            expected=j['expected'];assert bool(route)==(expected=='complete'),('gate_failed',j,x)
            if route:assert x['entry_seconds']<20
        if x['raw'].get('status') in ('core_invalid','exception'):raise RuntimeError(('audit_or_technical',j,x))
        print(phase,i+1,'/',len(jobs),j['id'],x['raw'].get('status'),round(x['entry_seconds'],4),flush=True)
def setup_gates():
    from bridge_generate import case,rect
    fixtures=[]
    f=rect(0,0,5,3);t={(0,1),(4,1)};c=case('history_transit',f,t,(4,1),t,(3,1));c['base']=(0,1);fixtures.append(c)
    f=rect(0,0,5,3)-{(2,1)};c=case('detour',f,{(4,1)},(0,1));fixtures.append(c)
    f={(x,1) for x in range(5)};c=case('single_bridge_return',f,{(4,1)},(0,1));fixtures.append(c)
    c=case('start_base_across',f,{(2,1)},(4,1));fixtures.append(c)
    c=case('empty_pending_return',f,{(4,1)},(4,1),{(4,1)},(3,1));fixtures.append(c)
    c=case('unreachable_negative',{(0,1),(2,1)},{(2,1)},(0,1));fixtures.append(c)
    order=[]
    for c in fixtures:
        save(H/'gates'/f'{c["name"]}.json',c)
        for m in ('PPCPP','P2_MULTI'):
            j=dict(id=f'gate__{c["name"]}__{m}',phase='gate',method=m,seed=20261021,budget=20,input=f'gates/{c["name"]}.json',seal='event_seal.json',expected='infeasible' if c['name']=='unreachable_negative' else 'complete');save(H/'jobs'/f'{j["id"]}.json',j);order.append(j)
    save(H/'gate_order.json',order)
def seal_event():
    assert read(H/'stage_A.json')['passed']
    prior=read(H/'prep_seal.json')['files']
    for p,h in prior.items():assert sha(p)==h,p
    order=[]
    for i,inp in enumerate(sorted((H/'inputs').glob('*.json'))):
        for rep,seed in enumerate((20261020,20261021,20261022)):
            methods=['PPCPP','P2_MULTI'] if (i+rep)%2==0 else ['P2_MULTI','PPCPP']
            for method in methods:
                j=dict(id=f'{inp.stem}__r{rep}__{method}',phase='formal',method=method,seed=seed,rep=rep,budget=20,input='inputs/'+inp.name,seal='event_seal.json');save(H/'jobs'/f'{j["id"]}.json',j);order.append(j)
    assert len(order)==432;save(H/'formal_order.json',order)
    files=dict(prior)
    for p in H.rglob('*'):
        if p.is_file():files[str(p.resolve())]=sha(p)
    save(H/'event_seal.json',dict(stage='after_histories_before_gates_and_event_solves',created_utc=time.time(),files=files))
    print('EVENT SEALED',len(files),flush=True)
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='worker':worker(sys.argv[2],sys.argv[3])
    elif mode=='seal_prep':seal_prep()
    elif mode=='setup_gates':setup_gates()
    elif mode=='seal_event':seal_event()
    elif mode in ('prep','gate','formal'):run_phase(mode)
