"""Pure I/O and frozen postprocessors; no planning import."""
from pathlib import Path
import json,hashlib,csv,importlib.util
H=Path(__file__).resolve().parent;R=H.parent;S=R/'复杂障碍压力开发测试_v0.1_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
CASES=('31x21_maze_p30','31x21_serpentine_p30');SEEDS=(20261020,20261021,20261022)
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(p,rows):
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in r.items()} for r in rows])
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
M=R/'评价指标完整补算与数据审计_v0.1_20261020';metric=load('probe_metric',M/'metrics.py').metrics;cross=load('probe_cross',M/'crosscheck.py').calculate
def both(c,path):
    a=metric(c,path);assert a==cross(c,path) and a['complete_legal'];return a
EXCLUSIONS={'$.entry_seconds':'entry wall clock','$.phase_seconds.p0':'P0 duration','$.phase_seconds.final_audit':'final audit duration','$.phase_seconds.encoding':'encoding duration','$.raw.branches.P0.seconds':'native duration','$.raw.branches.P0.accepted_seconds':'native accepted duration','$.raw.branches.P0.budget':'remaining wall clock passed to one native call'}
def comparable(x):
    x=norm(x)
    for pointer in EXCLUSIONS:
        keys=pointer[2:].split('.');node=x
        for key in keys[:-1]:node=node[key]
        assert keys[-1] in node,pointer;node.pop(keys[-1])
    return x
