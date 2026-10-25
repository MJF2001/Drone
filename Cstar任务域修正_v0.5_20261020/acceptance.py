"""Seal before gates; old artifacts untouched. Stop at first audit/error."""
import sys,json,hashlib,subprocess,time,os
from pathlib import Path
from collections import Counter
from audit_v05 import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    p=read(HERE/'protocol.json')
    for path,h in p['sources'].items():assert sha(HERE/path)==h,path
    return p
def prepare():
    assert not (HERE/'protocol.json').exists();jobs=[]
    def add(c,name,kind,seed,budget,runtime='runtime'):
        path=HERE/'inputs'/(name+'.json')
        if not path.exists():save(path,c)
        jobs.append(dict(run_id=f'{kind}__{name}__{runtime}__{seed}',kind=kind,name=name,input=str(path),input_sha256=sha(path),runtime=runtime,seed=seed,budget=budget))
    for padding in (2,6,10):
        c=read(ROOT/'文献对照身份与复现偏差检查_20261020/micro/inputs'/f'padding_{padding}.json')
        for rt in ('service_only_runtime','runtime'):add(c,f'padding{padding}','ablation',20261018,5,rt)
    f=[(x,y) for x in range(5) for y in range(3)]
    boundary=dict(name='boundary_known',free=f,targets=f,covered=[],current=[0,0],base=[0,0],published_targets=f,distance_budget=1000)
    for rt in ('service_only_runtime','runtime'):add(boundary,'boundary_known','ablation',20261018,5,rt)
    for folder in ('micro_evidence','regression_evidence'):
        for c in read(ROOT/'Cstar历史适配验收_20261019/修正版_v0.2'/folder/'inputs.json'):
            for seed in (20261018,20261019):add(c,folder+'__'+c['name'],'micro',seed,5)
    special=read(ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3/evidence/results.json')
    holecases=[r['input'] for r in special if r['kind']=='functional' and 'expected_hole_case' in r['input']]
    assert len(holecases)==3
    for c in holecases:
        for seed in (20261018,20261019):add(c,c['name'],'micro_hole',seed,5)
    batch=ROOT/'七算法共同预算比较_v0.2_20261020'
    for j in read(batch/'protocol.json')['jobs']:
        if j['method']=='CSTAR':
            assert sha(Path(j['input']))==j['input_sha256'];add(read(Path(j['input'])),j['case_id'],'road',j['seed'],20)
    sources={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')}
    save(HERE/'protocol.json',dict(version='CSTAR_TASK_DOMAIN_v0.5',jobs=jobs,sources=sources,counts=dict(Counter(j['kind'] for j in jobs)),order='unit10 -> ablation8 -> old micro52 and hole6 -> synthetic deadlines -> road40',watchdog=35,acceptance='all positive micro and all roads complete legal within core budget and entry <= budget+0.010; negative fixtures reject; preserve all failures, no retries',scope='service S from initial pending, F remains transit; final knowledge closed current task; no future/old tail input, no global completion',stop='first exception/audit/feasible incompletion blocks following stages; road logical deadline failures retained through fixed40, two consecutive technical failures stop',holdout=False,ranking=False))
def execute(job):
    verify();assert sha(Path(job['input']))==job['input_sha256'];folder=HERE/'evidence';jp=folder/'jobs'/(job['run_id']+'.json');rp=folder/'results'/(job['run_id']+'.json');assert not rp.exists();save(jp,job);rp.parent.mkdir(parents=True,exist_ok=True)
    with (folder/(job['run_id']+'.log')).open('x',encoding='utf-8') as log:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(jp),str(rp)],stdout=log,stderr=subprocess.STDOUT,timeout=35,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
    assert proc.returncode==0,job['run_id'];z=read(rp);assert z['job']==job;r=z['result'];c=read(Path(job['input']));checked=audit(c,r,job['budget'])
    row=dict(run_id=job['run_id'],kind=job['kind'],runtime=job['runtime'],name=job['name'],seed=job['seed'],**checked,entry_seconds=z['entry_seconds'],result_sha256=sha(rp))
    row['timely']=row['accepted'] and z['entry_seconds']<=job['budget']+.010
    return row
def gates():
    p=verify();assert not (HERE/'gate_checks.json').exists()
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'test_v05.py'),'-v'],capture_output=True,text=True)
    (HERE/'unit_sealed.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0
    rows=[]
    for j in p['jobs']:
        if j['kind']=='road':continue
        row=execute(j);rows.append(row);save(HERE/'gate_checks.json',rows);print(j['run_id'],row['status'],row['steps'],flush=True)
        negative=j['name'].endswith(('resource_too_short','disconnected_target','disconnected_return'))
        if negative:assert not row['accepted']
        else:assert row['timely'],row
        if j['kind']=='ablation' and j['name'].startswith('padding'):assert row['steps']==12
    sys.path.insert(0,str(HERE/'runtime'));from history_adapter import solve
    c=read(HERE/'inputs/boundary_known.json');stages=[]
    discovery=solve(c,2,20261018,clock=lambda:0,checkpoint_hook=lambda s:stages.append(s));audit(c,json.loads(json.dumps(discovery)),2);assert discovery['status']=='task_complete'
    save(HERE/'deadline/discovery.json',discovery);checks=[]
    for stage in sorted(set(stages)):
        for relation,value in [('before',2-1e-6),('equal',2),('after',2+1e-6)]:
            state={'time':0,'hit':False}
            def hook(s):
                if s==stage and not state['hit']:state.update(time=value,hit=True)
            r=solve(c,2,20261018,clock=lambda:state['time'],checkpoint_hook=hook);r=json.loads(json.dumps(r));audit(c,r,2)
            assert state['hit']
            if relation=='before':assert r['status']=='task_complete'
            else:assert r['status'] in ('deadline','wall_clock_cap') and not r['route']
            name=stage+'__'+relation;save(HERE/'deadline'/(name+'.json'),r);checks.append(dict(name=name,status=r['status']))
    save(HERE/'deadline/checks.json',checks);verify();save(HERE/'gates_PASS.json',dict(calls=len(rows),unit_tests=10,deadline_calls=len(checks),discovery_calls=1,stages=sorted(set(stages))))
def roads():
    p=verify();assert (HERE/'gates_PASS.json').exists() and not (HERE/'road_checks.json').exists();rows=[]
    for j in p['jobs']:
        if j['kind']!='road':continue
        row=execute(j);rows.append(row);save(HERE/'road_checks.json',rows);print(j['run_id'],row['status'],row['steps'],row['entry_seconds'],flush=True)
    verify();save(HERE/'road_summary.json',dict(calls=len(rows),accepted=sum(r['accepted'] for r in rows),timely=sum(r['timely'] for r in rows),counts=dict(Counter(r['status'] for r in rows)),gate='PASS' if len(rows)==40 and all(r['timely'] for r in rows) else 'NOT_PASSED',ranking=False))
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='gates':gates()
    elif sys.argv[1]=='road':roads()
