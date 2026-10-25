from pathlib import Path
import json,hashlib,time,os,sys,importlib.util
H=Path(__file__).resolve().parent;ROOT=H.parent
OLD=ROOT/'障碍后片区两阶段规则有限验证_v0.1_20261023'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ps(a):return set(map(tuple,a))
def norm(a):return json.loads(json.dumps(a,ensure_ascii=False,allow_nan=False))
def append(p,x):
 with Path(p).open('a',encoding='utf-8') as f:
  f.write(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def bindings():
 from region_center_v01_20261023 import bench,metrics,service,exact
 from region_center_v01_20261023.post import engine,geometry
 from region_center_v01_20261023.audit import _post_geometry,region
 import region_native
 import frozen_reference as ref
 val=module('_region_resume_v02_validation_20261023',ROOT/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py')
 from model import Snapshot
 return dict(B=bench,metrics=metrics,service=service,exact=exact,engine=engine,G=geometry,IG=_post_geometry,region=region,native=region_native,reference=ref,validate=val.validate,Snapshot=Snapshot)
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
 assert len(starts)<16 and not any(z['job']==job['id'] for z in starts),'absolute entry cap / duplicate'
 oldrows=[json.loads(z) for z in (OLD/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()]
 oldstarts=[z for z in oldrows if z['event']=='started' and z['kind']==kind]
 assert len(oldstarts)==22 and len(oldstarts)+len(starts)<38 and not any(z['job']==job['old_job_id'] for z in oldstarts),'cross-version cap / repeat'
 phase=job['phase'];assert phase=='formal'
 allowed=read(H/'plan.json')['jobs'];assert job in allowed,'unregistered call'
 append(p,dict(event='started',kind=kind,job=job['id'],phase=phase,arm=job['arm'],utc=time.time()))
def returned(job,kind):append(H/'entry_log.jsonl',dict(event='returned',kind=kind,job=job['id'],phase=job['phase'],arm=job['arm'],utc=time.time()))
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
 for p,v in read(H/'old_package_guards.json').items():assert sha(OLD/p)==v,('old changed',p)
