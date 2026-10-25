import json,hashlib,sys,subprocess,os
from pathlib import Path
from worker import snapshot
from rollout import solve,native
from checks import audit,norm
H=Path(__file__).resolve().parent;R=H.parent
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    return p
def gates():
    protect();records=[]
    def call(c,method,hook=None):
        s=snapshot(c);args=(s,set(map(tuple,c['initial_targets'])),5,20261018,tuple(c['predator']),tuple(c['previous']))
        r=native.solve(*args) if method=='PPCPP' else solve(*args,mode='one' if method=='ONE' else 'three',_hook=hook)
        item=dict(input=c,method=method,result=r);records.append(item);save(H/'gates.json',records);audit(c,r);return r
    for mask in range(64):
        h={(-1,0),(0,0)};cells=[(x,y) for x in range(3) for y in range(2)];t=h|{p for k,p in enumerate(cells) if mask>>k&1}
        c=dict(name='micro_'+str(mask),free=sorted(set(cells)|h),targets=sorted(t),covered=sorted(h),published_targets=sorted(t),deferred_targets=[],current=(0,0),base=(-1,0),distance_budget=100,initial_targets=sorted(h),predator=(-2,0),previous=(-1,0),old_route=[(0,0),(-1,0)])
        n=call(c,'PPCPP');one=call(c,'ONE');three=call(c,'THREE')
        assert n['status']==one['status']==three['status']=='core_complete'
        assert norm(n['route'])==norm(one['route']) and norm(n['trace'])==norm(one['trace'])
        base=three['branches'][0];assert norm(base['route'])==norm(n['route']) and norm(base['trace'])==norm(n['trace'])
        if three['branch_state'] is not None and len(three['branches'])>1:discovery=c
    seen=[];call(discovery,'THREE',lambda stage:seen.append(stage))
    for target in sorted(set(seen)):
        def hook(stage):
            if stage==target:raise native.DeadlineExceeded()
        r=call(discovery,'THREE',hook);assert r['status']=='deadline' and not r['route']
    save(H/'gate_PASS.json',dict(calls=len(records),micro_subsets=64,deadline_stages=len(set(seen)),all_pass=True))
def run():
    p=protect();assert read(H/'gate_PASS.json')['all_pass'] and not (H/'execution').exists();rows=[]
    for i,j in enumerate(p['jobs']):
        jp=H/'execution/jobs'/(j['run_id']+'.json');dest=H/'execution/results'/(j['run_id']+'.json');save(jp,j);dest.parent.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
        with (H/'execution'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
            code=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jp),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
        assert code==0,j;r=read(dest);c=read(j['input']);audit(c,r['raw'])
        row=dict(job=j,eligible=r['eligible'],status=r['raw']['status'],entry_seconds=r['entry_seconds'],result_sha256=sha(dest),metrics=metrics(c,r['raw']['route']) if r['raw']['route'] else None);rows.append(row);save(H/'execution/checks.json',rows)
        print(i+1,'/',len(p['jobs']),j['run_id'],row['metrics']['length'] if row['metrics'] else row['status'],flush=True)
    protect();save(H/'execution/completion.json',dict(scheduled=len(p['jobs']),executed=len(rows),eligible=sum(x['eligible'] for x in rows)))
if __name__=='__main__':
    if sys.argv[1]=='gates':gates()
    else:run()
