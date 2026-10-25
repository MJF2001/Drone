"""Pure I/O/source stage contracts. No planners or graph operations."""
from pathlib import Path
import json,hashlib,os
H=Path(__file__).resolve().parent;R=H.parent;P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def put(p,b):
    with Path(p).open('xb') as f:f.write(b)
def env():return dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
def binding():return {n:sha(H/n) for n in read(H/'binding_files.json')}
def config():
    x=read(H/'config.json')
    if H.name=='SYNTHETIC_TECHNICAL_NOT_REAL':assert x['synthetic_only'] is True
    else:assert x==dict(real_entry_cap=18,entry_budget=20,watchdog=90,seed=20261021,threads=1,stub_cap_all_rounds=24,technical_round_cap=3)
    return x
def receipt(stage,files):save(H/'receipts'/(stage+'.json'),dict(stage=stage,status='PASS',binding=binding(),files={str(Path(p).relative_to(H)):sha(p) for p in files}))
def require(stage):
    x=read(H/'receipts'/(stage+'.json'));assert x['status']=='PASS' and x['stage']==stage and x['binding']==binding()
    for p,v in x['files'].items():assert sha(H/p)==v,p
    return x
def check_seal():
    require('technical');require('seal');x=read(H/'seal.json');assert x['complete'] and x['binding']==binding()
    for p,v in x['critical'].items():assert sha(p)==v,p
    return x
