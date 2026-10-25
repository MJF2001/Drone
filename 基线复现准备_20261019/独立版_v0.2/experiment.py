"""Gate, freeze, then serial 120-call comparison; immutable old files."""
import sys,json,hashlib,subprocess,time,os,traceback,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUN=HERE/'comparison'
sys.path.insert(0,str(ROOT))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False)
def worker(j,dest):
    try:
        start=time.perf_counter();import ppcpp
        from model import Snapshot
        c=read(j['case']);s=Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),(),0,c['distance_budget'])
        if j['method']=='PPCPP':
            bootstrap=time.perf_counter()-start
            raw=ppcpp.solve(s,set(map(tuple,c['metadata']['initial_targets'])),j['budget'],j['seed'],tuple(j['predator']),tuple(j['previous']) if j['previous'] is not None else None)
            route=raw['route'];seconds=raw['seconds'];timely=raw['status']=='core_complete'
        else:
            for name in list(sys.modules):
                if name=='oarp_replan' or name.startswith('oarp_replan.'):del sys.modules[name]
            sys.path.insert(0,str(HERE/'oarp_remote'));import kernel
            kernel.ROOT=dest.parent/'oarp_traces'/j['run_id'];kernel.ROOT.mkdir(parents=True,exist_ok=False)
            import glns,pyscipopt
            from oarp_replan import ranks,tour
            assert Path(ranks.__file__).resolve().is_relative_to(HERE/'oarp_remote/sources')
            kernel.install_trace();bootstrap=time.perf_counter()-start
            req=dict(F=c['free'],P=c['metadata']['published_targets'],C=c['covered'],current=c['current'],base=c['base'],resource=c['distance_budget'],seed=j['seed'])
            raw=kernel.entry(req,'RANK0',None,[],j['run_id'],seconds=j['budget']);route=raw['route'];seconds=raw['public_seconds'];timely=raw['flags']['within_budget']
        write(dest,dict(worker_status='returned',job=j,input_sha256=sha(j['case']),bootstrap_seconds=bootstrap,route=route,seconds=seconds,timely=timely,raw=raw));return 0
    except BaseException:write(dest,dict(worker_status='exception',job=j,traceback=traceback.format_exc()));return 1
def history():
    a=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/continuous_history_diagnostics'
    old={e['map_id']:e for e in read(a/'preparation_verification_v0.1_20261016/checks.json')};out=[]
    for p in sorted((HERE/'oarp_remote/inputs').glob('*.json')):
        c=read(p);mid=p.stem;e=old[mid];h=e['history'];initpath=a/'preflight_v0.1_20261016/initial_cases'/(mid+'.json');initial=read(initpath)
        assert c['metadata']['split']=='development'
        for key in ('current','covered','old_route'):assert c[key]==h[key],(mid,key)
        assert c['distance_budget']==h['remaining_budget']
        prefix=list(map(tuple,h['executed_route']));targets=set(map(tuple,initial['targets']))
        assert prefix[-1]==tuple(c['current']) and set(prefix)&targets==set(map(tuple,c['covered']))
        assert len(set(prefix[:-1])&targets)<(len(targets)+1)//2<=len(set(prefix)&targets)
        assert set(map(tuple,c['free']))<=set(map(tuple,initial['free']))
        published=set(map(tuple,c['metadata']['published_targets']));free=set(map(tuple,c['free']));covered=set(map(tuple,c['covered']))
        assert set(map(tuple,c['targets']))==published&free
        assert set(map(tuple,c['metadata']['deferred_targets']))==published-free-covered
        pred=(min(x for x,y in initial['free'])-1,initial['base'][1]);prev=prefix[-2] if len(prefix)>1 else None
        out.append(dict(map_id=mid,case=str(p),input_sha256=sha(p),initial_input_sha256=sha(initpath),initial_input=str(initpath),predator=pred,previous=prev,history_source_sha256=sha(a/'preparation_verification_v0.1_20261016/checks.json')))
    assert len(out)==10;return out
def verify_rows(folder,jobs):
    from audit_ppcpp import audit
    from types import SimpleNamespace
    import importlib.util
    spec=importlib.util.spec_from_file_location('_oarp_independent_audit',HERE/'oarp_remote/independent.py');aud=importlib.util.module_from_spec(spec);spec.loader.exec_module(aud)
    checks=[]
    for j in jobs:
        p=folder/(j['run_id']+'.json')
        if not p.exists():checks.append(dict(j,valid=False,timely=False));continue
        r=read(p);assert r['job']==json.loads(json.dumps(j))
        if r['worker_status']!='returned':checks.append(dict(j,valid=False,timely=False));continue
        c=read(j['case']);assert sha(j['case'])==r['input_sha256']==j['input_sha256']
        req=dict(F=c['free'],P=c['metadata']['published_targets'],C=c['covered'],current=c['current'],base=c['base'],resource=c['distance_budget'])
        valid=bool(r['route']) and not aud.audit(req,r['route'])
        if valid and j['method']=='PPCPP':audit(c,r['raw']);assert r['raw']['predator']==list(j['predator']) and r['raw']['initial_previous']==(list(j['previous']) if j['previous'] is not None else None)
        if valid and j['method']=='OARP':
            assert r['raw']['source']=='core' and not r['raw']['flags']['fallback_selected'];aud.check_strips(r['raw']['core_plan'],aud.targets(req))
        if r['timely']:assert valid and r['seconds']<j['budget']
        checks.append(dict(run_id=j['run_id'],method=j['method'],map_id=j['map_id'],budget=j['budget'],seed=j['seed'],valid=valid,timely=bool(r['timely']) and valid,steps=len(r['route'])-1 if valid else None,seconds=r['seconds'],bootstrap_seconds=r['bootstrap_seconds']))
    return checks
def main():
    assert not (RUN/'protocol.json').exists();families=history()
    # Preserve original source downloads, then freeze sources/inputs before any developer calls.
    for e in read(HERE/'source_manifest.json')['files']:assert sha(HERE/e['path'])==e['sha256']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    test=subprocess.run([sys.executable,'-B','-X','utf8','-m','unittest','discover','-s',str(HERE),'-p','test_gates.py','-v'],cwd=ROOT,env=env,capture_output=True,text=True)
    assert test.returncode==0,test.stderr
    RUN.mkdir(exist_ok=True)
    if not (RUN/'gate_tests.log').exists():
        (RUN/'gate_tests.log').write_text(test.stdout+test.stderr,encoding='utf-8');write(RUN/'history_contracts.json',families)
    else:
        assert read(RUN/'history_contracts.json')==json.loads(json.dumps(families))
        (RUN/'post_import_fix_gate_tests.log').write_text(test.stdout+test.stderr,encoding='utf-8')
    jobs=[]
    for i,e in enumerate(families):
        for k,seed in enumerate((20261018,20261019)):
            for b in ((1,20,120) if (i+k)%2==0 else (120,20,1)):
                for m in (('PPCPP','OARP') if (i+k)%2==0 else ('OARP','PPCPP')):
                    jobs.append(dict(e,run_id=f'c{i:02d}_s{seed}_b{b}_{m}',method=m,budget=b,seed=seed))
    assert len(jobs)==120
    def execute(j,folder):
        dest=folder/(j['run_id']+'.json');folder.mkdir(exist_ok=True);start=time.perf_counter()
        with (folder/(j['run_id']+'.log')).open('x',encoding='utf-8') as f:
            try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',json.dumps(j),str(dest)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=j['budget']+15).returncode;timeout=False
            except subprocess.TimeoutExpired:code=None;timeout=True
        return dict(run_id=j['run_id'],code=code,watchdog=timeout,wall_seconds=time.perf_counter()-start)
    pre=[dict(j,run_id='preflight_'+j['run_id']) for j in jobs if j['map_id']=='small_g2_development' and j['seed']==20261018 and j['budget']==20]
    assert len(pre)==2
    if (RUN/'preflight_verification.json').exists():
        gate=verify_rows(RUN/'preflight',pre)
        write(RUN/'pre_freeze_repair.json',dict(reason='Parent process portable_frozen import path missing after two successful preflight calls; no formal calls occurred. Added ROOT to sys.path; reused successful preflight, no repeats.',source_before_sha256=sha(HERE/'experiment_before_import_fix.py.txt'),reused_preflight_calls=2,new_preflight_calls=0))
    else:
        pre_rows=[execute(j,RUN/'preflight') for j in pre];gate=verify_rows(RUN/'preflight',pre);write(RUN/'preflight_verification.json',dict(execution=pre_rows,checks=gate))
    assert all(v['timely'] for v in gate)
    paths=[p for p in HERE.rglob('*') if p.is_file() and RUN not in p.parents]
    import portable_frozen
    paths+=list(portable_frozen.FROZEN.rglob('*.py'))+[portable_frozen.FROZEN/'runtime_profile.json']
    paths+=list((portable_frozen.ALGO/'.deps').rglob('*.pyd'))+list((portable_frozen.ALGO/'.deps').rglob('*.dll'))
    paths+=[ROOT/'portable_frozen.py',ROOT/'基线复现准备_20261019/ppcpp_independent.py',HERE.parents[0]/'ppcpp_independent.py']
    paths=[p for p in paths if p.is_file()]
    protected={str(p):sha(p) for p in paths};write(RUN/'protocol.json',dict(jobs=jobs,protected_hashes=protected,preflight_calls=2,formal_calls=120,version='v0.2',initial_planning_calls=0,weights=[2,.5],predator_policy='min initial known flight-domain x minus one, initial base y; fixed across events/budgets/seeds',history_policy='actual prefix heading and covered ledger; old tail not used as candidate or decision input',clock='complete entry includes validation/geometry/search/trace/final audit; preload separate',attempts='no automatic retry; failures retained',holdout_used=False))
    rows=[]
    with (RUN/'execution.jsonl').open('x',encoding='utf-8') as ledger:
        for i,j in enumerate(jobs):
            r=execute(j,RUN/'runs');rows.append(r);ledger.write(json.dumps(r)+'\n');ledger.flush()
            if (i+1)%20==0:print('completed',i+1,'of 120',flush=True)
    assert all(sha(Path(p))==h for p,h in protected.items())
    checks=verify_rows(RUN/'runs',jobs);write(RUN/'route_decision_checks.json',checks)
    pairs=[]
    for b in (1,20,120):
        vals=[];failed=[]
        for mid in sorted({j['map_id'] for j in jobs}):
            for seed in (20261018,20261019):
                a=next(v for v in checks if (v.get('map_id'),v.get('budget'),v.get('seed'),v.get('method'))==(mid,b,seed,'PPCPP'));o=next(v for v in checks if (v.get('map_id'),v.get('budget'),v.get('seed'),v.get('method'))==(mid,b,seed,'OARP'))
                if a['timely'] and o['timely']:vals.append(dict(map_id=mid,seed=seed,PPCPP=a['steps'],OARP=o['steps'],difference=a['steps']-o['steps'],relative=a['steps']/o['steps']-1))
                else:failed.append(dict(map_id=mid,seed=seed,PPCPP_timely=a['timely'],OARP_timely=o['timely']))
        pairs.append(dict(budget=b,paired=len(vals),unpaired=failed,shorter=sum(v['difference']<0 for v in vals),equal=sum(v['difference']==0 for v in vals),longer=sum(v['difference']>0 for v in vals),mean_relative=statistics.mean(v['relative'] for v in vals) if vals else None,per_pair=vals))
    write(RUN/'paired_summary.json',pairs)
    stats=[]
    for b in (1,20,120):
        for m in ('PPCPP','OARP'):
            rr=[r for r in checks if r.get('budget')==b and r.get('method')==m];tt=[r for r in rr if r['timely']]
            stats.append(dict(budget=b,method=m,valid=sum(r['valid'] for r in rr),timely=len(tt),sum_steps_timely=sum(r['steps'] for r in tt),total_seconds=sum(r.get('seconds',0) for r in rr),overruns=sum(r.get('seconds',0)>b+.01 for r in rr)))
    write(RUN/'method_summary.json',stats);write(RUN/'completion.json',dict(formal_calls=120,preflight_calls=2,valid=sum(v['valid'] for v in checks),timely=sum(v['timely'] for v in checks),exceptions=sum(r['code'] not in (0,None) for r in rows),watchdogs=sum(r['watchdog'] for r in rows),protected_unchanged=True,holdout_used=False))
    write(RUN/'sha256.json',{str(p.relative_to(RUN)):sha(p) for p in RUN.rglob('*') if p.is_file()});print(json.dumps(stats,ensure_ascii=False),flush=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(json.loads(sys.argv[2]),Path(sys.argv[3])))
    main()
