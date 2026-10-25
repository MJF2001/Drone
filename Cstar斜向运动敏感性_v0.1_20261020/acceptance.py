"""Preseal -> semantic/cost/path gates -> old complete golden runs -> road40."""
import sys,json,hashlib,subprocess,os
from pathlib import Path
from collections import Counter
from audit_diagonal import audit
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'Cstar任务域修正_v0.5_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    p=read(HERE/'protocol.json')
    for f,h in p['sources'].items():assert sha(HERE/f)==h,f
    return p
def view(r):
    return {k:v for k,v in r.items() if k not in ('seconds','version','adaptation','protection_cache','efficiency_stats')}
def prepare():
    assert not (HERE/'protocol.json').exists();jobs=[]
    prior=read(OLD/'protocol.json')
    for j in prior['jobs']:
        if j['kind']=='road' or (j['kind']!='road' and j['runtime']=='runtime'):
            j=dict(j);j.update(runtime='runtime',run_id=j['kind']+'__'+j['name']+'__'+str(j['seed']))
            jobs.append(j)
    save(HERE/'protocol.json',dict(version='CSTAR_DIAGONAL_SENSITIVITY_v0.1',jobs=jobs,sources={str(f.relative_to(HERE)):sha(f) for f in HERE.rglob('*.py')},
        counts=dict(Counter(j['kind'] for j in jobs)),unit_tests=10,order='unit10 -> prior micro62 -> synthetic deadlines -> fixed road40',
        motion='8-neighbour; cardinal1 diagonal_sqrt2; both corner-side cells must be free; ONLY landed cells credited; same rule for base return',
        semantic_change='motion and incidental acquisition consequences ONLY; RCG/TSP policies unchanged; NOT equivalent to four-neighbour output',
        holdout=False,ranking=False,watchdog=35,entry_tolerance=.010,
        comparison='sensitivity to granting ONLY CSTAR diagonals; do NOT merge with frozen seven-method ranking; both are geometric length, but feasible motion sets differ',
        stop='first technical/audit/gate failure blocks roads; fixed40 retains logical failures, no retry or budget increase'))
def execute(j):
    verify();assert sha(Path(j['input']))==j['input_sha256'];jp=HERE/'evidence/jobs'/(j['run_id']+'.json');rp=HERE/'evidence/results'/(j['run_id']+'.json')
    assert not rp.exists();save(jp,j);rp.parent.mkdir(parents=True,exist_ok=True)
    with (HERE/'evidence'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(jp),str(rp)],stdout=log,stderr=subprocess.STDOUT,timeout=35,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
    assert proc.returncode==0,j['run_id'];z=read(rp);assert z['job']==j
    r=z['result'];checked=audit(read(Path(j['input'])),r,j['budget'])
    row=dict(run_id=j['run_id'],kind=j['kind'],name=j['name'],seed=j['seed'],**checked,entry_seconds=z['entry_seconds'],result_sha256=sha(rp))
    row['timely']=row['accepted'] and z['entry_seconds']<=j['budget']+.010
    if 'golden' in j:
        assert sha(Path(j['golden']))==j['golden_sha256']
        before=view(read(Path(j['golden']))['result']);after=view(r)
        if before!=after:
            save(HERE/'golden_difference.json',dict(run_id=j['run_id'],different_keys=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]))
            raise AssertionError('golden result changed: '+j['run_id'])
        row['golden_equal']=True
    return row
def gates():
    p=verify();assert not (HERE/'gate_checks.json').exists()
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'test_diagonal.py'),'-v'],capture_output=True,text=True)
    (HERE/'unit.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0
    rows=[]
    for j in p['jobs']:
        if j['kind']=='road':continue
        row=execute(j);rows.append(row);save(HERE/'gate_checks.json',rows);print(j['run_id'],row['status'],row['steps'],row['entry_seconds'],flush=True)
        negative=j['name'].endswith(('resource_too_short','disconnected_target','disconnected_return'))
        if negative:assert not row['accepted']
        else:assert row['timely'],row
    sys.path.insert(0,str(HERE/'runtime'));from history_adapter import solve
    c=read(OLD/'inputs/boundary_known.json');stages=[]
    r=solve(c,2,20261018,clock=lambda:0,checkpoint_hook=lambda s:stages.append(s));audit(c,json.loads(json.dumps(r)),2);assert r['status']=='task_complete'
    save(HERE/'deadline/discovery.json',r);checks=[]
    for stage in sorted(set(stages)):
        for relation,value in [('before',2-1e-6),('equal',2),('after',2+1e-6)]:
            state={'time':0,'hit':False}
            def hook(s):
                if s==stage and not state['hit']:state.update(time=value,hit=True)
            r=solve(c,2,20261018,clock=lambda:state['time'],checkpoint_hook=hook);r=json.loads(json.dumps(r));audit(c,r,2);assert state['hit']
            assert r['status']=='task_complete' if relation=='before' else r['status'] in ('deadline','wall_clock_cap') and not r['route']
            name=stage+'__'+relation;save(HERE/'deadline'/(name+'.json'),r);checks.append(dict(name=name,status=r['status']))
    save(HERE/'deadline/checks.json',checks);verify();save(HERE/'gates_PASS.json',dict(calls=len(rows),unit_tests=10,deadline_calls=len(checks),discovery_calls=1,stages=sorted(set(stages))))
def roads():
    p=verify();assert (HERE/'gates_PASS.json').exists() and not (HERE/'road_checks.json').exists();rows=[]
    for j in p['jobs']:
        if j['kind']!='road':continue
        row=execute(j);rows.append(row);save(HERE/'road_checks.json',rows);print(j['run_id'],row['status'],row['steps'],row['entry_seconds'],flush=True)
    verify();save(HERE/'road_summary.json',dict(calls=len(rows),accepted=sum(r['accepted'] for r in rows),timely=sum(r['timely'] for r in rows),counts=dict(Counter(r['status'] for r in rows)),gate='PASS' if len(rows)==40 and all(r['timely'] for r in rows) else 'NOT_PASSED',ranking=False))
if __name__=='__main__':{'prepare':prepare,'gates':gates,'road':roads}[sys.argv[1]]()
