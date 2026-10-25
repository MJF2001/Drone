"""Read-only hashes, saved independent receipts and accounting; no solver imports."""
from common import *
from collections import Counter
import sys,datetime,hashlib
def main():
 checks=[]
 for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d,('input',p)
 for p,d in read(H/'active_freeze.json').items():assert sha(H/p)==d,('active',p)
 guards=read(H/'source_guards.json')
 for p,d in guards.items():assert sha(p)==d,('source',p)
 checks.append(f'{len(guards)} old source/evidence hashes and current input/active freezes intact')
 b=read(H/'bindings.json');assert sha(b['accepted_OFF_worker_file'])==b['accepted_OFF_worker_sha256']
 assert sha(H/'worker_r.py')==b['R_worker_sha256'] and sha(H/'repair_runtime.py')==b['R_runtime_sha256']
 assert sha(Path(b['reused_accepted_batch'])/'worker_r.py')==b['R_worker_sha256'] and sha(Path(b['reused_accepted_batch'])/'repair_runtime.py')==b['R_runtime_sha256']
 assert read(H/'input_contract.json')['projection_used'] is False
 sel=read(H/'selection.json');plan=read(H/'plan.json');status=read(H/'status.json');ledger=read(H/'ledger.json')
 assert [c['id'] for c in sel['selected']]==['large_Z_corner_p30','medium_Z_corner_p30']
 assert {c['shape'] for c in sel['selected']}=={'Z'} and len({c['base_id'] for c in sel['selected']})==2
 assert len(plan['jobs'])==36 and Counter(j['branch'] for j in plan['jobs'])=={'B':12,'R':12,'C':12}
 assert plan['seeds']==[20261020,20261021,20261022] and all(str(v)=='1' for v in plan['thread_env'].values()) and len(plan['thread_env'])==4
 assert len(status['completed'])==36 and status['failure'] is None and status['not_run']==[]
 assert (ledger['processing_attempted'],ledger['processing_completed'],ledger['actual_core'],ledger['R'],ledger['technical_core'],ledger['warmup'])==(36,36,24,12,0,0)
 events=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(events)==72 and [x['id'] for x in events if x['event']=='started']==[j['id'] for j in plan['jobs']]
 assert len({x['id'] for x in events if x['event']=='started'})==36 and all(x['success'] for x in events if x['event']=='ended')
 for ci,c in enumerate(sel['selected']):
  n,e=read(H/c['N']),read(H/c['E']);hist=read(H/c['history']);cert=read(H/c['certificate'])
  assert n==hist['N_source_reconstruction'];assert n['old_route']==hist['suffix'] and n['current']==hist['prefix'][-1] and n['previous']==hist['prefix'][-2]
  assert all(n[k]==e[k] for k in n if k not in ('targets','free'))
  assert ps(n['free'])-ps(e['free'])==ps(c['obstacles'])<=ps(n['covered'])
  assert len(ps(n['targets'])-ps(n['covered']))==len(ps(e['targets'])-ps(e['covered']))==[201,75][ci]
  for x in (n,e):assert ps(x['targets'])==ps(x['published_targets'])&ps(x['free']) and not ps(x['published_targets'])-ps(x['free'])-ps(x['covered'])
  assert cert['N_legal'] and cert['remaining_all_reachable'] and [z['edge'] for z in cert['strict_coverage_blockages']]==[[61,62],[30,31]][ci]
  for x in c['sources'].values():assert sha(x['path'])==x['sha256']
  for x in hist['source_files'].values():assert sha(x['path'])==x['sha256']
 checks.append('two fixed normalized N/E inputs, complete physical H, U and old suffix/history/certificates bound without geometry replay')
 saved=[];rr={};expectedviews={}
 for j in plan['jobs']:
  p=H/'outputs'/(j['id']+'.json');x=read(p);assert x['job']==j and x['passed'] and x['main_passed'] and x['independent']['passed']
  assert x['input']==read(H/j['input']) and x['native']==read(H/'outputs'/(j['id']+'_native_raw.json'))
  assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0} and x['native_counts_actual'] is None and x['native_observation']['counts'] is None
  assert x['identity_before']==x['identity_after'] and x['identity_before']['primary']['file']!=x['identity_before']['independent']['file']
  postraw=read(H/'outputs'/(j['id']+'_post_raw.json'))
  assert x['post']==json.loads(x['post_response_utf8']) and postraw['response_utf8']==x['post_response_utf8'] and postraw['envelope']==x['post_envelope']
  assert json.dumps(postraw['request'],ensure_ascii=False,separators=(',',':'))==x['post_request_utf8']
  assert hashlib.sha256(x['post_request_utf8'].encode()).hexdigest()==x['independent']['post']['input_sha256']
  assert hashlib.sha256(x['post_response_utf8'].encode()).hexdigest()==x['independent']['post']['output_sha256']
  assert x['timing']['termination']=='natural' and x['post_envelope']['fallback'] is None
  assert not any(x['timing'][k] for k in ('native_late','raw_stage_late','combined_late','post_late'))
  for alias,v in x['views'].items():
   m=v['metrics'];assert m['remaining_before']==(201 if j['base_id']=='large_Z' else 75)
   assert m['missing']==m['deferred']==0 and m['return_success'] and m['active_coverage']==m['published_coverage']==1
   assert ps(x['input']['covered'])<=ps(m['final_H'])==ps(x['input']['published_targets'])
   assert m['length']<=x['input']['distance_budget'] and v['path'][0]==x['input']['current'] and v['path'][-1]==x['input']['base']
   assert x['independent']['views'][alias]['passed'];expectedviews[(j['id'],alias)]=v
  for src,d in x['loaded_core_sources'].items():assert src in guards and guards[src]==d==sha(src)
  if j['branch']=='R':
   assert x['independent']['repair_structure']['passed'];q=x['native']['repair_counts'];assert q['entry_started']==q['entry_returned']==1
   assert q['BFS_started']==q['BFS_returned']==(1 if j['env']=='E' else 0)
   key=j['case'],j['env'];route=x['native']['raw']['route'];assert key not in rr or route==rr[key];rr[key]=route
  else:assert x['native']['method']==j['method'] and x['native']['seed']==j['seed']
  saved.append({'id':j['id'],'source_sha256':sha(p),'independent_saved':True})
 views=read(H/'72视图完整指标.json');assert len(views)==72
 for v in views:
  ev=expectedviews[(v['id'],v['alias'])];assert v['metrics']==ev['metrics'] and v['counts']==ev['counts'] and v['source_sha256']==sha(H/'outputs'/(v['id']+'.json'))
 en=read(H/'18环境配对.json');assert len(en)==18 and Counter(x['branch'] for x in en)=={'B':6,'R':6,'C':6}
 assert len(read(H/'12_B_C配对.json'))==len(read(H/'12_B_R辅助配对.json'))==12
 assert len(read(H/'6组六分支逐seed.json'))==len(read(H/'行为与阶段差异.json'))==6 and len(read(H/'两状态等权.json'))==2
 for a in read(H/'行为与阶段差异.json'):
  assert not a['decision_signature']['equal'] and not a['B_post_credit_order']['equal'] and not a['B_nominal_anchor_order']['equal']
  assert not a['causal_fault_proven'] and a['necessary_detour_unknown'] and a['tier']==3
 for s in read(H/'两状态等权.json'):
  if s['base_id']=='large_Z':assert s['means']['B_raw_delta']==2 and s['means']['B_post_delta']>0 and s['means']['B_E_minus_R_E']>0
  else:assert s['means']['B_raw_delta']==0 and s['means']['B_post_delta']<0 and s['means']['B_E_minus_R_E']<0
 pre=read(H/'prechecks.json');assert pre['passed'] and len(pre['cases'])==6 and pre['fixed_stub_repair_attempts']==4 and pre['real_core_calls']==pre['real_R_calls']==pre['post_search_calls']==0
 assert not read(H/'prechecks_preparation_v01_failed.json')['passed'] and not read(H/'prechecks_preparation_v02_failed.json')['passed']
 assert read(H/'preparation_repairs.json')['repairs_used']==2 and ledger['pure_case_attempts']==10
 assert read(H/'调用与查询总账.json')['formal_aggregated_observed']['R_runtime']['BFS_started']==6
 assert read(H/'review_packet.json')['new_intervention_started'] is False
 for f in read(H/'figure_receipts.json'):assert sha(H/f['figure'])==f['sha256']
 assert read(H/'图版目视核验.json')['viewed_all'] is True
 checks.append('36 completed receipts / 72 views / 18 E-N and 12 B-C pairs; OFF, costs, positive and negative outcomes bound; no new core/R/post/geometry/BFS')
 root=ROOT/'当前进度与下一步.md';assert root.read_bytes().endswith((H/'root_before.md').read_bytes())
 final=H/'final_receipt.json'
 if final.exists():
  f=read(final)
  for p,d in f['files'].items():assert sha(H/p)==d,('seal',p)
  actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert actual==set(f['files']) and len(actual)==f['file_count']
  assert sha(root)==f['root_sha256'];checks.append(f'final seal {len(actual)} files and root progress intact')
 else:assert '--preseal' in sys.argv
 print(json.dumps({'passed':True,'mode':'sealed' if final.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'saved_processing_outputs':len(saved),'new_core_R_post_geometry_BFS':0,'writes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
