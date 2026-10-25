"""Read-only hashes, saved contracts/receipts and ledger arithmetic. No solvers."""
from pathlib import Path
import json,hashlib,sys
H=Path(__file__).resolve().parent;ROOT=H.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 count=0
 for rel,v in read(H/'active_freeze.json').items():assert sha(H/rel)==v,rel;count+=1
 for rel,v in read(H/'source_guards.json').items():assert sha(Path(rel))==v,rel;count+=1
 for rel,v in read(H/'runtime_guards.json').items():assert sha(Path(rel))==v,rel;count+=1
 if (H/'qualification_freeze.json').exists():
  for rel,v in read(H/'qualification_freeze.json').items():assert sha(H/rel)==v,rel;count+=1
 rows=[json.loads(s) for s in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()] if (H/'entry_log.jsonl').exists() else []
 starts=[z for z in rows if z['event']=='started'];keys=[(z['job'],z['kind']) for z in starts];assert len(keys)==len(set(keys))
 counts={kind:sum(z['kind']==kind for z in starts) for kind in ('core','post')};assert counts['core']<=42 and counts['post']<=42
 for arm,cap in [('history',6),('REF',12),('OFF',12),('ALT1',12)]:
  for kind in ('core','post'):assert sum(z['arm']==arm and z['kind']==kind for z in starts)<=cap
 status=read(H/'status.json');reviewed=0;views=0
 for item in status['completed']:
  out=read(H/'outputs'/(item['id']+'.json'));assert out['input']==read(H/out['job']['input'])
  if out['passed'] and 'independent' in out and 'decision_audit' in out:
   assert out['independent']['passed'] and out['decision_audit']['passed'];reviewed+=1;views+=len(out['views'])
  if out['job']['arm']=='OFF' and out['passed']:assert all(out['off_equivalence'].values())
 for row in read(H/'pairs.json'):
  assert row['independent_sign']['independent_from_physical_vertices']
  for k in ('phases_OFF','phases_ALT1'):
   p=row[k];assert sum(p[z] for z in ('before_trigger','recovery','after_own_goal_coverage','return_after_last'))==p['total']
 before=(H/'root_before.md').read_bytes();current=(ROOT/'当前进度与下一步.md').read_bytes()
 if (H/'root_after.md').exists():assert current==(H/'root_after.md').read_bytes() and current.endswith(before)
 else:assert current==before
 if (H/'final_receipt.json').exists():
  f=read(H/'final_receipt.json')
  for rel,v in f['files'].items():assert sha(H/rel)==v,rel
  assert f['root_sha256']==sha(ROOT/'当前进度与下一步.md')
 result=dict(passed=True,hash_bindings_checked=count,actual_entry_counts=counts,reviewed_processing=reviewed,views=views,root_history_chain=True,failure_retained=status['failure'],new_core_calls=0,new_post_calls=0,new_geometry_queries=0,new_BFS=0)
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
