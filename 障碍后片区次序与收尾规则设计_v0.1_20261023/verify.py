"""Document-package integrity only. No rule semantics/performance validation.
No old script imports, no task data classification, no geometry/path operations.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,time,ast,re
H=Path(__file__).resolve().parent;ROOT=H.parent;C=Counter()
def read(p):
 b=Path(p).read_bytes();C['json_reads']+=1;C['json_bytes']+=len(b);return json.loads(b.decode('utf-8-sig'))
def sha(p):
 b=Path(p).read_bytes();C['hash_reads']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def verify():
 start=time.perf_counter()
 for p,v in read(H/'source_guards.json').items():assert sha(p)==v,p
 m=read(H/'manifest.json');assert m['status']=='design_draft_pending_owner_decision' and m['rule_count']==1 and m['all_new_policy_items_pending_approval'];assert not m['rule_implemented'] and not m['rule_tested'] and m['old_rule_classifications']==m['geometry_queries_performed']==m['new_snapshots']==0;assert all(type(v) is int and v==0 for v in m['actual_new_calls'].values());assert not m['prior_cost_protocol_pursued'] and not m['prior_estimator_stage_B_reopened']
 b=m['future_proposed_budget'];assert b['history_core']+b['equivalence_core']+b['formal_core']==b['total_core']==44;assert b['history_post']+b['equivalence_post']+b['formal_post']==b['total_post']==44;assert b['pure_cases']==16
 slots=read(H/'sample_slots_draft.json');assert slots['contains_coordinates'] is False and slots['snapshots_generated']==slots['old_cases_classified_by_new_rule']==0;rr=slots['slots'];assert len(rr)==12 and len({x['id'] for x in rr})==12 and Counter(x['base'] for x in rr)==Counter({f'G{i}':2 for i in range(1,7)});assert all(x['status']=='proposed_pending_approval_not_snapshot' and set(x)=={'id','base','variant','status'} for x in rr)
 names=['00_固定规则通俗说明与待裁决.md','01_确定性规则伪代码与接口改动.md','02_小规模正反结构验证协议_待核定.md','03_来源与机制重合.md','设计审阅记录.md','review_packet.md'];links=0
 for name in names:
  path=H/name;s=path.read_text(encoding='utf-8');C['document_reads']+=1;C['document_bytes']+=len(s.encode());assert s.strip()
  if name[:2] in ('00','01','02'):assert '待核定' in s
  for ref in re.findall(r'\]\(([^)]+)\)',s):
   assert not ref.startswith(('http:','https:')),'no new web provenance expected';target=re.sub(r':\d+$','',ref);p=(H/target).resolve();assert p.is_file(),(name,ref)
   line=re.search(r':(\d+)$',ref)
   if line:assert int(line.group(1))<=len(p.read_text(encoding='utf-8-sig').splitlines())
   links+=1
 # Only packaging utilities are executable. This audits imports, not pseudocode.
 allowed={'pathlib','collections','json','hashlib','time','sys','ast','re'}
 python_files=list(H.glob('*.py'));assert {p.name for p in python_files}=={'archive.py','verify.py'}
 for p in python_files:
  tree=ast.parse(p.read_text(encoding='utf-8'))
  for node in ast.walk(tree):
   if isinstance(node,ast.Import):assert all(x.name.split('.')[0] in allowed for x in node.names)
   elif isinstance(node,ast.ImportFrom):assert node.module.split('.')[0] in allowed
   C['AST_nodes']+=1
 source=read(H/'开工静态来源核验.json');assert source['passed'] and source['old_verify_reexecuted'] is False and source['old_scripts_imported'] is False
 old=ROOT/'障碍后双候选完整试走既有证据审查_v0.1_20261023';before=(H/'root_before.md').read_bytes();assert before==(old/'root_after.md').read_bytes() and sha(H/'root_before.md')==read(old/'final_receipt.json')['root_sha256'];oldv=read(old/'verify_receipt.json');assert oldv['passed'] and oldv['final_receipt_sha256']==sha(old/'final_receipt.json')
 now=(ROOT/'当前进度与下一步.md').read_bytes();assert now.endswith(before)
 if (H/'root_after.md').exists():assert now==(H/'root_after.md').read_bytes() and now.startswith('# 最新进度：片区次序与收尾规则设计草案待核定'.encode())
 else:assert now==before
 sealed=0
 if (H/'final_receipt.json').exists():
  f=read(H/'final_receipt.json');assert f['status']=='design_draft_sealed_pending_approval_stopped' and not f['rule_implemented'] and not f['rule_tested'] and not f['scientific_rule_validation_claim'] and not f['auto_execution']
  for p,v in f['files'].items():assert sha(H/p)==v,p;sealed+=1
  assert f['root_sha256']==sha(ROOT/'当前进度与下一步.md')
 result=dict(passed=True,validation_scope='documents/links/source hashes/pending metadata/proposed budget arithmetic/root chain ONLY; no rule correctness, benefit or speed claim',documents=len(names),links_checked=links,proposed_slots=12,proposed_core_cap=44,proposed_post_cap=44,rule_implemented=False,rule_evaluated=False,new_snapshots=0,actual_new_calls=m['actual_new_calls'],old_scripts_imported=False,old_verifiers_executed=0,root_chain=True,sealed_files_checked=sealed,counts=dict(C),seconds=time.perf_counter()-start)
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
