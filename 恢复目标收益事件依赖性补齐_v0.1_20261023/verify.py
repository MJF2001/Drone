"""Read-only hash/identity/receipt verification, no planning/geometry imports."""
from common import *
from collections import Counter
import sys,hashlib,datetime
def semantic(x):
 if isinstance(x,dict):return {k:semantic(v) for k,v in x.items() if k not in {'seconds','accepted_seconds','budget','overrun_gt_10ms','version'}}
 if isinstance(x,(list,tuple)):return [semantic(v) for v in x]
 return x
def main():
 checks=[];guards=read(H/'source_guards.json');active=read(H/'active_freeze.json')
 for p,d in guards.items():assert sha(p)==d,('source',p)
 for p,d in active.items():assert sha(H/p)==d,('active',p)
 for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d,('input/reused',p)
 for b in read(H/'bindings.json')['module_copies']:
  assert sha(b['source'])==b['source_sha256'] and sha(H/b['destination'])==b['destination_sha256']
  if b['destination'] in ('eventdep_diag_native.py','eventdep_diag_hook.py','eventdep_diag_decision_audit.py'):assert b['byte_identical'] and Path(b['source']).read_bytes()==(H/b['destination']).read_bytes()
 checks.append(f'{len(guards)} old source/evidence hashes; all new execution/input/reused freezes; byte-identical core/hook/auditor')
 sel=read(H/'selection.json');old=Path(sel['previous_E_package']);f=read(old/'final_receipt.json')
 for p,d in f['files'].items():assert sha(old/p)==d,('old seal',p)
 old_actual={str(p.relative_to(old)) for p in old.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert old_actual==set(f['files']) and len(old_actual)==122
 before=(H/'root_before.md').read_bytes();assert before==(old/'root_after.md').read_bytes() and sha(H/'root_before.md')==f['root_sha256'] and before.endswith((old/'root_before.md').read_bytes())
 pv=read(H/'previous_verify_at_start.json');assert pv['passed'] and pv['mode']=='sealed' and pv['writes']==pv['new_core_R_P2_post_geometry_BFS']==0 and pv['root_sha256_at_start']==f['root_sha256'] and pv['old_final_sha256']==sha(old/'final_receipt.json')
 root=ROOT/'当前进度与下一步.md';assert root.read_bytes().endswith(before)
 checks.append('old 122-file seal and start verify success intact; old root binds exact start bytes, current root preserves suffix history chain')
 plan=read(H/'plan.json');status=read(H/'status.json');ledger=read(H/'ledger.json');jobs=plan['jobs']
 assert len(jobs)==12 and Counter(j['target_label'] for j in jobs)=={'T0':6,'T1':6} and all(j['environment']==j['env']=='N' for j in jobs)
 assert [j['arm'] for j in jobs[:4]]==['OFF','OFF','ON','ON'] and status['two_OFF_gate_passed']
 assert len(status['completed'])==12 and status['failure'] is None and status['not_run']==[]
 assert plan['seeds']==[20261020,20261021,20261022] and len(plan['thread_env'])==4 and all(str(v)=='1' for v in plan['thread_env'].values())
 assert ledger['new_N_core_attempted']==ledger['new_N_core_completed']==ledger['new_N_post_saved']==12 and ledger['new_N_views']==24
 assert ledger['reused_E_processing']==12 and ledger['reused_E_views']==24 and ledger['combined_processing_routes']==24 and ledger['combined_views']==48 and ledger['four_cell_groups']==6
 assert ledger['new_E_R_P2_history_warmup_technical_calls']==0 and ledger['preparation_repairs']==0
 attempts=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(attempts)==24 and [a['id'] for a in attempts if a['event']=='started']==[j['id'] for j in jobs] and all(a['success'] for a in attempts if a['event']=='ended')
 def check_label(row):
  assert row['target_label']==(('T1' if row['target_intervention_enabled'] else 'T0') if row['environment']=='N' else ('T0' if row['target_intervention_enabled'] else 'T1'))
 outputs={};allviews={}
 for j in jobs:
  check_label(j);p=H/'outputs'/(j['id']+'.json');x=read(p);outputs[(j['case'],j['seed'],'N',j['target_label'])]=x
  assert x['job']==j and x['passed'] and x['main_passed'] and x['independent']['passed'] and x['decision_audit']['passed']
  for k in ('environment','target_label','target_intervention_enabled'):assert x[k]==x['native'][k]==j[k]
  assert x['native']==read(H/'outputs'/(j['id']+'_native_raw.json')) and x['input']==read(H/j['input'])
  assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0} and x['native_observation']['counts'] is None and x['native_counts_actual'] is None and j['config']=='OFF'
  diag=x['native']['diagnostic'];assert diag['counts']['matched']==1 and diag['counts']['applied']==int(j['target_intervention_enabled']) and diag['counts']['explanatory_distance_queries']==2
  assert x['decision_audit']['authorized_exceptions']==int(j['target_intervention_enabled']) and diag['core_detail_profile_enabled'] is False
  assert x['identity_before']==x['identity_after'] and x['identity_before']['primary']['file']!=x['identity_before']['independent']['file']
  assert x['timing']['termination']=='natural' and x['post_envelope']['fallback'] is None and not any(x['timing'][k] for k in ('native_late','raw_stage_late','combined_late','post_late'))
  postraw=read(H/'outputs'/(j['id']+'_post_raw.json'));assert postraw['response_utf8']==x['post_response_utf8'] and postraw['envelope']==x['post_envelope'] and x['post']==json.loads(x['post_response_utf8'])
  assert json.dumps(postraw['request'],ensure_ascii=False,separators=(',',':'))==x['post_request_utf8'] and postraw['request']['id']==j['id']
  assert hashlib.sha256(x['post_request_utf8'].encode()).hexdigest()==x['independent']['post']['input_sha256'] and hashlib.sha256(x['post_response_utf8'].encode()).hexdigest()==x['independent']['post']['output_sha256']
  for name,d in x['loaded_core_sources'].items():assert guards[name]==d==sha(name)
  for name,d in x['loaded_diagnostic_sources'].items():assert active[str(Path(name).relative_to(H))]==d==sha(name)
  if j['arm']=='OFF':
   assert x['off_equivalence']['passed'] and sha(j['old_B_N'])==j['old_B_N_sha256'];prior=read(j['old_B_N']);assert semantic(x['native']['raw'])==semantic(prior['native']['raw'])
   for a in ('A','B'):assert x['views'][a]['path']==prior['views'][a]['path'] and x['views'][a]['events']==prior['views'][a]['events'] and x['views'][a]['metrics']==prior['views'][a]['metrics']
  else:assert x['off_equivalence'] is None
 refs=read(H/'reused_E/index.json')['references'];assert len(refs)==12
 for ref in refs:
  check_label(ref);assert ref['environment']=='E' and sha(ref['source'])==ref['source_sha256'];w=read(H/ref['wrapper']);x=w['saved_output'];assert x==read(ref['source'])
  for k in ('environment','target_label','target_intervention_enabled'):assert w[k]==ref[k]
  assert x['passed'] and x['independent']['passed'] and x['decision_audit']['passed'];outputs[(ref['case'],ref['seed'],'E',ref['target_label'])]=x
 assert len(outputs)==24
 for key,x in outputs.items():
  for alias,v in x['views'].items():
   m=v['metrics'];assert m['remaining_before']==m['new_credit']==(201 if key[0].startswith('large') else 75) and m['missing']==m['deferred']==0 and m['active_coverage']==m['published_coverage']==1 and m['return_success'] and m['length']<=x['input']['distance_budget']
   assert ps(m['final_H'])==ps(x['input']['published_targets']) and ps(x['input']['covered'])<=ps(m['final_H']);allviews[(*key,alias)]=v
 vv=read(H/'48四格视图完整指标.json');assert len(vv)==48 and len(read(H/'24新增N视图完整指标.json'))==len(read(H/'24复用E视图完整指标.json'))==24
 assert Counter(v['environment'] for v in vv)=={'N':24,'E':24}
 for v in vv:
  check_label(v);assert sha(v['source'])==v['source_sha256'] and v['metrics']==allviews[(v['case'],v['seed'],v['environment'],v['target_label'],v['alias'])]['metrics']
 groups=read(H/'6组四格对照.json');proofs=read(H/'四格路径与local机制证据.json');arith=read(H/'独立算术核验.json');assert len(groups)==len(proofs)==6 and len(arith)==12
 for c in sel['selected']:
  n,e=read(H/c['input']),read(c['E_source']);assert sha(H/c['input'])==c['N_sha256'] and n==read(c['N_source'])
  assert all(n[k]==e[k] for k in n if k not in ('free','targets')) and ps(n['targets'])-ps(n['covered'])==ps(e['targets'])-ps(e['covered'])
  for x in (n,e):assert ps(x['targets'])==ps(x['published_targets'])&ps(x['free']) and not ps(x['published_targets'])-ps(x['free'])-ps(x['covered'])
 for proof in proofs:
  c=next(c for c in sel['selected'] if c['id']==proof['case']);spec=read(H/c['spec']);k=spec['trace_record']
  for name,cell in proof['cells'].items():
   env,t=name.split('_');x=outputs[(proof['case'],proof['seed'],env,t)];tr=x['native']['diagnostic']['trigger'];assert cell['trigger']==tr and tr['pending']==spec['pending'] and tr['current']==spec['current'] and tr['previous']==spec['previous'] and tr['chosen_goal']==spec[t]
   assert x['native']['raw']['trace'][:k]==spec['original_trace'][:k] and x['native']['raw']['route'][:tr['route_index']+1]==spec['original_route_prefix']
 for a in arith:
  assert a['independent']['passed'];alias='A' if a['view']=='raw' else 'B'
  for name,cert in a['input_length_certificates'].items():env,t=name.split('_');assert cert==outputs[(a['case'],a['seed'],env,t)]['views'][alias]['metrics']['length_certificate']
  g=next(g for g in groups if g['case']==a['case'] and g['seed']==a['seed']);assert a['primary']['values']==g['effects'][a['view']]
  for key in ('D_N','D_E','I'):assert a['primary']['values'][key]['sign']==a['independent']['values'][key]['sign']
 for g in groups:
  assert g['natural_complete_four_cells'] and g['cross_batch_E_N_time_interaction']=='forbidden/not computed'
  raw,post=g['effects']['raw'],g['effects']['post']
  if g['case'].startswith('large'):
   assert (raw['D_N']['display'],raw['D_E']['display'],raw['I']['display'])==(-2,0,2) and post['D_N']['sign']==-1 and post['D_E']['sign']==0 and post['I']['sign']==1
   assert g['target_comparisons']['E']['raw_route']['equal'] and g['target_comparisons']['E']['post_route']['equal']
  else:assert (raw['D_N']['display'],raw['D_E']['display'],raw['I']['display'])==(-2,-2,0) and post['D_N']['sign']==post['D_E']['sign']==post['I']['sign']==-1
 pre=read(H/'prechecks.json');assert pre['passed'] and len(pre['cases'])==6 and pre['new_core_post_geometry_BFS']==0 and read(H/'preparation_repairs.json')['used']==0
 assert read(H/'summary.json')['cross_batch_time_interaction_or_ranking_computed'] is False and read(H/'review_packet.json')['two_target_chain_stopped'] is True
 for f in read(H/'figure_receipts.json'):assert sha(H/f['path'])==f['sha256']
 assert read(H/'图版目视核验.json')['viewed_all']
 checks.append('12 new N cores/posts and six strict OFF equalities; 12 unchanged reused E outputs; 48 tagged views, six four-cell proofs, 12 independent saved arithmetic receipts bound; no cross-batch time inference')
 final=H/'final_receipt.json'
 if final.exists():
  f=read(final)
  for p,d in f['files'].items():assert sha(H/p)==d,('seal',p)
  actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert actual==set(f['files']) and len(actual)==f['file_count'] and sha(root)==f['root_sha256']
  checks.append(f'final {len(actual)}-file seal and current root intact; prior root history separately checked')
 else:assert '--preseal' in sys.argv
 print(json.dumps({'passed':True,'mode':'sealed' if final.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'new_core_E_R_P2_post_geometry_BFS':0,'new_arithmetic_execution':0,'writes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
