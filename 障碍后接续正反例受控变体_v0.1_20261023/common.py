from pathlib import Path
import json,hashlib,time,os,sys,importlib.util
H=Path(__file__).resolve().parent;ROOT=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ps(a):return set(map(tuple,a))
def norm(a):return json.loads(json.dumps(a,ensure_ascii=False,allow_nan=False))
def append(p,x):
 with Path(p).open('a',encoding='utf-8') as f:
  f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def bindings():
 sys.path.insert(0,str(ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022'))
 from center_bench_v01_20261022 import bench,metrics,service,exact
 from center_bench_v01_20261022.post import engine,geometry
 from center_bench_v01_20261022.audit import _post_geometry,region
 import expand_native
 ref=module('_expand_frozen_reference',ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')
 val=module('_expand_frozen_validation',ROOT/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py')
 from model import Snapshot
 return dict(B=bench,metrics=metrics,service=service,exact=exact,engine=engine,G=geometry,IG=_post_geometry,region=region,native=expand_native,reference=ref,validate=val.validate,Snapshot=Snapshot)
def phase_validate(c,validate):
 validate(c);F=ps(c['free']);P=ps(c['published_targets']);HH=ps(c['covered']);S=tuple(c['current']);B=tuple(c['base'])
 assert ps(c['initial_targets'])==P and ps(c['targets'])==P&F
 assert not ps(c['deferred_targets']) and ps(c['targets'])-HH==P-HH
 if c['phase']=='history_prepare':
  assert S==B and B in F and B not in P and not HH and c['previous'] is None,'history phase contract'
 elif c['phase']=='event_response':
  assert S in P and S in HH and c['previous'] is not None,'event current must actually have been collected'
  prev=tuple(c['previous']);assert prev in F and sum(abs(a-b) for a,b in zip(prev,S))==1,'event true heading'
 else:raise AssertionError('unknown phase')
def snapshot(c,Snapshot):return Snapshot(c['name'],frozenset(ps(c['free'])),frozenset(ps(c['targets'])),frozenset(ps(c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
def canonical(x):
 excluded={'seconds','accepted_seconds','budget','overrun_gt_10ms'}
 if isinstance(x,dict):return {k:canonical(v) for k,v in x.items() if k not in excluded}
 if isinstance(x,(tuple,list)):return [canonical(v) for v in x]
 return x
def entry(job,kind):
 p=H/'entry_log.jsonl';rows=[json.loads(z) for z in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []
 starts=[z for z in rows if z['event']=='started' and z['kind']==kind]
 assert len(starts)<36 and not any(z['job']==job['id'] for z in starts),'absolute entry cap / duplicate'
 phase=job['arm'];cap=0 if phase=='history' else 12
 assert sum(z['arm']==phase for z in starts)<cap
 append(p,dict(event='started',kind=kind,job=job['id'],arm=phase,utc=time.time()))
def returned(job,kind):append(H/'entry_log.jsonl',dict(event='returned',kind=kind,job=job['id'],arm=job['arm'],utc=time.time()))
def loaded_sources():
 out={}
 for m in list(sys.modules.values()):
  p=getattr(m,'__file__',None)
  if p:
   p=Path(p).resolve()
   if p.suffix=='.py' and p.is_relative_to(ROOT):out[str(p)]=sha(p)
 return out
def guard():
 for p,v in read(H/'active_freeze.json').items():assert sha(H/p)==v,('active changed',p)
 for p,v in read(H/'runtime_guards.json').items():assert sha(p)==v,('runtime changed',p)
 if (H/'qualification_freeze.json').exists():
  for p,v in read(H/'qualification_freeze.json').items():assert sha(H/p)==v,('qualification changed',p)
