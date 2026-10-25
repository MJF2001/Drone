"""Read-only saved evidence and history chain. No solver/post/geometry imports."""
from common import *
from collections import Counter
import sys,hashlib,datetime
def sem(x):
 if isinstance(x,dict):return {k:sem(v) for k,v in x.items() if k not in {'seconds','accepted_seconds','budget','overrun_gt_10ms','version'}}
 if isinstance(x,(list,tuple)):return [sem(v) for v in x]
 return x
def main():
 checks=[]
 for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d,('input',p)
 active=read(H/'active_freeze.json')
 for p,d in active.items():assert sha(H/p)==d,('active',p)
 guards=read(H/'source_guards.json')
 for p,d in guards.items():assert sha(p)==d,('source',p)
 b=read(H/'bindings.json');assert sha(b['original_native'])==b['original_native_sha256'] and sha(b['accepted_worker'])==b['accepted_worker_sha256'] and sha(b['original_independent_auditor'])==b['original_independent_auditor_sha256']
 checks.append(f'{len(guards)} old source/evidence hashes; current execution/input freeze; original core/worker intact')
 old=Path(read(H/'selection.json')['old_package']);oldfinal=read(old/'final_receipt.json')
 for p,d in oldfinal['files'].items():assert sha(old/p)==d,('old seal',p)
 oldfiles={str(p.relative_to(old)) for p in old.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert oldfiles==set(oldfinal['files'])
 before=(H/'root_before.md').read_bytes();assert before==(old/'root_after.md').read_bytes() and sha(H/'root_before.md')==oldfinal['root_sha256']
 assert before.endswith((old/'root_before.md').read_bytes())
 pv=read(H/'previous_verify_at_start.json');assert pv['passed'] and pv['mode']=='sealed' and pv['writes']==pv['new_core_R_post_geometry_BFS']==0 and pv['root_sha256_at_start']==oldfinal['root_sha256'] and pv['previous_final_sha256']==sha(old/'final_receipt.json')
 root=ROOT/'当前进度与下一步.md';assert root.read_bytes().endswith(before)
 checks.append('old 220-file seal and successful old verify at start; old root hash binds exact root_before, current progress preserves historical suffix chain')
 plan=read(H/'plan.json');status=read(H/'status.json');ledger=read(H/'ledger.json');selection=read(H/'selection.json')
 assert len(plan['jobs'])==12 and Counter(j['arm'] for j in plan['jobs'])=={'OFF':6,'ON':6}
 assert [j['arm'] for j in plan['jobs'][:4]]==['OFF','OFF','ON','ON'] and len({j['case'] for j in plan['jobs'][:2]})==2
 assert status['two_OFF_gate_passed'] and len(status['completed'])==12 and status['failure'] is None and status['not_run']==[]
 assert plan['seeds']==[20261020,20261021,20261022] and len(plan['thread_env'])==4 and all(str(v)=='1' for v in plan['thread_env'].values())
 assert ledger['core_attempted']==ledger['core_completed']==ledger['post_saved']==12 and ledger['views']==24 and ledger['complete_pairs']==6 and ledger['state_count']==2
 assert ledger['new_N_R_P2']==ledger['technical_core']==ledger['warmup']==ledger['new_maps']==ledger['new_calls_after_formal']==0
 events=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];assert len(events)==24
 assert [e['id'] for e in events if e['event']=='started']==[j['id'] for j in plan['jobs']] and len({e['id'] for e in events if e['event']=='started'})==12 and all(e['success'] for e in events if e['event']=='ended')
 expected={};outputs={}
 for c in selection['selected']:
  inp=read(H/c['input']);sp=read(H/c['spec']);assert inp==read(sp['source_E']['path']) and sha(H/c['input'])==sp['source_E']['sha256'] and sp['source_E']['path'].endswith('E_contract_v02.json')
  assert ps(inp['targets'])==ps(inp['published_targets'])&ps(inp['free']) and not ps(inp['published_targets'])-ps(inp['free'])-ps(inp['covered'])
  assert len(ps(inp['targets'])-ps(inp['covered']))==sp['initial_U'] and ps(sp['pending'])==ps(inp['targets'])-ps(inp['covered'])-ps(sp['original_route_prefix'])
 for j in plan['jobs']:
  f=H/'outputs'/(j['id']+'.json');x=read(f);outputs[(j['case'],j['seed'],j['arm'])]=x
  assert x['job']==j and x['passed'] and x['main_passed'] and x['independent']['passed'] and x['decision_audit']['passed']
  assert x['input']==read(H/j['input']) and x['native']==read(H/'outputs'/(j['id']+'_native_raw.json'))
  assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0} and x['native_observation']['counts'] is None and x['native_counts_actual'] is None and j['config']=='OFF'
  assert x['identity_before']==x['identity_after'] and x['identity_before']['primary']['file']!=x['identity_before']['independent']['file']
  d=x['native']['diagnostic'];assert d['target_intervention_enabled']==j['target_intervention_enabled'] and d['core_detail_profile_enabled'] is False
  assert d['counts']['matched']==1 and d['counts']['applied']==int(j['target_intervention_enabled']) and d['counts']['explanatory_distance_queries']==2
  assert x['decision_audit']['authorized_exceptions']==int(j['target_intervention_enabled'])
  assert len(d['decision_states'])==d['counts']['decision_records']==len(x['native']['raw']['trace'])-1
  assert x['timing']['termination']=='natural' and x['post_envelope']['fallback'] is None and not any(x['timing'][k] for k in ('native_late','raw_stage_late','combined_late','post_late'))
  assert x['native']['raw']['route']==x['native']['raw']['branches']['P0']['route'] and x['native']['raw']['selected']=='P0'
  postraw=read(H/'outputs'/(j['id']+'_post_raw.json'));assert postraw['response_utf8']==x['post_response_utf8'] and postraw['envelope']==x['post_envelope'] and x['post']==json.loads(x['post_response_utf8'])
  assert json.dumps(postraw['request'],ensure_ascii=False,separators=(',',':'))==x['post_request_utf8']
  assert hashlib.sha256(x['post_request_utf8'].encode()).hexdigest()==x['independent']['post']['input_sha256'] and hashlib.sha256(x['post_response_utf8'].encode()).hexdigest()==x['independent']['post']['output_sha256']
  for path,digest in x['loaded_core_sources'].items():assert guards[path]==digest==sha(path)
  for path,digest in x['loaded_diagnostic_sources'].items():assert active[str(Path(path).relative_to(H))]==digest==sha(path)
  for alias,v in x['views'].items():
   m=v['metrics'];assert m['missing']==m['deferred']==0 and m['active_coverage']==m['published_coverage']==1 and m['return_success'] and m['length']<=x['input']['distance_budget']
   assert m['remaining_before']==m['new_credit']==(201 if j['base_id']=='large_Z' else 75)
   assert ps(m['final_H'])==ps(x['input']['published_targets']) and ps(x['input']['covered'])<=ps(m['final_H'])
   assert x['independent']['views'][alias]['passed'];expected[(j['id'],alias)]=v
  if j['arm']=='OFF':
   assert x['off_equivalence']['passed'] and sha(j['old_B_E'])==j['old_B_E_sha256'];prior=read(j['old_B_E'])
   assert sem(x['native']['raw'])==sem(prior['native']['raw'])
   for a in ('A','B'):assert x['views'][a]['path']==prior['views'][a]['path'] and x['views'][a]['events']==prior['views'][a]['events'] and x['views'][a]['metrics']==prior['views'][a]['metrics']
  else:assert x['off_equivalence'] is None
 vv=read(H/'24视图完整指标.json');assert len(vv)==24
 for v in vv:assert v['metrics']==expected[(v['id'],v['alias'])]['metrics'] and v['source_sha256']==sha(H/'outputs'/(v['id']+'.json'))
 pairs=read(H/'6对ON减OFF全指标.json');proof=read(H/'逐决策干预证明.json');assert len(pairs)==len(proof)==6
 for p in proof:
  off,on=[outputs[(p['case'],p['seed'],arm)] for arm in ('OFF','ON')];sp=read(H/off['job']['spec']);k=sp['trace_record'];ta,tb=[x['native']['raw']['trace'] for x in (off,on)]
  assert ta[:k]==tb[:k] and dict(tb[k],goal=ta[k]['goal'])==ta[k]
  assert p['triggers']['OFF']==off['native']['diagnostic']['trigger'] and p['triggers']['ON']==on['native']['diagnostic']['trigger']
  assert p['triggers']['ON']['pending']==p['triggers']['OFF']['pending']==sp['pending'] and p['ON_authorized_exceptions']==1 and p['OFF_authorized_exceptions']==0
  a,b=[p['triggers'][arm]['route_index'] for arm in ('OFF','ON')];assert off['views']['A']['path'][:a+1]==on['views']['A']['path'][:b+1]==sp['original_route_prefix']
  for arm,x in [('OFF',off),('ON',on)]:assert sum(p['native_partitions'][arm]['unit_lengths'].values())==len(x['views']['A']['path'])-1
 for p in pairs:
  if p['base_id']=='large_Z':assert p['raw_route']['equal'] and p['post_route']['equal'] and p['post_credit_order']['equal'] and p['raw_distance_delta']['sign']==p['post_distance_delta']['sign']==0
  else:assert p['raw_distance_delta']['display']==-2 and p['post_distance_delta']['sign']==-1 and not p['post_credit_order']['equal']
  assert p['causal_pair_natural']
 assert {p['case'] for p in pairs}=={c['id'] for c in selection['selected']} and len(selection['selected'])==2
 pre=read(H/'prechecks.json');first=read(H/'prechecks_preparation_v01_passed_count_incomplete.json');assert pre['passed'] and first['passed'] and len(pre['cases'])==len(first['cases'])==8 and ledger['pure_item_attempts']==16
 assert pre['real_core']==pre['real_post']==first['real_core']==first['real_post']==0 and read(H/'preparation_repairs.json')['used']==1
 assert len(pre['all_independent_stub_attempts_including_rejections'])==5 and sum(a['counts']['BFS_calls'] for a in pre['all_independent_stub_attempts_including_rejections'])==6
 assert read(H/'summary.json')['all_OFF_old_equal'] and read(H/'summary.json')['all_ON_unique_trigger_and_audit']
 q=read(H/'调用与查询总账.json')['formal_observed_aggregates'];assert q['diagnostic']['explanatory_distance_queries']==24 and q['independent_decision']['BFS_calls']==45
 assert read(H/'review_packet.json')['new_rollout_or_performance_batch_started'] is False
 for p in read(H/'figure_receipts.json'):assert sha(H/p['path'])==p['sha256']
 assert read(H/'图版目视核验.json')['viewed_all']
 checks.append('12 original returns / 12 common posts / 24 views / six strict OFF equalities and six one-goal intervention proofs; all later independent rules and cost receipts bound')
 final=H/'final_receipt.json'
 if final.exists():
  f=read(final)
  for p,d in f['files'].items():assert sha(H/p)==d,('seal',p)
  actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert actual==set(f['files']) and len(actual)==f['file_count']
  assert sha(root)==f['root_sha256'];checks.append(f'final {len(actual)}-file seal and current root hash intact; historical root verified separately')
 else:assert '--preseal' in sys.argv
 print(json.dumps({'passed':True,'mode':'sealed' if final.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'new_core_R_P2_post_geometry_BFS':0,'writes':0,'old_root_evolution_is_not_evidence_damage':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
