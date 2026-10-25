"""Stdlib read-only saved-evidence verification; no planner/post/audit/BFS imports."""
from pathlib import Path
from fractions import Fraction as Q
from collections import Counter
import json,hashlib,math,time,ast,re
H=Path(__file__).resolve().parent;ROOT=H.parent;OLD=ROOT/'障碍后片区两阶段规则有限验证_v0.1_20261023'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def length_terms(path):
 total=Counter()
 for a,b in zip(path,path[1:]):
  n=sum((a[j]-b[j])**2 for j in (0,1));assert type(n) is int and n>0
  outside=1;r=n;factor=2
  while factor*factor<=r:
   while r%(factor*factor)==0:r//=factor*factor;outside*=factor
   factor+=1
  total[r]+=outside
 return dict(total)
def loaded_terms(cert):return {t['r']:Q(t['c']['n'],t['c']['d']) for t in cert['exact']['terms']}
def inspect_view(v):
 path=v['path'];m=v['metrics'];terms=length_terms(path);assert terms==loaded_terms(m['length_certificate'])
 cert=m['length_certificate'];scale=1<<cert['interval_bits'];lo=hi=Q(0)
 for r,c in terms.items():
  k=math.isqrt(r*scale*scale);lo+=c*Q(k,scale);hi+=c*Q(k if k*k==r*scale*scale else k+1,scale)
 assert Q(cert['low']['n'],cert['low']['d'])==lo and Q(cert['high']['n'],cert['high']['d'])==hi
 assert float(lo)-1e-12<=m['length']<=float(hi)+1e-12
 turns=Counter();angle=0.;dirs=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:])]
 for a,b in zip(dirs,dirs[1:]):
  dot=a[0]*b[0]+a[1]*b[1];cross=a[0]*b[1]-a[1]*b[0]
  if cross or dot<0:turns['total']+=1;turns['90' if dot==0 else '180' if cross==0 else 'other']+=1;angle+=math.atan2(abs(cross),dot)
 assert dict(turns)==m['turns'] and abs(angle-m['total_turn_radians'])<1e-12
 new={tuple(e['cell']) for e in v['events'] if e['new']};assert len(new)==m['new_credit']==m['remaining_before']
 assert m['missing']==m['deferred']==0 and m['return_success']
def verify(sealed=True):
 begin=time.perf_counter();guards=0
 for p,v in read(H/'active_freeze.json').items():assert sha(H/p)==v,('new source/input changed',p);guards+=1
 for p,v in read(H/'runtime_guards.json').items():assert sha(p)==v,('runtime changed',p);guards+=1
 for p,v in read(H/'old_package_guards.json').items():assert sha(OLD/p)==v,('old file changed',p);guards+=1
 for p,v in read(OLD/'source_guards.json').items():assert sha(p)==v,('old external source changed',p);guards+=1
 for b in read(H/'immutable_bindings.json'):assert sha(H/b['copy'])==sha(OLD/b['old'])==b['sha256']
 plan=read(H/'plan.json');reg=read(H/'regression_receipt.json');review=read(H/'old_review_receipt.json');assert reg['passed'] and reg['fixed_cases']==reg['executed_cases']==16 and review['passed'] and review['reviewed']==22
 for n in range(1,17):assert read(H/'regression'/(str(n).zfill(2)+'.json'))['passed']
 oldledger=[json.loads(z) for z in (OLD/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];ledger=[json.loads(z) for z in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];oldcore=[r['job'] for r in oldledger if r['event']=='started' and r['kind']=='core'];assert len(oldcore)==22
 for k in ('core','post'):
  starts=[r['job'] for r in ledger if r['event']=='started' and r['kind']==k];returns=[r['job'] for r in ledger if r['event']=='returned' and r['kind']==k];assert starts==returns==[j['id'] for j in plan['jobs']] and len(starts)==len(set(starts))==16
 assert len([r for r in oldledger if r['event']=='started' and r['kind']=='post'])+16==38
 oldplan=read(OLD/'plan.json');qualified=plan['qualified_slots'];expected=[j for j in oldplan['jobs'] if j['phase']=='formal' and j['slot'] in qualified and j['slot']!='G1-A'];assert len(expected)==16
 assert [j['old_job_id'] for j in plan['jobs']]==[j['id'] for j in expected]
 views=0;source_data={}
 for jid in oldcore:
  r=read(OLD/'outputs'/(jid+'.json'));a=read(H/'audits/old'/(jid+'.json'));assert a['passed'] and a['saved_worker_sha256']==sha(OLD/'outputs'/(jid+'.json')) and a['decision']['passed']
  assert a['original_execution']==dict(status=r['status'],passed=r['passed'],eligible=r['eligible'])
  for key,v in (('input',r['input']),('native_raw',r['native']['raw']),('trace',r['native']['raw']['trace']),('rule',r['native']['raw'].get('rule')),('post_request_utf8',r['post_request_utf8']),('post_response_utf8',r['post_response_utf8']),('prior_geometric_receipt',r['independent']),('source_bindings',r['loaded_sources']),('entry_log',oldledger)):assert digest(v)==a['field_sha256'][key]
  source_data[jid]=r
 for j in plan['jobs']:
  r=read(H/'outputs/worker'/(j['id']+'.json'));assert r['job']==j and r['passed'] and r['eligible'] and r['decision_audit']['passed'] and r['independent']['passed'];assert read(H/'outputs/parent'/(j['id']+'.json'))['returncode']==0
  assert read(H/'audits/new'/(j['id']+'__decision.json'))==r['decision_audit'];assert read(H/'audits/new'/(j['id']+'__geometry.json'))==r['independent'];assert sha(H/j['input'])==sha(OLD/j['input'])==r['input_sha256']
  source_data[j['id']]=r
 for r in source_data.values():
  assert r['independent']['passed']
  post=r['independent']['post'];assert post['input_sha256']==hashlib.sha256(r['post_request_utf8'].encode()).hexdigest() and post['output_sha256']==hashlib.sha256(r['post_response_utf8'].encode()).hexdigest()
  for v in r['views'].values():inspect_view(v);views+=1
  t=r['timing'];assert abs(t['combined_end_to_end']-t['raw_common_end_to_end']-t['post_increment'])<1e-9
  assert t['combined_end_to_end']>=t['raw_common_end_to_end']>=t['native_entry_seconds'] and not any(t[k] for k in ('native_late','raw_stage_late','post_late','combined_late'))
 pairs=read(H/'nine_pairs.json');assert len(pairs)==9 and sum(p['pair_evidence']=='old_saved_reaudited_pair' for p in pairs)==1
 assert source_data['formal__G1-A__ON']['passed'] is False and source_data['formal__G1-A__ON']['status']=='implementation_or_contract_error'
 for p in pairs:
  prefix='formal__' if p['id']=='G1-A' else 'v02__formal__';a=source_data[prefix+p['id']+'__ORIGINAL'];z=source_data[prefix+p['id']+'__ON'];assert not p['activated'] and p['checked'] and all(p['same'].values())
  assert a['native']['raw']['route']==z['native']['raw']['route'] and a['post']['vertices']==z['post']['vertices'] and a['post']['credit_witnesses']==z['post']['credit_witnesses']
  for v in ('A','B'):assert length_terms(a['views'][v]['path'])==length_terms(z['views'][v]['path']) and p['deltas'][v]['sign']==0 and p['deltas'][v]['certificate']['exact']['terms']==[] and a['views'][v]['metrics']==z['views'][v]['metrics']
  assert all(p['mechanism'][k] is None for k in ('OTHER_no_active_S_choice','native_S_retained_to_release','post_finishes_S'))
 assert len(read(H/'all_metrics.json'))==len(read(H/'three_column_account.json'))==38
 assert {p['id'] for p in read(H/'permanent_missing_slots.json')}=={'G2-B','G5-B','G6-B'}
 gate=read(H/'continuation_gate.json');assert not gate['passed'] and not gate['original_12_pair_complete'] and gate['complete_six_base_equalweight_difference'] is None
 costs=read(H/'cost_and_query_account.json');assert costs['old_saved_result_review']['main_external_independent_BFS']==review['main_external_independent_BFS']
 assert len(read(H/'new_version_timing_pairs.json'))==8 and not any(x['id']=='G1-A' for x in read(H/'new_version_timing_pairs.json'))
 assert read(H/'old_archive_corrections.json')['irrecoverable_worker_JSON'] and read(H/'old_archive_corrections.json')['clock_or_query_counts_missing'] is None
 before=(H/'root_before.md').read_bytes();after=(H/'root_after.md').read_bytes();assert before==(OLD/'root_after.md').read_bytes() and sha(H/'root_before.md')==read(OLD/'final_receipt.json')['root_sha256'];assert after.endswith(before) and (ROOT/'当前进度与下一步.md').read_bytes()==after
 links=0
 for name in ('00_通俗接续结果与三栏账.md','review_packet.md'):
  for ref in re.findall(r'\]\(([^)]+)\)',(H/name).read_text(encoding='utf-8')):assert (H/ref).is_file();links+=1
 sealed_files=0
 if sealed:
  final=read(H/'final_receipt.json');assert final['root_sha256']==sha(ROOT/'当前进度与下一步.md')
  for p,v in final['files'].items():assert sha(H/p)==v,('sealed changed',p);sealed_files+=1
 return dict(passed=True,scope='old/new immutable hashes and root suffix chain; separate old execution vs saved-evidence review vs new real entries; 16 type-regression receipts; complete ledgers; 76 saved-view independent radical-length/turn/credit-ledger arithmetic; no new core/post/BFS/geometry credit searches; actual semantic BFS review separately logged',guards_checked=guards,new_core=16,new_post=16,cumulative_core=38,cumulative_post=38,old_saved_returns_reviewed=22,saved_views_recomputed=views,valid_physical_pairs=9,old_saved_review_pairs=1,new_execution_pairs=8,activated_pairs=0,all_post_deltas_zero=True,continuation_gate_passed=False,links_checked=links,sealed_files=sealed_files,seconds=time.perf_counter()-begin)
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
