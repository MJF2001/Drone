"""One-time coordinate registration. Static sets only; no planner imports."""
from region_common import *
import ast,shutil,difflib,platform
def rect(x0,x1,y0,y1):return {(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)}
def register():
 assert not (H/'plan.json').exists()
 for d in ('inputs','outputs','jobs','qualification','history','figures','logs','preparation'):(H/d).mkdir(exist_ok=True)
 # No planner, activation predicate, distance, route or gain is evaluated here.
 F=rect(0,32,0,22);base=(1,10);C=rect(3,4,10,11)
 defs=[
 ('G1-A',{'C0':C,'S':rect(8,9,10,11),'R':rect(20,22,9,12)},F,(6,10)),
 ('G1-B',{'C0':C,'S':rect(8,9,10,11),'R':rect(20,22,9,12)},F,(7,10)),
 ('G2-A',{'C0':C,'S':rect(7,8,3,4),'R':rect(20,22,10,13)},F,(6,7)),
 ('G2-B',{'C0':C,'S':rect(7,8,3,4),'R':rect(20,22,10,13)},F,(7,6)),
 ('G3-A',{'C0':C,'S':rect(9,10,10,11),'R':rect(22,24,9,12)},F,(6,10)),
 ('G3-B',{'C0':C,'S':rect(9,10,3,4),'R':rect(22,24,9,12)},F,(6,10)),
 ('G4-A',{'C0':C,'S':rect(8,9,10,11),'R':rect(20,23,10,11)},F,(6,10)),
 ('G4-B',{'C0':C,'S':rect(8,8,10,16),'R':rect(20,23,10,11)},F,(6,10)),
 ('G5-A',{'C0':C,'R':rect(20,22,9,12)},F,(10,10)),
 ('G5-B',{'C0':C,'S':rect(3,4,18,19),'R':rect(8,10,10,13)},F,(6,10)),
 ('G6-A',{'C0':C,'S':rect(9,10,10,11),'R':rect(19,21,6,9),'T':rect(25,28,15,18)},F-({(15,y) for y in range(1,22)}-{(15,5),(15,10),(15,18)}),(15,10)),
 ('G6-B',{'C0':C,'S':rect(9,10,10,11),'R':rect(19,21,6,9),'T':rect(25,28,15,18)},F-({(15,y) for y in range(1,22)}-{(15,5),(15,10),(15,18)}),(15,18))]
 slots=[];static=[]
 for ident,labels,free,obstacle in defs:
  P=set().union(*labels.values());assert len(P)==sum(map(len,labels.values())) and P<=free
  assert base in free-P and obstacle in free-{base} and len(free)<=10000 and len(P)<=1500
  for k,v in labels.items():
   assert v==rect(min(x for x,y in v),max(x for x,y in v),min(y for x,y in v),max(y for x,y in v))
   for l,w in labels.items():
    if k<l:assert not any((x+dx,y+dy) in w for x,y in v for dx,dy in ((0,1),(1,0),(0,-1),(-1,0)))
  c=dict(name=ident+'__history',phase='history_prepare',free=sorted(free),published_targets=sorted(P),initial_targets=sorted(P),targets=sorted(P),covered=[],deferred_targets=[],current=base,base=base,previous=None,predator=(-10,10),old_route=[],distance_budget=1000000,labels={k:sorted(v) for k,v in labels.items()})
  dump(H/'inputs'/(ident+'__history.json'),c)
  slots.append(dict(id=ident,base_geometry=ident[:2],C0=sorted(C),obstacle=obstacle,labels=c['labels'],history_input='inputs/'+ident+'__history.json',history_input_sha256=sha(H/'inputs'/(ident+'__history.json')),event_input='inputs/'+ident+'.json'))
  static.append(dict(id=ident,passed=True,F=len(free),P=len(P),target_counts={k:len(v) for k,v in labels.items()}))
 jobs=[]
 for s in slots:jobs.append(dict(id='history__'+s['id'],phase='history',arm='ORIGINAL',slot=s['id'],input=s['history_input']))
 for sid in ('G1-A','G2-A','G5-A','G6-A'):
  for arm in ('ORIGINAL','OFF'):jobs.append(dict(id='equivalence__'+sid+'__'+arm,phase='equivalence',arm=arm,slot=sid,input='inputs/'+sid+'.json',**({'reference_id':'equivalence__'+sid+'__ORIGINAL'} if arm=='OFF' else {})))
 for i,s in enumerate(slots):
  for arm in (('ORIGINAL','ON') if i%2==0 else ('ON','ORIGINAL')):jobs.append(dict(id='formal__'+s['id']+'__'+arm,phase='formal',arm=arm,slot=s['id'],input=s['event_input']))
 assert len(jobs)==44
 plan=dict(slots=slots,jobs=jobs,seed=20261023,budgets=dict(core=20,post_soft=18,post_late=20,post_candidates=4096,main=40,parent=150,raw_edges=4096,free=10000,targets=1500,distance=1000000,added_rule_rows=3),gate_slots=['G1-A','G2-A','G5-A','G6-A'],cut='earliest post vertex j>=1 after all C0 actual credits, vertex published target, incoming actual post edge four-neighbor unit; no alternate cut',history_sharing='none; one fresh history per slot even when full inputs apart from name match',stop='any fixed gate slot ineligible: no equivalence/formal; implementation/responsibility error after first real call: immediate seal; quality negative finish fixed qualified matrix',no_event_control=False,detailed_profile=False)
 dump(H/'plan.json',plan);dump(H/'static_registration.json',static)
 for j in jobs:dump(H/'jobs'/(j['id']+'.json'),j)
 # Explicit identity evidence before histories; names removed only for relation report.
 pairs=[]
 for n in (1,2,6):
  a=read(H/f'inputs/G{n}-A__history.json');b=read(H/f'inputs/G{n}-B__history.json');a.pop('name');b.pop('name');assert a==b
  pairs.append(dict(base=f'G{n}',physical_input_equal_except_nonsemantic_name=True,history_shared=False))
 dump(H/'registered_identity_relations.json',pairs)
 source=ROOT/'障碍后片区次序与收尾规则设计_v0.1_20261023';prior=read(source/'source_guards.json');prior[str(source/'final_receipt.json')]=sha(source/'final_receipt.json');prior[str(source/'verify_receipt.json')]=sha(source/'verify_receipt.json')
 for p in source.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:prior[str(p.resolve())]=sha(p)
 runtime={}
 dirs=[ROOT/'基线复现准备_20261019',ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source',ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source',ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps']
 for d in dirs:
  for p in d.rglob('*.py'):runtime[str(p.resolve())]=sha(p)
 for p in (ROOT/'portable_frozen.py',ROOT/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py'):runtime[str(p.resolve())]=sha(p)
 dump(H/'runtime_guards.json',runtime);prior.update(runtime);dump(H/'source_guards.json',prior)
 original=ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
 diffs=[]
 for f in ('frozen_reference.py','region_native.py'):
  diffs.append(''.join(difflib.unified_diff(original.read_text(encoding='utf-8').splitlines(True),(H/f).read_text(encoding='utf-8').splitlines(True),fromfile=str(original),tofile=f)))
 (H/'source.diff').write_text('\n'.join(diffs),encoding='utf-8')
 copybindings=[]
 for p in (H/'region_center_v01_20261023').rglob('*.py'):
  old=ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022'/p.relative_to(H/'region_center_v01_20261023')
  assert sha(p)==sha(old);copybindings.append(dict(copy=str(p.relative_to(H)),source=str(old),sha256=sha(p)));runtime[str(old)]=sha(old)
 dump(H/'public_post_bindings.json',copybindings);dump(H/'runtime_guards.json',runtime)
 for p in H.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
 freeze={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('active_freeze.json',)}
 dump(H/'active_freeze.json',freeze)
 dump(H/'registration_receipt.json',dict(passed=True,slots=12,jobs=44,real_core=0,real_post=0,planner_imports=0,activation_checks=0,route_or_gain_queries=0,coordinates_locked=True,active_freeze_sha256=sha(H/'active_freeze.json'),utc=time.time(),environment=dict(python=sys.version,platform=platform.platform())))
 print('REGISTERED 12 slots / 44 planned jobs; no planner/rule/gain evaluated')
if __name__=='__main__':register()
