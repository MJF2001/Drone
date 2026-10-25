"""Frozen 60-call independent OARP FULL comparison. No retries or fallback."""
import argparse,datetime,hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,obj):
    p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def emit(event):
    event=dict(event,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (ROOT/'calls.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def prepare():
    assert not (ROOT/'protocol.json').exists()
    assert all(sha(p)==h for p,h in read('protection.json').items())
    assert all(sha(p)==h for p,h in read('dependencies_before.json')['files'].items())
    assert all(sha(ROOT/p)==h for p,h in read('sources_before.json').items())
    import independent
    save('preflight.json',independent.selftest())
    jobs=[]
    for p in sorted((ROOT/'inputs').glob('*.json')):
        d=read(p.relative_to(ROOT));assert d['metadata']['split']=='development'
        for budget in (1,20,120):
            for seed in (20261018,20261019):
                jobs.append({'plan_id':p.stem+'_'+str(seed)+'_B'+str(budget),'case':p.stem,'budget':budget,'seed':seed,'input_sha256':sha(p)})
    assert len(jobs)==60
    save('protocol.json',{'method':'OARP_FULL_INDEPENDENT_SCENE','planned':jobs,'full_call_limit':60,'SCIP_limit':120,'GLNS_limit':60,
        'configuration':'rank variant 0; full atomic-strip GTSP; unchanged rank/tour source and solver parameters',
        'candidate_policy':'core only; no greedy; no old-route candidate; no history passed to entry',
        'geometry':'fresh empty cache per call; original BFS/path implementation unchanged',
        'public_clock':'validation + rank partition + blocks + connection matrix + GLNS + reconstruction + candidate audit + final audit',
        'preload':'numerical dependencies outside public timer, same convention as previous comparison; separate bootstrap and supervisor times saved',
        'GLNS':{'mode':'default','trials':5,'restarts':3},'soft_seconds':[1,20,120],'hard_seconds':'job budget + 15',
        'same_cases_and_seeds_as_previous':True,'development_only':True,'holdout':False,'automatic_retries':False,
        'other_methods':'reuse historical same-state P2/TREE/PPCPP data; do not attribute fallback outputs to their core',
        'scope':'independent FULL scene adaptation, not complete original OARP-Replan controller reproduction',
        'regression_tests':'8 mocked entry tests; before: 8 fail; after: 8 pass; zero actual planner calls'})
    save('freeze.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file()})
    print('FROZEN:60 calls, 3 budgets, no retries. Preparation planner calls:0',flush=True)
def worker(ident):
    assert all(sha(ROOT/p)==h for p,h in read('freeze.json').items())
    job=next(j for j in read('protocol.json')['planned'] if j['plan_id']==ident)
    attempt=str(uuid.uuid4());emit({'event':'start','kind':'response','attempt_id':attempt,'plan_id':ident,'freeze_sha256':sha(ROOT/'freeze.json')})
    try:
        import kernel as k
        k.emit=emit;k.ACTIVE=attempt
        began=time.perf_counter()
        import glns,pyscipopt
        from oarp_replan import ranks,tour
        k.install_trace();bootstrap=time.perf_counter()-began
        d=read('inputs/'+job['case']+'.json')
        req={'case_id':job['case'],'F':d['free'],'P':d['metadata']['published_targets'],'C':d['covered'],
             'current':d['current'],'base':d['base'],'resource':d['distance_budget'],'seed':job['seed']}
        result=k.entry(req,'RANK0',None,[],attempt,seconds=job['budget'])
        result.update(plan_id=ident,attempt_id=attempt,method_label='OARP_FULL_INDEPENDENT_SCENE',soft_seconds=job['budget'],
            input_sha256=job['input_sha256'],bootstrap_seconds=bootstrap,
            imports={'rank':ranks.__file__,'tour':tour.__file__,'glns':glns.__file__},
            core_complete=bool(result['flags']['core_candidate_valid'] and result['core_detail'].get('core_natural') and result['flags']['call_within_budget']))
        save('results/'+ident+'.json',result)
        emit({'event':'end','kind':'response','attempt_id':attempt,'plan_id':ident,'status':result['status'],'result_sha256':sha(ROOT/'results'/f'{ident}.json')})
        assert 'error' not in result['core_detail'],result['core_detail']
    except BaseException as exc:
        emit({'event':'failure','kind':'worker_error','attempt_id':attempt,'plan_id':ident,'error':repr(exc)});raise
def run():
    assert not (ROOT/'manifest.json').exists()
    for job in read('protocol.json')['planned']:
        name=job['plan_id'];result_path=ROOT/'results'/f'{name}.json'
        assert not result_path.exists(),'no overwrite or retry'
        if (ROOT/'calls.jsonl').exists():
            assert not any(json.loads(line).get('plan_id')==name for line in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines())
        began=time.perf_counter()
        with (ROOT/(name+'.console.txt')).open('x',encoding='utf-8') as out:
            try:
                process=subprocess.run([sys.executable,'-B','-X','utf8',__file__,'worker','--id',name],stdout=out,stderr=subprocess.STDOUT,timeout=job['budget']+15)
            except subprocess.TimeoutExpired:
                save('watchdog/'+name+'.json',{'plan_id':name,'killed':True,'wall_seconds':time.perf_counter()-began});raise
        save('supervisor/'+name+'.json',{'plan_id':name,'exit_code':process.returncode,'wall_seconds':time.perf_counter()-began})
        if process.returncode:raise SystemExit('STOP '+name)
        result=read('results/'+name+'.json')
        print(name,'steps',result['audit']['steps'],'seconds',round(result['public_seconds'],4),'timely',result['flags']['within_budget'],'core_complete',result['core_complete'],flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','worker','run']);parser.add_argument('--id');args=parser.parse_args()
    {'prepare':prepare,'worker':lambda:worker(args.id),'run':run}[args.mode]()
