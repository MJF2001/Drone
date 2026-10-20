"""Bounded rerun of repaired OARP FULL on the identical ten saved states."""
import argparse,collections,datetime,hashlib,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
OLD=WORK/'OARP原生参照修订_v0.2_20261018';DEV=WORK/'DeepSeek_底层算法开发比较_20261018'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,x):
    p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def emit(e):
    e=dict(e,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (ROOT/'calls.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def prepare():
    assert not (ROOT/'protocol.json').exists()
    shutil.copyfile(OLD/'revision.py',ROOT/'kernel.py')
    shutil.copyfile(WORK/'OARP改进方向诊断_v0.1_20261018/independent.py',ROOT/'independent.py')
    shutil.copytree(OLD/'sources',ROOT/'sources',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (ROOT/'inputs').mkdir()
    protected={str(p):sha(p) for p in OLD.rglob('*') if p.is_file()}
    protected.update({str(p):sha(p) for p in (DEV/'runs/LONG120/results').glob('*.json')})
    jobs=[]
    for p in sorted((DEV/'sources/cases').glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8'));assert d['metadata']['split']=='development'
        shutil.copyfile(p,ROOT/'inputs'/p.name);protected[str(p)]=sha(p)
        for seed in (20261018,20261019):jobs.append({'plan_id':p.stem+'_'+str(seed),'case':p.stem,'seed':seed})
    assert len(jobs)==20
    save('protection.json',protected)
    dep=json.loads((OLD/'dependency_lock_after_execution.json').read_text(encoding='utf-8'))
    assert all(sha(p)==h for p,h in dep['files'].items());save('dependencies_before.json',dep)
    import independent
    save('preflight.json',independent.selftest())
    save('protocol.json',{'method':'OARP_FULL_SCENE','configuration':'repaired rank0 and full atomic strip tour; no native history recovered from P2',
        'planned':jobs,'full_call_limit':20,'SCIP_limit':40,'GLNS_limit':20,'soft_seconds':120,'hard_seconds':135,
        'GLNS':{'mode':'default','trials':5,'restarts':3},'input_semantics':'identical F/P/C/current/base/resource and old suffix to old comparison',
        'preload_solver_modules_before_entry':'matches old registry source_digest importing ranks/tour before public timer',
        'public_clock':'kernel.entry includes fallback, ranks, geometry, solve, reconstruction and final audit',
        'old_3_methods':'reuse their same-state LONG120 saved outcomes, identify this as separate batch',
        'holdout':False,'automatic_retries':False})
    save('freeze.json',{str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file()})
    print('FROZEN:20 OARP-only calls,120s soft/135s hard; zero new calls in preparation')
def worker(ident):
    assert all(sha(ROOT/p)==h for p,h in read('freeze.json').items())
    job=next(j for j in read('protocol.json')['planned'] if j['plan_id']==ident)
    attempt=str(uuid.uuid4());emit({'event':'start','attempt_id':attempt,'kind':'response','plan_id':ident,'freeze':sha(ROOT/'freeze.json')})
    try:
        import kernel as k
        k.emit=emit;k.ACTIVE=attempt
        # Old registry imports the numerical solver modules in source_digest
        # outside the public clock. Use the same preload convention here.
        bootstrap=time.perf_counter()
        import glns,pyscipopt
        from oarp_replan import ranks,tour
        k.install_trace();bootstrap=time.perf_counter()-bootstrap
        d=read('inputs/'+job['case']+'.json')
        req={'case_id':job['case'],'F':d['free'],'P':d['metadata']['published_targets'],'C':d['covered'],
            'current':d['current'],'base':d['base'],'resource':d['distance_budget'],'seed':job['seed'],
            'old_route':d['old_route'],'old_suffix':d['old_route']}
        result=k.entry(req,'RANK0',None,[],attempt,seconds=120)
        result.update(plan_id=ident,attempt_id=attempt,method_label='OARP_FULL_SCENE',input_sha256=sha(ROOT/'inputs'/f"{job['case']}.json"),
            bootstrap_seconds=bootstrap,imports={'rank':ranks.__file__,'tour':tour.__file__,'glns':glns.__file__},
            core_complete=bool(result['flags']['core_candidate_valid'] and result['core_detail'].get('core_natural') and result['flags']['call_within_budget']))
        save('results/'+ident+'.json',result)
        emit({'event':'end','attempt_id':attempt,'kind':'response','plan_id':ident,'status':result['status'],'result_sha256':sha(ROOT/'results'/f'{ident}.json')})
        assert 'error' not in result['core_detail'],result['core_detail']
    except BaseException as exc:
        emit({'event':'failure','attempt_id':attempt,'kind':'supervisor_error','plan_id':ident,'error':repr(exc)});raise
def run():
    for j in read('protocol.json')['planned']:
        name=j['plan_id']
        assert not (ROOT/'results'/f'{name}.json').exists(),'no repeat or overwrite'
        if (ROOT/'calls.jsonl').exists():
            assert not any(json.loads(s).get('plan_id')==name for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines())
        began=time.perf_counter()
        with (ROOT/(name+'.console.txt')).open('w',encoding='utf-8') as f:
            try:p=subprocess.run([sys.executable,'-B','-X','utf8',__file__,'worker','--id',name],stdout=f,stderr=subprocess.STDOUT,timeout=135)
            except subprocess.TimeoutExpired:
                save('watchdog/'+name+'.json',{'killed':True,'plan_id':name,'core_end_not_fabricated':True});raise
        save('supervisor/'+name+'.json',{'plan_id':name,'exit_code':p.returncode,'wall_seconds':time.perf_counter()-began})
        if p.returncode:raise SystemExit('STOP '+name)
        r=read('results/'+name+'.json');print(name,r['audit']['steps'],round(r['public_seconds'],3),'core_complete',r['core_complete'],'source',r['source'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run','worker']);p.add_argument('--id');a=p.parse_args()
    {'prepare':prepare,'run':run,'worker':lambda:worker(a.id)}[a.mode]()
