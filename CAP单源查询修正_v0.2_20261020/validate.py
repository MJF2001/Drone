import json,sys,hashlib,subprocess,time,unittest
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'TRACE_CAP适配复现_20261020'
sys.path.insert(0,str(HERE/'runtime'))
from planners import solve
from primitives import Metric,Deadline,Unreachable
from audit import audit,distance
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def semantic(r):return {k:v for k,v in r.items() if k not in ('seconds','metric_counts')}
def main():
    assert not (HERE/'protocol.json').exists()
    sources={str(p.relative_to(HERE)):sha(p) for p in [*sorted((HERE/'runtime').glob('*.py')),HERE/'validate.py',HERE/'audit.py',HERE/'worker.py',HERE/'test_core.py']}
    jobs=[]
    for kind in ('micro','road'):
        for job in read(OLD/(kind+'_evidence/protocol.json'))['jobs']:
            if job['method']=='CAP':jobs.append(dict(kind=kind,**job))
    save(HERE/'protocol.json',dict(version='CAP_PUBLIC_RESTART_v0.2',sources=sources,jobs=jobs,order='unit, row contracts, all deadline stages, micro52, then road40',comparison='exclude only seconds and metric_counts; every other field identical',watchdog=35,stop='first exception, mismatch or unexpected status; no overwrite'))
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'test_core.py'),'-v'],capture_output=True,text=True)
    (HERE/'unit.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0
    f={(x,y) for x in range(4) for y in range(3)}-{(1,1)};goals=[(3,2),(0,0),(3,2),(2,1)]
    m=Metric(f);row=m.distances_from((0,0),goals);assert row==[distance(f,(0,0),p) for p in goals];assert m.rows==1
    assert row==Metric(f).matrix([(0,0)]+goals)[0][1:]
    assert Metric(f).distances_from((0,0),[])==[]
    try:Metric({(0,0),(2,0)}).distances_from((0,0),[(2,0)]);raise AssertionError('accepted disconnected')
    except Unreachable:pass
    try:Metric(f).distances_from((0,0),[(99,99)]);raise AssertionError('accepted invalid terminal')
    except Unreachable:pass
    save(HERE/'row_checks.json',dict(independent_bfs=True,old_matrix_equal=True,duplicates_and_start=True,empty=True,unreachable=True,invalid=True,rows=1))
    c=read(OLD/'deadline_evidence/input.json');seen=[]
    r=solve(c,'CAP',1,clock=lambda:0,checkpoint_hook=lambda s:seen.append(s));audit(c,r);assert r['status']=='complete'
    assert 'single_source' in seen
    gates=[]
    for stage in sorted(set(seen)):
        for relation,value in [('before',1-1e-6),('equal',1),('after',1+1e-6)]:
            state={'time':0,'hit':False}
            def hook(s):
                if s==stage and not state['hit']:state.update(time=value,hit=True)
            r=solve(c,'CAP',1,clock=lambda:state['time'],checkpoint_hook=hook);audit(c,r)
            assert state['hit'] and r['status']==('complete' if relation=='before' else 'deadline')
            name=stage+'__'+relation;save(HERE/'deadline'/ (name+'.json'),r);gates.append(dict(name=name,status=r['status']))
    save(HERE/'deadline_checks.json',gates)
    checks=[]
    for job in jobs:
        assert sha(Path(job['input']))==job['input_sha256']
        for p,h in sources.items():assert sha(HERE/p)==h
        jp=HERE/'jobs'/(job['run_id']+'.json');rp=HERE/job['kind']/(job['run_id']+'.json');save(jp,job);rp.parent.mkdir(exist_ok=True)
        begin=time.perf_counter();proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(jp),str(rp)],capture_output=True,text=True,timeout=35)
        assert proc.returncode==0,proc.stderr
        r=read(rp);old=read(OLD/(job['kind']+'_evidence/results')/(job['run_id']+'.json'));audit(read(Path(job['input'])),r)
        assert semantic(r)==semantic(old),job['run_id']
        if r['status']=='complete':assert r['seconds']<job['budget']
        assert r['metric_counts']['distance_rows']<=old['metric_counts']['distance_rows']
        checks.append(dict(run_id=job['run_id'],kind=job['kind'],status=r['status'],semantic_equal=True,rows_old=old['metric_counts']['distance_rows'],rows_new=r['metric_counts']['distance_rows'],seconds=r['seconds'],dispatch_read_audit_wall=time.perf_counter()-begin,result_sha256=sha(rp)))
        save(HERE/'checks.json',checks);print(job['kind'],job['run_id'],r['status'],'EQUAL',flush=True)
    save(HERE/'summary.json',dict(unit_tests=27,row_contract_checks=6,deadline_tests=len(gates),deadline_stage_discovery_calls=1,by_kind={k:dict(Counter(x['status'] for x in checks if x['kind']==k)) for k in ('micro','road')},semantic_pairs=len(checks),distance_rows_old=sum(x['rows_old'] for x in checks),distance_rows_new=sum(x['rows_new'] for x in checks),road_max_core_seconds=max(x['seconds'] for x in checks if x['kind']=='road'),all_pass=True))
if __name__=='__main__':main()
