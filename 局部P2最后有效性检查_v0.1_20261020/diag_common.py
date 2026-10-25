import json,hashlib,sys,time,importlib.util
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parent;S=R/'PPCPP局部P2混合开发诊断_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def norm(x):return json.loads(json.dumps(x))
def pts(x):return set(map(tuple,x))
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def production():
 sys.path.insert(0,str(S));import hybrid,runtime
 return hybrid,runtime
