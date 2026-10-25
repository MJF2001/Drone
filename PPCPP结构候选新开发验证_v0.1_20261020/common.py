import json,hashlib,subprocess,sys,os
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def protect(inputs=False):
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    if inputs:
        seal=read(H/'input_seal.json');assert seal['protocol_sha256']==sha(H/'protocol.json')
        for f,h in seal['files'].items():assert sha(f)==h,f
    return p
def call(j,dest):
    dest.parent.mkdir(parents=True,exist_ok=True);jp=dest.with_suffix('.job.json');save(jp,j)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    with dest.with_suffix('.log').open('x',encoding='utf-8') as log:
        code=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jp),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
    assert code==0,(j,dest);return read(dest)
def signature(c):
    f=list(map(tuple,c['free']));dx=min(x for x,y in f);dy=min(y for x,y in f)
    def number(v):return int(v) if float(v).is_integer() else v
    def point(q):return [number(q[0]-dx),number(q[1]-dy)] if q is not None else None
    data={k:sorted(point(q) for q in c[k]) for k in ('free','targets','covered','published_targets','initial_targets')}
    for k in ('current','base','previous','predator'):data[k]=point(c[k])
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
