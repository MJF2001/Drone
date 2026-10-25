"""Pure I/O, frozen metrics and fixed rectangular geometry, no planners."""
import json,hashlib,csv,importlib.util,collections,math,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020';S=R/'复杂障碍压力开发测试_v0.1_20261021';M=R/'评价指标完整补算与数据审计_v0.1_20261020'
CONDS=('CONTROL','H_SIDE','MIXED_SIDE','U_SIDE');SEEDS=(20261020,20261021,20261022);METHODS=('PPCPP','P2_MULTI')
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normal(x):return json.loads(json.dumps(x,ensure_ascii=False))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(p,rows):
    if not rows:return
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,tuple,dict)) else v for k,v in r.items()} for r in rows])
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
metric=load('widen_metric',M/'metrics.py').metrics;cross=load('widen_cross',M/'crosscheck.py').calculate
def dual(c,path):
    a=metric(c,path);assert a==cross(c,path) and a['complete_legal'];return a
def rect(x,y,w,h):return {(xx,yy) for xx in range(x,x+w) for yy in range(y,y+h)}
def adj(p):
    x,y=p;return ((x+1,y),(x,y+1),(x-1,y),(x,y-1))
def bfs(f,s):
    d={s:0};q=collections.deque([s])
    while q:
        p=q.popleft()
        for n in adj(p):
            if n in f and n not in d:d[n]=d[p]+1;q.append(n)
    assert set(d)==f;return d
def history(route,t0,cut):return set(map(tuple,route[:cut+1]))&t0
def timely(seconds,legal):return bool(legal and seconds<20)
def position_label(k,ell):return 'U_SIDE' if k==0 else 'H_SIDE' if k==ell else 'MIXED_SIDE'
def binding():return {n:sha(H/n) for n in read(H/'binding_files.json')}
def receipt(stage,paths):save(H/'receipts'/f'{stage}.json',dict(stage=stage,status='PASS',binding=binding(),files={str(Path(p).relative_to(H)):sha(p) for p in paths}))
def require(stage):
    r=read(H/'receipts'/f'{stage}.json');assert r['stage']==stage and r['status']=='PASS' and r['binding']==binding(),stage
    for p,h in r['files'].items():assert sha(H/p)==h,p
    return r
def check_seal(name):
    s=read(H/name);assert s['complete'] and s['binding']==binding()
    for p,h in s['critical'].items():assert sha(p)==h,p
    return s
