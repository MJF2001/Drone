"""Frozen bounded OARP diagnostic. All writes and calls remain in this folder."""
import argparse,collections,copy,datetime,hashlib,importlib,json,math,os
from pathlib import Path
import shutil,subprocess,sys,time,uuid
import independent as ind
ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'OARP原生参照修订_v0.2_20261018'
DEPS=ROOT.parent/'DeepSeek_底层算法开发比较_20261018/sources/reference_tree/研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps'
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,v):
    p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def emit(e):
    e=dict(e,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (ROOT/'calls.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(e,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def inflate(cells):return {(x+dx,y+dy) for x,y in cells for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1))}
def initial(name,L,W):
    P={(x,y) for x in range(L) for y in range(W)};F=inflate(P)|{(-2,0),(-1,0)}
    return {'case_id':name,'P':sorted(P),'F':sorted(F),'C':[],'current':[-2,0],'base':[-2,0],
            'resource':10000,'seed':20261018,'old_route':[],'old_suffix':[],'length':L,'width':W}

def kernel():
    import kernel as k
    k.emit=emit
    return k

def event(k,prep_result,kind):
    before=prep_result['request'];plan=prep_result['core_plan'];P=set(map(tuple,before['P']));F=set(map(tuple,before['F']))
    ex=k.reconstruct_execution(plan,P,math.ceil(len(P)/2));C=set(ex['C']);current=tuple(ex['current'])
    reference=k.normalize(plan,C);L,W=before['length'],before['width'];added=set();blocked=set()
    if kind=='straight':added={(x,y) for x in range(L,L+2) for y in range(W)}
    if kind=='corner_obstacle':
        added={(x,y) for x in range(L,L+2) for y in range(W)}|{(x,y) for x in range(L,L+4) for y in range(W,W+2)}
    if kind in ('obstacle','corner_obstacle'):
        candidates=sorted(P-C-{current,tuple(before['base'])},key=lambda p:(p[1],p[0]))
        for p in candidates:
            newF=(F|inflate(added))-{p};g=ind.Geometry({'F':sorted(newF)})
            try:
                g.path(current,tuple(before['base']))
                if ((P-C)|added)-{p}<=set(g.rows[current]):blocked={p};break
            except AssertionError:continue
        assert blocked,'predefined event has no feasible obstacle'
    newP=P|added;newF=(F|inflate(added))-blocked
    req={'case_id':before['case_id']+'_'+kind,'P':sorted(newP),'F':sorted(newF),'C':sorted(C),
         'current':list(current),'base':before['base'],'resource':before['resource']-ex['steps'],
         'seed':20261018,'old_route':plan['route'],'old_suffix':plan['route'][ex['index']:]}
    return {'case_id':req['case_id'],'request':req,'reference':reference,'execution':ex,
            'event':{'kind':kind,'added':sorted(added),'blocked':sorted(blocked)},
            'preparation_plan_id':prep_result['plan_id'],'preparation_attempt_id':prep_result['attempt_id'],
            'preparation_sha256':sha(ROOT/'results'/f"{prep_result['plan_id']}.json")}

def prepare():
    assert not (ROOT/'freeze.json').exists() and not (ROOT/'calls.jsonl').exists()
    assert all(sha(PREVIOUS/p)==h for p,h in json.loads((PREVIOUS/'manifest.json').read_text(encoding='utf-8')).items())
    save('previous_protection.json',{str(p.relative_to(PREVIOUS)):sha(p) for p in PREVIOUS.rglob('*') if p.is_file()})
    shutil.copyfile(PREVIOUS/'revision.py',ROOT/'kernel.py')
    shutil.copytree(PREVIOUS/'sources',ROOT/'sources',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Make snapshot directories explicitly, then copy all relevant saved inputs.
    for directory in ('events','results'):
        (ROOT/'saved_micro'/directory).mkdir(parents=True,exist_ok=True)
        for p in (PREVIOUS/directory).glob('N*.json'):shutil.copyfile(p,ROOT/'saved_micro'/directory/p.name)
    specs=[('rect6x3',6,3),('rect12x4',12,4),('rect24x5',24,5)]
    jobs=[]
    for name,L,W in specs:
        save(f'inputs/{name}.json',initial(name,L,W));jobs.append({'plan_id':'prep_'+name,'kind':'preparation','case':name,'arm':'FULL','seed':20261018})
    for scale_index,(name,L,W) in enumerate(specs):
        for event_index,kind in enumerate(('unchanged','obstacle','straight','corner_obstacle')):
            for seed_index,seed in enumerate((20261018,20261019)):
                order=('FULL','ATOMIC','PACKED');shift=(scale_index+event_index+seed_index)%3
                for arm in order[shift:]+order[:shift]:
                    jobs.append({'plan_id':f'{name}_{kind}_{seed}_{arm}','kind':'response','case':name+'_'+kind,
                                 'arm':arm,'seed':seed})
    save('protocol.json',{'planned':jobs,'full_entry_limit':75,'SCIP_limit':180,'GLNS_limit':90,
        'soft_seconds':30,'hard_seconds':40,'GLNS':{'mode':'default','trials':5,'restarts':3},
        'method_definition':{'FULL':'rank0 + individual ranks','ATOMIC':'model2 cap=2Q + individual ranks',
                             'PACKED':'model2 cap=2Q + native old packets'},
        'matrix_design':'3 fixed generated rectangles x 4 fixed events x 2 response seeds x 3 arms; 3 native preparations',
        'warm_dependency_loading_outside_public_entry_reported_separately':True,
        'arm_order':'cyclic shift (scale_index+event_index+seed_index)%3',
        'runtime_phase_measurements_are_inclusive_of_actual_work_not_free_shared_rank':True,
        'holdout':False,'prior_ten_road_maps_used':False,'no_automatic_retry':True,
        'micro_exact':'7 global coverage BFS, 21 packed/atomic pairs, all minimum-rank ties',
        'new_exact':'one fixed-structure exact check for each saved core with <=12 groups; no GLNS rerun'})
    save('copy_provenance.json',{'kernel.py':{'source':str(PREVIOUS/'revision.py'),'sha256':sha(ROOT/'kernel.py')},
         'frozen_OARP_package':{'source':str(PREVIOUS/'sources'),'unchanged':True},'saved_micro_source':str(PREVIOUS)})
    # Copy previous environment snapshot then verify it BEFORE the first call.
    dep=json.loads((PREVIOUS/'dependency_lock_after_execution.json').read_text(encoding='utf-8'))
    assert all(sha(p)==h for p,h in dep['files'].items())
    dep['snapshot_timing']='verified before this diagnostic first solver call; prior source snapshot was post-execution'
    save('dependency_lock_before_execution.json',dep)
    k=kernel();test=ind.selftest()
    old=read('saved_micro/events/N1.json');p=old['initial_plan']
    # Pure normalization: no event mutation may remove a blocked old target.
    refs=k.normalize(p,old['request']['C']);assert json.loads(json.dumps(refs))==old['reference']
    # Wrong-axis, missing goals, and malformed packets must be rejected.
    bad=copy.deepcopy(p);bad['strips'][0]['axis']='V'
    try:ind.check_strips(bad,set(map(tuple,p['service_targets'])))
    except AssertionError:pass
    else:raise AssertionError('wrong axis accepted')
    test.update(reference_immutable=True,wrong_axis_negative=True,solver_calls=0)
    save('preflight.json',test)
    freeze={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and
            (p.suffix=='.py' or 'inputs' in p.parts or 'saved_micro' in p.parts or p.name in
             ('protocol.json','本轮方案.md','dependency_lock_before_execution.json','copy_provenance.json','previous_protection.json','preflight.json'))}
    save('freeze.json',freeze);print('FROZEN',len(jobs),'complete entries; preflight has zero solver calls')

def worker(planid):
    assert all(sha(ROOT/p)==h for p,h in read('freeze.json').items())
    job=next(j for j in read('protocol.json')['planned'] if j['plan_id']==planid)
    ident=str(uuid.uuid4());emit({'event':'start','attempt_id':ident,'kind':job['kind'],'plan_id':planid,'freeze_sha256':sha(ROOT/'freeze.json')})
    bootstrap=time.perf_counter();k=kernel();sys.path.insert(0,str(DEPS))
    import glns,pyscipopt
    from oarp_replan import ranks,tour
    k.ACTIVE=ident;k.install_trace();phases=collections.defaultdict(float);depth=0
    original_rank=ranks.rank_replan
    def timed_rank(*a,**kw):
        nonlocal depth
        top=depth==0;began=time.perf_counter();depth+=1
        try:return original_rank(*a,**kw)
        finally:
            depth-=1
            if top:phases['rank']+=time.perf_counter()-began
    ranks.rank_replan=timed_rank
    def timed(owner,name,label):
        original=getattr(owner,name)
        def wrapper(*a,**kw):
            t=time.perf_counter()
            try:return original(*a,**kw)
            finally:phases[label]+=time.perf_counter()-t
        setattr(owner,name,wrapper)
    timed(tour,'gtsp_instance','geometry_matrix');timed(glns,'solve','GLNS');timed(k,'annotate','rebuild')
    orig_packets=k.packets
    def changed_packets(rr,frags,route,free):
        t=time.perf_counter()
        try:return orig_packets(rr,[] if job['arm']=='ATOMIC' else frags,route,free)
        finally:phases['packets']+=time.perf_counter()-t
    k.packets=changed_packets
    def audit(req,route):
        t=time.perf_counter()
        try:return k.audit(req,route)
        finally:phases['audit']+=time.perf_counter()-t
    bootstrap_seconds=time.perf_counter()-bootstrap
    try:
        if job['kind']=='preparation':req=read('inputs/'+job['case']+'.json');reference=[];event_sha=None
        else:
            case=read('events/'+job['case']+'.json');req=copy.deepcopy(case['request']);req['seed']=job['seed']
            reference=case['reference'];event_sha=sha(ROOT/'events'/f"{job['case']}.json")
        method='RANK0' if job['arm']=='FULL' else 'REPLAN2';cap=None if method=='RANK0' else 2*len(ind.targets(req))
        result=k.entry(req,method,cap,reference,ident,seconds=30,auditor=audit)
        result.update(plan_id=planid,attempt_id=ident,kind=job['kind'],arm=job['arm'],event_sha256=event_sha,
            bootstrap_seconds=bootstrap_seconds,phase_seconds=dict(phases),
            imported_modules={'glns':glns.__file__,'pyscipopt':pyscipopt.__file__,'rank':ranks.__file__,'tour':tour.__file__},
            core_complete=bool(result['flags']['core_candidate_valid'] and result['core_detail'].get('core_natural') and result['flags']['call_within_budget']))
        assert not ind.audit(req,result['route']) if result['flags']['route_valid'] else True
        if result['core_plan']:ind.check_strips(result['core_plan'],ind.targets(req))
        assert 'error' not in result['core_detail'],result['core_detail']
        if job['kind']=='preparation':assert result['core_complete'],'initial core did not naturally complete'
        save('results/'+planid+'.json',result)
        emit({'event':'end','attempt_id':ident,'kind':job['kind'],'plan_id':planid,'status':result['status'],
              'result_sha256':sha(ROOT/'results'/f'{planid}.json')})
    except BaseException as exc:
        emit({'event':'end','attempt_id':ident,'kind':job['kind'],'plan_id':planid,'error':repr(exc)});raise

def run():
    for job in read('protocol.json')['planned']:
        name=job['plan_id']
        if (ROOT/'results'/f'{name}.json').exists():continue
        if job['kind']=='response' and not (ROOT/'events'/f"{job['case']}.json").exists():
            k=kernel();prepname=job['case'].split('_')[0]
            prep=read('results/prep_'+prepname+'.json');assert prep['core_complete']
            for kind in ('unchanged','obstacle','straight','corner_obstacle'):
                case=event(k,prep,kind);save('events/'+case['case_id']+'.json',case)
        if (ROOT/'calls.jsonl').exists():
            ledger=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
            assert not any(e.get('plan_id')==name and e['event']=='start' for e in ledger),'previous attempt; automatic retry forbidden'
        began=time.perf_counter()
        with (ROOT/(name+'.console.txt')).open('w',encoding='utf-8') as f:
            try:process=subprocess.run([sys.executable,'-B','-X','utf8',__file__,'worker','--plan-id',name],stdout=f,stderr=subprocess.STDOUT,timeout=40)
            except subprocess.TimeoutExpired:
                save('watchdog/'+name+'.json',{'killed':True,'plan_id':name,'no_end_fabricated':True});raise
        save('supervisor/'+name+'.json',{'plan_id':name,'returncode':process.returncode,'process_wall_seconds':time.perf_counter()-began})
        if process.returncode:raise SystemExit('STOP: failed '+name)
        result=read('results/'+name+'.json');print(name,result['audit']['steps'],result['core_complete'],round(result['public_seconds'],4),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','run','worker']);ap.add_argument('--plan-id');args=ap.parse_args()
    {'prepare':prepare,'run':run,'worker':lambda:worker(args.plan_id)}[args.mode]()
