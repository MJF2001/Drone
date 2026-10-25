import json,hashlib,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def protect():
 for p,h in read(H/'protocol.json')['files'].items():assert sha(R/p)==h,p
 if (H/'source_seal.json').exists():
  for p,h in read(H/'source_seal.json')['files'].items():assert sha(H/p)==h,p
def points(xs):return set(map(tuple,xs))
old=R/'PPCPP小图最优差距诊断_v0.2_20261020'
pa=load('last_independent_original_audit',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
metric=load('last_metrics',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py').metrics
cross=load('last_cross',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py').calculate
