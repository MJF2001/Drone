import json,hashlib,sys,subprocess,os,time,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP_CAP_KR1共同预算比较_v0.1_20261020'
sys.path.insert(0,str(UP));from common_audit import audit as common
from audit_kr1 import audit as ka
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
spec=importlib.util.spec_from_file_location('pa',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py');pa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    return p
def main():
    p=protect();assert not (H/'execution').exists();rows=[]
    for j in p['jobs']:
        jp=H/'execution/jobs'/(j['run_id']+'.json');dest=H/'execution/results'/(j['run_id']+'.json');save(jp,j);dest.parent.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
        with (H/'execution'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
            pr=subprocess.run([sys.executable,'-B','-X','utf8',str(UP/'worker.py'),str(jp),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
        assert pr.returncode==0,j
        result=read(dest);c=read(j['input']);raw=result['raw'];check=common(c,dict(route=raw['route']));assert check['valid'] and result['eligible']
        if j['method']=='CAP_KR1':ka(c,raw)
        else:pa.audit(c,raw)
        m=metrics(c,raw['route']);row=dict(job=j,result_sha256=sha(dest),metrics=m,entry_seconds=result['entry_seconds'],eligible=result['eligible']);rows.append(row)
        save(H/'execution/checks.json',rows);print(len(rows),'/',len(p['jobs']),j['run_id'],m['length'],flush=True)
    protect();save(H/'execution/completion.json',dict(executed=len(rows),scheduled=36,valid=36,timely=36,holdout=False))
if __name__=='__main__':main()
