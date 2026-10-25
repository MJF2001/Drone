import json,sys,subprocess,os,time,hashlib,importlib.util
from pathlib import Path
from common_audit import audit as common
from audit_kr1 import audit as audit_kr1
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
spec=importlib.util.spec_from_file_location('independent_ppcpp_audit',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py');pa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(Path(f))==h,f
    return p
def execute(j,folder):
    protect();assert sha(j['input'])==j['input_sha256']
    jp=folder/'jobs'/(j['run_id']+'.json');rp=folder/'results'/(j['run_id']+'.json');assert not rp.exists();save(jp,j);rp.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    start=time.perf_counter();watchdog=False
    with (folder/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
        try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jp),str(rp)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
        except subprocess.TimeoutExpired:code=None;watchdog=True
    row=dict(run_id=j['run_id'],method=j['method'],case_id=j['case_id'],seed=j['seed'],technical_failure=watchdog or code!=0,watchdog=watchdog,process_seconds=time.perf_counter()-start,valid=False,timely=False,steps=None)
    if not row['technical_failure']:
        r=read(rp);assert r['job']==j;c=read(j['input']);raw=r['raw'];check=common(c,dict(route=raw['route'] if raw else []))
        if raw:
            if j['method']=='CAP_KR1':audit_kr1(c,raw)
            elif raw['route']:pa.audit(c,raw)
        if raw and raw['route']:assert check['valid'],check
        assert r['eligible']==bool(r['complete'] and r['entry_seconds']<j['budget'] and r['independent_call_seconds']<j['budget'])
        if r['eligible']:assert check['valid'] and r['accepted_route']==raw['route']
        else:assert r['accepted_route']==[]
        row.update(valid=check['valid'],timely=r['eligible'] and check['valid'],steps=check['steps'],status=r['status'],entry_seconds=r['entry_seconds'],independent_call_seconds=r['independent_call_seconds'],payload_bytes=r['payload_bytes'],result_sha256=sha(rp),audit='PASS')
    return row
def main():
    p=protect();assert not (H/'execution').exists()
    # Common auditor must reject the same deliberately bad physical routes.
    c=read(p['gate_input']);good=[[1,0],[2,0],[3,0],[4,0],[3,0],[2,0],[1,0],[0,0]]
    assert common(c,dict(route=good))['valid']
    for route in ([],[[1,0],[0,0]],[[1,0],[4,0],[0,0]],[[1,0],[99,0],[0,0]],[[1,0],[2,0],[3,0],[4,0]]):assert not common(c,dict(route=route))['valid']
    gate=[]
    for method in p['methods']:
        j=dict(run_id='gate_'+method,case_id='gate',method=method,input=p['gate_input'],input_sha256=sha(p['gate_input']),budget=5,seed=20261018)
        x=execute(j,H/'preflight');gate.append(x);save(H/'preflight/checks.json',gate);assert x['timely'] and not x['technical_failure'],x
    # Deterministically force post-serialization expiry for BOTH methods.
    from worker import invoke
    deadline=[]
    for method in p['methods']:
        class Clock:
            value=0
            def __call__(self):return self.value
        clock=Clock()
        def hook(stage):
            if stage=='serialized':clock.value=6
        x=invoke(Path(p['gate_input']).read_bytes(),method,5,20261018,clock=clock,phase_hook=hook)
        deadline.append(x);save(H/'preflight/deadline.json',deadline)
        assert x['complete'] and not x['eligible'] and not x['accepted_route'] and x['status']=='late_complete'
    save(H/'preflight/PASS.json',dict(calls=4,physical_audit_probes=6))
    rows=[];consecutive=0
    for i,j in enumerate(p['jobs']):
        try:x=execute(j,H/'execution')
        except Exception as exc:save(H/'execution/ABORTED.json',dict(index=i,error=repr(exc)));raise
        rows.append(x);save(H/'execution/checks.json',rows);consecutive=consecutive+1 if x['technical_failure'] else 0
        print(i+1,'/',len(p['jobs']),j['run_id'],'valid',x['valid'],'timely',x['timely'],'steps',x['steps'],flush=True)
        if consecutive>=2:break
    protect();save(H/'execution/completion.json',dict(scheduled=len(p['jobs']),executed=len(rows),not_run=len(p['jobs'])-len(rows),technical_failures=sum(x['technical_failure'] for x in rows),holdout=False))
if __name__=='__main__':main()
