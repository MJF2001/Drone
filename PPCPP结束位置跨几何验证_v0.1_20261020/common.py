import json,hashlib,sys,importlib.util,time
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'基线复现准备_20261019'))
native=load('small_native',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')
pa=load('small_original_audit',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
validation=load('small_validation',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py')
metric=load('small_metrics',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py').metrics
cross=load('small_cross',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py').calculate
from model import Snapshot
def solve_payload(payload):
 begin=time.perf_counter();c=json.loads(payload);validation.validate(c)
 s=Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
 r=native.solve(s,set(map(tuple,c['initial_targets'])),20-(time.perf_counter()-begin),20261020,tuple(c['predator']),tuple(c['previous']) if c['previous'] else None)
 wire=json.dumps(r,ensure_ascii=False,allow_nan=False);seconds=time.perf_counter()-begin
 return dict(raw=r,entry_seconds=seconds,eligible=r['status']=='core_complete' and seconds<20,payload_bytes=len(wire.encode('utf-8')))
def points(v):return set(map(tuple,v))
def protect():
 for p,h in read(H/'protocol.json')['files'].items():assert sha(R/p)==h,p
 if (H/'input_seal.json').exists():
  for p,h in read(H/'input_seal.json').items():assert sha(H/p)==h,p
