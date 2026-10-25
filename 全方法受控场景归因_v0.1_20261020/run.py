import json,hashlib,subprocess,sys,time,os,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
sys.path.insert(0,str(R/'PPCPP_CAP_KR1共同预算比较_v0.1_20261020'));from common_audit import audit as common
from audit_kr1 import audit as kr
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
pa=mod('full_pa',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
tc=mod('full_tc',R/'TRACE_CAP适配复现_20261020/audit.py')
ca=mod('full_ca',R/'Cstar连接器等价提速_v0.7_20261020/audit_v05.py')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    return p
def audit(c,r,m,budget):
    if m=='PPCPP':
        if r['route']:pa.audit(c,r)
    elif m=='CSTAR':ca.audit(c,r,budget)
    elif m=='CAP_KR1':kr(c,r)
    else:tc.audit(c,r)
def execute(j,folder):
    jp=folder/'jobs'/(j['run_id']+'.json');dest=folder/'results'/(j['run_id']+'.json');assert not dest.exists();save(jp,j);dest.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');start=time.perf_counter()
    with (folder/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
        try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jp),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
        except subprocess.TimeoutExpired:code=None
    x=dict(job=j,technical_failure=code!=0,watchdog=code is None,process_seconds=time.perf_counter()-start,valid=False,eligible=False,metrics=None)
    if code==0:
        r=read(dest);c=read(j['input']);raw=r['raw'];ck=common(c,dict(route=raw['route'] if raw else []))
        if raw:audit(c,raw,j['method'],r['solver_budget'])
        if raw and raw['route']:assert ck['valid']
        x.update(valid=ck['valid'],eligible=r['eligible'] and ck['valid'],entry_seconds=r['entry_seconds'],status=raw['status'] if raw else 'entry_deadline',result_sha256=sha(dest),metrics=metrics(c,raw['route']) if ck['valid'] else None)
    return x
def main():
    p=protect();assert not (H/'execution').exists();gates=[]
    for m in p['methods']:
        for late in (False,True):
            j=dict(run_id='gate_'+m+('_late' if late else ''),method=m,input=p['gate_input'],budget=5,seed=20261018,inject_late=late)
            x=execute(j,H/'preflight');gates.append(x);save(H/'preflight/checks.json',gates)
            assert x['valid'] and x['eligible']==(not late),x
    save(H/'preflight/PASS.json',dict(calls=10,all_pass=True))
    rows=[];consecutive=0
    for i,j in enumerate(p['jobs']):
        try:x=execute(j,H/'execution')
        except Exception as exc:save(H/'execution/ABORTED.json',dict(index=i,error=repr(exc)));raise
        rows.append(x);save(H/'execution/checks.json',rows);consecutive=consecutive+1 if x['technical_failure'] else 0
        print(i+1,'/',len(p['jobs']),j['run_id'],x['valid'],x['eligible'],x['metrics']['length'] if x['metrics'] else None,flush=True)
        if consecutive>=2:break
    protect();save(H/'execution/completion.json',dict(scheduled=270,executed=len(rows),valid=sum(x['valid'] for x in rows),timely=sum(x['eligible'] for x in rows),technical_failures=sum(x['technical_failure'] for x in rows),not_run=270-len(rows)))
if __name__=='__main__':main()
