"""Read-only frozen-source and saved-receipt verification. No solver imports."""
from common import *
from collections import Counter
import sys,datetime,hashlib
def main():
 checks=[]
 for name in ('input_freeze.json','active_freeze.json'):
  for p,d in read(H/name)['files'].items() if name=='input_freeze.json' else read(H/name).items():assert sha(H/p)==d,(name,p)
  checks.append(name+' intact')
 guards=read(H/'source_guards.json')
 for p,d in guards.items():assert sha(p)==d,p
 checks.append(str(len(guards))+' old source hashes intact')
 b=read(H/'bindings.json');assert sha(b['accepted_OFF_worker_file'])==b['accepted_OFF_worker_sha256']
 body=(H/'source_snapshot/accepted_OFF_worker.py.txt').read_text(encoding='utf-8')
 assert hashlib.sha256(body.encode()).hexdigest()==b['accepted_worker_function_sha256']
 sel=read(H/'selection.json');plan=read(H/'plan.json');status=read(H/'status.json');ledger=read(H/'ledger.json')
 assert len(sel['selected'])==len({x['base_id'] for x in sel['selected']})==plan['m']==6
 assert len({x['shape'] for x in sel['selected']})==3 and sel['counts']['source_states_scanned']<=54
 assert all(len(x['candidate_checks'])<=20 for x in sel['scanned'])
 assert len(plan['jobs'])==108 and Counter(j['branch'] for j in plan['jobs'])=={'B':36,'R':36,'C':36}
 assert len(status['completed'])==108 and status['failure'] is None and status['not_run']==[]
 assert ledger['attempted_processing']==108 and ledger['core_attempted']==72 and ledger['R_attempted']==36
 assert ledger['technical_core']==ledger['warmup']==0
 events=[json.loads(x) for x in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(events)==216 and len({e['id'] for e in events if e['event']=='started'})==108
 assert [e['id'] for e in events if e['event']=='started']==[j['id'] for j in plan['jobs']]
 assert all(e.get('success') is True for e in events if e['event']=='ended')
 for c in sel['selected']:
  n,e=read(H/c['N']),read(H/c['E']);h=read(H/c['history'])
  assert all(n[k]==e[k] for k in n if k!='free') and ps(n['free'])-ps(e['free'])==ps(c['obstacles'])
  assert not (ps(n['targets'])-ps(n['covered']))&ps(c['obstacles'])
  assert h['old_suffix_N_legal'] and h['old_suffix_E_invalid_interiors']
  assert n['old_route']==h['suffix'] and ps(n['covered'])==ps(h['H']) and n['current']==h['prefix'][-1] and n['previous']==h['prefix'][-2]
  for x in h['source_files'].values():assert sha(x['path'])==x['sha256']
 checks.append('6 common snapshots, old history/suffix and strict-interior blockage receipts bound; no geometry or reachability replay')
 rr={};saved=[]
 for j in plan['jobs']:
  p=H/'outputs'/(j['id']+'.json');x=read(p);assert x['job']==j and x['passed'] and x['main_passed'] and x['independent']['passed']
  assert x['input']==read(H/j['input']) and x['native']==read(H/'outputs'/(j['id']+'_native_raw.json'))
  postraw=read(H/'outputs'/(j['id']+'_post_raw.json'))
  assert x['post']==json.loads(x['post_response_utf8']) and postraw['response_utf8']==x['post_response_utf8'] and postraw['envelope']==x['post_envelope']
  assert json.dumps(postraw['request'],ensure_ascii=False,separators=(',',':'))==x['post_request_utf8']
  assert hashlib.sha256(x['post_request_utf8'].encode()).hexdigest()==x['independent']['post']['input_sha256']
  assert hashlib.sha256(x['post_response_utf8'].encode()).hexdigest()==x['independent']['post']['output_sha256']
  assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0} and x['native_counts_actual'] is None and x['native_observation']['counts'] is None
  assert x['identity_before']==x['identity_after'] and x['identity_before']['primary']['file']!=x['identity_before']['independent']['file']
  assert x['timing']['termination']=='natural' and x['post_envelope']['fallback'] is None
  assert all(x['timing'][k] is False for k in ('native_late','raw_stage_late','combined_late','post_late'))
  for a,v in x['views'].items():
   m=v['metrics'];assert m['missing']==m['deferred']==0 and m['return_success'] and m['active_coverage']==m['published_coverage']==1
   assert v['path'][0]==x['input']['current'] and v['path'][-1]==x['input']['base']
   assert m['length']<=x['input']['distance_budget'] and x['independent']['views'][a]['passed']
  if j['branch']=='R':
   assert x['native']['repair_counts']['entry_started']==x['native']['repair_counts']['entry_returned']==1 and x['independent']['repair_structure']['passed']
   key=j['case'],j['env'];r=x['native']['raw']['route'];assert key not in rr or rr[key]==r;rr[key]=r
  else:assert x['native']['method']==j['method'] and x['native']['seed']==j['seed']
  saved.append({'id':j['id'],'sha256':sha(p),'independent_saved':True})
 assert read(H/'prechecks.json')['passed'] and len(read(H/'prechecks.json')['cases'])==12
 assert read(H/'prechecks_preparation_v01_failed.json')['passed'] is False and read(H/'preparation_repairs.json')['repairs_used']==1
 s=read(H/'summary.json');a=read(H/'行为补充与阶段分解.json');raw=read(H/'原生与直达变化澄清.json')
 assert len(read(H/'216视图完整指标.json'))==216 and len(read(H/'同状态同seed六分支配对.json'))==18
 assert s['same_B_nominal_order_pairs']==s['same_B_credit_order_pairs']==s['same_B_prefix_through_last_anchor_pairs']==s['same_B_R_post_E_pairs']==18
 assert s['tier_counts']=={'2':18} and a['all18_full_trace_equal'] and a['all18_delta_only_saved_return_stage']
 assert all(p['B_raw_delta']==0 and p['R_raw_delta']==2 for p in raw['pairs'])
 assert read(H/'review_packet.json')['new_intervention_recommended'] is False
 checks.append('108 independent receipts / 216 views / 18 complete pairs; budgets and OFF counts; full saved R repeat routes, no replay')
 root=ROOT/'当前进度与下一步.md';assert root.read_bytes().endswith((H/'root_before.md').read_bytes())
 final=H/'final_receipt.json'
 if final.exists():
  f=read(final)
  for p,d in f['files'].items():assert sha(H/p)==d,p
  actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='final_receipt.json'};assert actual==set(f['files'])
  assert sha(root)==f['root_sha256'];checks.append('final seal '+str(len(actual))+' files and root progress intact')
 else:assert '--preseal' in sys.argv,'not sealed'
 print(json.dumps({'passed':True,'mode':'sealed' if final.exists() else 'preseal','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'saved_processing_outputs':len(saved),'new_core_calls':0,'new_R_calls':0,'new_post_calls':0,'new_geometry_calls':0,'new_BFS_calls':0,'writes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
