"""Read-only stdlib verification. No native/rule/post imports or new searches."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,hashlib,math,time,ast
H=Path(__file__).resolve().parent;ROOT=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def terms(path):
 out=Counter()
 for a,b in zip(path,path[1:]):
  n=sum((x-y)**2 for x,y in zip(a,b));assert n>0;k=1;r=n;p=2
  while p*p<=r:
   while r%(p*p)==0:k*=p;r//=p*p
   p+=1
  out[r]+=k
 return dict(out)
def turns(path):
 dirs=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:])];c=Counter()
 for a,b in zip(dirs,dirs[1:]):
  cross=a[0]*b[1]-a[1]*b[0];dot=a[0]*b[0]+a[1]*b[1]
  if cross or dot<0:c['total']+=1;c['90' if dot==0 else '180' if cross==0 else 'other']+=1
 return dict(c)
def verify(sealed=True):
 start=time.perf_counter();guards=0
 for g in ('source_guards.json','runtime_guards.json'):
  for p,v in read(H/g).items():assert sha(p)==v,p;guards+=1
 for p,v in read(H/'active_freeze.json').items():assert sha(H/p)==v,('frozen',p)
 if (H/'qualification_freeze.json').exists():
  for p,v in read(H/'qualification_freeze.json').items():assert sha(H/p)==v,('qualification',p)
 plan=read(H/'plan.json');assert len(plan['slots'])==12 and len(plan['jobs'])==44
 pre=read(H/'prechecks.json');assert len(pre['cases'])<=16 and pre['real_core']==pre['real_post']==0
 if (H/'entry_log.jsonl').exists():ledger=[json.loads(s) for s in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()]
 else:ledger=[]
 starts=[r for r in ledger if r['event']=='started'];assert all(len([r for r in starts if r['kind']==k])<=44 for k in ('core','post'));assert len({(r['kind'],r['job']) for r in starts})==len(starts)
 for phase,cap in (('history',12),('equivalence',8),('formal',24)):
  assert all(sum(r['phase']==phase and r['kind']==k for r in starts)<=cap for k in ('core','post'))
 jobs={j['id']:j for j in plan['jobs']};views=0
 for p in (H/'outputs').glob('*.json'):
  r=read(p);assert r['job']==jobs[r['job']['id']]
  if r['passed']:
   assert r['independent']['passed'] and r['decision_audit']['passed'];assert r['timing']['combined_end_to_end']>=r['timing']['raw_common_end_to_end']>=r['timing']['native_entry_seconds']
   assert abs(r['timing']['combined_end_to_end']-r['timing']['raw_common_end_to_end']-r['timing']['post_increment'])<1e-8
   for v in r['views'].values():
    actual=terms(v['path']);saved={e['r']:Fraction(e['c']['n'],e['c']['d']) for e in v['metrics']['length_certificate']['exact']['terms']};assert actual==saved
    assert turns(v['path'])==v['metrics']['turns'];m=v['metrics'];assert m['missing']==0 and m['return_success'] and m['remaining_before']==m['new_credit'];views+=1
 status=read(H/'run_status.json')
 if status['status']=='stopped_fixed_gate_slot_ineligible':
  rows=read(H/'state_registry.json');assert len(rows)==12
  assert all(r['phase']=='history' for r in starts)
  bad=[s for s in plan['gate_slots'] if next(r for r in rows if r['id']==s)['status']!='qualified'];assert bad==status['failed_gate_slots'] and bad
 assert (ROOT/'当前进度与下一步.md').read_bytes()==(H/'root_after.md').read_bytes();assert (H/'root_after.md').read_bytes().endswith((H/'root_before.md').read_bytes())
 prior=ROOT/'障碍后片区次序与收尾规则设计_v0.1_20261023';assert (H/'root_before.md').read_bytes()==(prior/'root_after.md').read_bytes();assert sha(H/'root_before.md')==read(prior/'final_receipt.json')['root_sha256']
 files=0
 if sealed:
  f=read(H/'final_receipt.json');assert f['root_sha256']==sha(ROOT/'当前进度与下一步.md')
  for p,v in f['files'].items():assert sha(H/p)==v,('sealed',p);files+=1
 return dict(passed=True,scope='saved source/seal/root chain + ledger caps + saved independent audit receipts + independently refactored integer radical lengths/turns; no planner, rule, post, BFS, new geometric/service searches; not universal algorithm proof or benefit verification',guards_checked=guards,sealed_files=files,views_recomputed=views,actual_core=sum(r['kind']=='core' for r in starts),actual_post=sum(r['kind']=='post' for r in starts),status=status['status'],seconds=time.perf_counter()-start)
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
