"""Re-audit saved evidence; never calls native.solve or post.process."""
from region_common import *
from collections import Counter
import traceback
from region_audit import audit
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def review():
 assert read(H/'regression_receipt.json')['passed'] and not (H/'old_review_receipt.json').exists();guard();start=time.perf_counter();plan=read(OLD/'plan.json');jobs={j['id']:j for j in plan['jobs']};ledger=[json.loads(z) for z in (OLD/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];order=[r['job'] for r in ledger if r['event']=='started' and r['kind']=='core'];assert len(order)==22
 receipts=[];counts=Counter();failed=None
 for jid in order:
  t=time.perf_counter();oldpath=OLD/'outputs'/(jid+'.json');r=read(oldpath);j=jobs[jid];row={'id':jid,'passed':False,'original_execution':{'status':r['status'],'passed':r['passed'],'eligible':r['eligible']},'review_status':'pending','saved_worker_sha256':sha(oldpath)}
  try:
   assert r['job']==j and r['input']==read(OLD/j['input']) and r['input_sha256']==sha(OLD/j['input'])
   assert sum(x['job']==jid and x['kind']=='post' and x['event']=='returned' for x in ledger)==1
   raw=r['native']['raw'];assert raw['status']=='core_complete';request=json.loads(r['post_request_utf8']);assert request['raw']==raw and request['input']==r['input'];assert json.loads(r['post_response_utf8'])==r['post']
   # The prior independent complete geometric and center-credit audit is intact
   # for all 22, including failed ON. Bind it, do not generate new post routes.
   g=r['independent'];assert g['passed'] and g['post']['passed'] and all(v['passed'] for v in g['views'].values())
   assert not any(r['timing'][k] for k in ('native_late','raw_stage_late','post_late','combined_late'))
   decision=audit(r['input'],raw,j['arm']=='ON');assert decision['passed'];counts.update(decision['counts'])
   if jid=='formal__G1-A__ON':assert not r['passed'] and r['last_stage']=='independent_review'
   else:assert r['passed'] and r['eligible']
   row.update(passed=True,review_status='v02_saved_result_semantics_passed',scientific_inclusion='old_saved_formal_pair_arm' if j['phase']=='formal' else 'history_or_OFF_gate_evidence_only',decision=decision,independent_geometric_evidence='hash-bound reuse of v01 receipt; no new geometry or post',old_online_timing=r['timing'],field_sha256={k:digest(v) for k,v in {'input':r['input'],'native_raw':raw,'trace':raw['trace'],'rule':raw.get('rule'),'post_request_utf8':r['post_request_utf8'],'post_response_utf8':r['post_response_utf8'],'prior_geometric_receipt':g,'source_bindings':r['loaded_sources'],'entry_log':ledger}.items()})
  except BaseException as e:row.update(review_status='failed_stop',failure=repr(e),traceback=traceback.format_exc());failed=jid
  row['review_seconds']=time.perf_counter()-t;receipts.append(row);dump(H/'audits/old'/(jid+'.json'),row);print('REVIEW',jid,row['passed'],row.get('failure',''),flush=True)
  if failed:break
 allpass=len(receipts)==22 and all(r['passed'] for r in receipts);result=dict(passed=allpass,reviewed=len(receipts),expected=22,failed_id=failed,real_core=0,real_post=0,new_planner_routes=0,new_post_generated_routes=0,main_external_independent_BFS=dict(counts),new_geometry_or_credit_queries=0,geometric_credit_receipts_reused=sum(r['passed'] for r in receipts),seconds=time.perf_counter()-start,G1_A_saved_pair_reusable=allpass,old_execution_status_changed=False)
 dump(H/'old_review_receipt.json',result);guard();return allpass
if __name__=='__main__':raise SystemExit(0 if review() else 1)
