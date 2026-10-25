"""Strict semantic equality, normalizing tuple/list and named clock metadata only."""
from common import read,sha
from pathlib import Path
def claim_destination(path):
 with Path(path).open('x',encoding='utf-8') as f:f.write('')
CLOCK_FIELDS={'seconds','accepted_seconds','budget','overrun_gt_10ms','version'}
def semantic(x):
 if isinstance(x,dict):return {k:semantic(v) for k,v in x.items() if k not in CLOCK_FIELDS}
 if isinstance(x,(list,tuple)):return [semantic(v) for v in x]
 return x
def compare_old_off(result):
 j=result['job'];assert sha(j['old_B_E'])==j['old_B_E_sha256'];old=read(j['old_B_E'])
 assert result['input']==old['input'],'OFF input mismatch'
 assert semantic(result['native']['raw'])==semantic(old['native']['raw']),'OFF full raw/decision semantics mismatch'
 assert result['post']['vertices']==old['post']['vertices'],'OFF post path mismatch'
 for alias in ('A','B'):
  assert result['views'][alias]['path']==old['views'][alias]['path'] and result['views'][alias]['events']==old['views'][alias]['events'],'OFF path/credit mismatch'
  assert result['views'][alias]['metrics']==old['views'][alias]['metrics'],'OFF metrics mismatch'
 return {'passed':True,'source':j['old_B_E'],'sha256':j['old_B_E_sha256'],'full_raw_semantic_equal':True,'raw_route_trace_options_index_pending_preserved':True,'post_path_and_all_credit_events_equal':True,'all_metrics_equal':True,'excluded_named_metadata':sorted(CLOCK_FIELDS)}
