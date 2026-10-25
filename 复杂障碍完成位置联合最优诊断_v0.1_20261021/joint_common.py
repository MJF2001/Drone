"""Experiment I/O and independent route accounting; no planner imports."""
import json,hashlib,csv,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;S=R/'复杂障碍压力开发测试_v0.1_20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def normal(x):return json.loads(json.dumps(x,ensure_ascii=False))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def csvsave(p,rows):
    if not rows:return
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()} for r in rows])
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=load('joint_metric_a',M/'metrics.py').metrics;cross=load('joint_metric_b',M/'crosscheck.py').calculate
def account(c,path,last=None):
    route=list(map(tuple,path));a=metric(c,route);assert a==cross(c,route) and a['complete_legal']
    pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));acq=[]
    for i,p in enumerate(route):
        if p in pending:pending.remove(p);acq.append((i,p))
    assert not pending
    completion=acq[-1][0] if acq else 0;ep=acq[-1][1] if acq else None
    assert completion==a['completion_step'] and len(route)-1-completion==a['return_tail_steps']
    if last is not None:assert ep==tuple(last)
    return dict(metrics=a,C=completion,ep=ep,R=len(route)-1-completion,last_new_acquisitions=acq)
def query(c,last=None):
    # Raw targets-H retain possible start target; exact engines credit start themselves.
    return dict(free=c['free'],start=c['current'],base=c['base'],tasks=sorted(set(map(tuple,c['targets']))-set(map(tuple,c['covered']))),last=last,resource=c['distance_budget'],seconds=60,max_states=1000000)
