"""Read-only: original prefix re-scan, independent Fraction/isqrt physical
length reconstruction and decisions, hashes, saved independent geometry receipts.
No planner/post/geometry/BFS imports or calls.
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction as Q
from math import isqrt
import hashlib,json,time
H=Path(__file__).resolve().parent;ROOT=H.parent;C=Counter()
def read(p):
 b=Path(p).read_bytes();C['files_read']+=1;C['bytes_read']+=len(b);return json.loads(b.decode('utf-8-sig'))
def sha(p):
 b=Path(p).read_bytes();C['hash_files']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def ps(x):return set(map(tuple,x))
def coefficients(c):
 out=Counter()
 for x in c['exact']['terms']:out[x['r']]+=Q(x['c']['n'],x['c']['d']);C['saved_coefficients']+=1
 return {r:v for r,v in out.items() if v}
def add(*parts):
 out=Counter()
 for sign,terms in parts:
  for r,c in terms.items():out[r]+=sign*c;C['independent_coefficient_additions']+=1
 return {r:c for r,c in out.items() if c}
def lengths(path):
 result=Counter()
 for a,b in zip(path,path[1:]):
  n=sum((x-y)**2 for x,y in zip(a,b));C['physical_length_edges']+=1
  if not n:continue
  factor=1
  for i in range(1,isqrt(n)+1):
   C['square_factor_trials']+=1
   if n%(i*i)==0:factor=i
  result[n//(factor*factor)]+=Q(factor)
 return dict(result)
def interval(d,bits=160):
 S=1<<bits;lo=hi=Q(0)
 for r,c in d.items():
  k=isqrt(r*S*S);a=Q(k,S);b=a if k*k==r*S*S else Q(k+1,S);lo+=c*(a if c>0 else b);hi+=c*(b if c>0 else a);C['integer_root_bounds']+=1
 return lo,hi
def sign(d):
 if not d:return 0
 lo,hi=interval(d);assert lo>0 or hi<0,'numeric_uncertain';return 1 if lo>0 else -1
def display(d):return float(sum(interval(d))/2)
def close(a,b):assert abs(a-b)<1e-9,(a,b)
def verify():
 start=time.perf_counter();checks=Counter();m=read(H/'manifest.json');assert len(m['slots'])==38
 for name,local in [('freeze.json',True),('source_guards.json',False)]:
  for p,v in read(H/name).items():assert sha(H/p if local else p)==v,(name,p)
 seal=read(H/'predictions_seal.json');assert seal['predictions_sha256']==sha(H/'predictions.json') and seal['manifest_sha256']==sha(H/'manifest.json') and seal['freeze_sha256']==sha(H/'freeze.json');assert seal['controller_sha256']==sha(H/'run_batch.py')==read(H/'controller_registration.json')['source_sha256']
 for p,v in seal['files'].items():assert sha(H/p)==v,p
 summary=read(H/'summary.json');assert summary['truth_released_utc']>=seal['sealed_utc'] and summary['prediction_seal_sha256']==sha(H/'predictions_seal.json')
 technical=read(H/'technical/round1.json');assert technical['passed'] and technical['unique_cases']==18 and technical['attempts']==18 and all(t['passed'] for t in technical['cases']);assert technical['core_calls']==technical['public_post_calls']==0
 status=read(H/'status.json');assert status['failure'] is None and not status['not_run'] and len(status['completed'])==38 and len(set(status['attempted']))==38;assert status['core_calls']==0 and status['post_calls']==38 and status['new_tails']==38
 log=[json.loads(s) for s in (H/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];assert len(log)==76 and sum(x['event']=='started' for x in log)==38 and sum(x['event']=='completed' for x in log)==38
 assert len(list((H/'logs').glob('*.post_started')))==38 and len(list((H/'outputs').glob('*.claim')))==38
 struct=ROOT/'障碍后正反例任务次序与收尾结构对照_v0.1_20261023';ixs={x['key']:x for x in read(struct/'pair_index.json')};reg={s:{r['id']:r for r in read(ROOT/p/'state_registry.json')} for s,p in [('base','障碍后接续假设有限扩样_v0.1_20261023'),('variants','障碍后接续正反例受控变体_v0.1_20261023')]};original={};estimates={};totals=Counter();auditcounts=Counter();origins={};loaded={}
 for slot in m['slots']:
  key=slot['key'];arm=slot['arm'];ix=ixs[key];r=read(struct/ix['file']);src=read(r['source'][arm]);assert sha(r['source'][arm])==r['source'][arm+'_sha256'];original[key,arm]=src;packet=read(H/slot['crop']);loaded[key,arm]=packet;out=read(H/'outputs'/(slot['id']+'.json'));assert out['passed'] and out['eligible'] and out['new_core_calls']==0 and out['post_calls']==1 and out['crop_sha256']==sha(H/slot['crop']);assert set(packet)==set(m['input_whitelist']) and packet['event']==src['input'] and packet['old_order']==reg[ix['dataset']][ix['id']]['old_order'];c=packet['event'];F=ps(c['free']);tr=src['diagnostic']['trigger'];raw=src['native']['raw']['route'];k=tr['route_index'];q=tuple(tr['chosen_goal']);assert packet['selected_q']==list(q);assert packet['common_prefix']==raw[:k+1]
  pending=ps(c['targets'])-ps(c['covered'])-ps(raw[:k+1]);assert pending==ps(packet['choice_state']['pending']);i=k;local=0;arrival=tuple(raw[k])==q
  while True:
   x,y=raw[i];has_local=any(z in pending and z in F for z in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)));C['prefix_stop_tests']+=1
   reason='all_pending_collected' if not pending else 'total_64' if i-k>=64 else 'next_recovery_after_q' if arrival and not has_local else 'local_16' if arrival and local>=16 else None
   if reason:break
   i+=1
   if arrival:local+=1
   pending.discard(tuple(raw[i]));arrival=arrival or tuple(raw[i])==q
  st=packet['stop_state'];assert packet['finite_prefix']==raw[k:i+1] and st['reason']==reason and st['pending']==[list(z) for z in sorted(pending)] and st['current']==raw[i] and st['previous']==(raw[i-1] if i>k else tr['previous']) and st['edges']==i-k and st['local_edges']==local and st['q_arrived']==arrival;checks['independent_original_prefix_and_stop']+=1
  assert read(H/'crop_audits'/(slot['id']+'.json'))['passed'];audit=read(H/'audits'/(slot['id']+'.json'));assert audit['passed'] and audit['post']['passed'];auditcounts.update(audit['counts']);assert audit['post']['input_sha256']==hashlib.sha256(out['post_request_utf8'].encode()).hexdigest() and audit['post']['output_sha256']==hashlib.sha256(out['post_response_utf8'].encode()).hexdigest()
  route=out['tail']['route'];cursor=0;vi=0;seen=set();counts=Counter();pend=set(pending);old=packet['old_order'];assert pend<=ps(old)
  for rank,goal in enumerate(old):
   goal=tuple(goal);dup=goal in seen;seen.add(goal);counts['old_order_entries_scanned']+=1;counts['old_duplicate_entries']+=int(dup)
   if dup or goal not in pend:counts['old_entries_skipped']+=1;continue
   v=out['tail']['visits'][vi];vi+=1;assert v['old_rank']==rank and v['goal']==list(goal) and v['kind']=='task' and v['tail_start']==cursor;end=v['tail_stop'];part=route[cursor:end+1];assert part[0]==route[cursor] and part[-1]==list(goal) and v['pending_before']==[list(z) for z in sorted(pend)];new=pend&ps(part);assert v['new_tasks']==[list(z) for z in sorted(new)];pend-=new;cursor=end;counts['task_path_queries']+=1;counts['tail_new_tasks']+=len(new);counts['incidental_tasks']+=len(new-{goal})
  assert not pend;v=out['tail']['visits'][vi];assert vi+1==len(out['tail']['visits']) and v['kind']=='return' and v['goal']==c['base'] and v['tail_start']==cursor and v['tail_stop']==len(route)-1;counts['return_path_queries']=1;counts['path_queries']=vi+1;counts['tail_new_edges']=len(route)-1
  for a,b in zip(route,route[1:]):assert tuple(a) in F and tuple(b) in F and sum(abs(x-y) for x,y in zip(a,b))==1
  for name,val in counts.items():assert out['counts'][name]==val,(slot['id'],name)
  joined=packet['common_prefix']+packet['finite_prefix'][1:]+route[1:];assert joined==out['raw']['route'] and len(joined)-1==out['Jhat_raw'];assert ps(joined)<=F and ps(c['targets'])<=ps(c['covered'])|ps(joined);assert joined[0]==c['current'] and joined[-1]==c['base'] and len(joined)-1<=c['distance_budget'];assert sum(abs(x-y) for a,b in zip(joined,joined[1:]) for x,y in zip(a,b))==len(joined)-1;assert not out['post_envelope']['late'] and out['post_envelope']['fallback'] is None
  C['native_substitute_edges']+=len(joined)-1;checks['old_order_incidental_join_contract']+=1
  estimates[key,arm]=lengths(out['post']['vertices']);truth=lengths(src['post']['vertices']);assert estimates[key,arm]==coefficients(out['Jhat_certificate']) and truth==coefficients(src['views']['B']['metrics']['length_certificate']);close(display(estimates[key,arm]),out['Jhat_post']);origins[key,arm]=truth;checks['physical_estimate_and_truth_lengths']+=2
  allowed_data={str((H/slot['crop']).resolve()),str((H/'manifest.json').resolve()),str((H/'freeze.json').resolve())}
  for p in out['read_guard']['read_paths']:
   pp=Path(p);assert p in allowed_data or pp.suffix in ('.py','.pyc') and pp.is_relative_to(H) or pp.is_relative_to(ROOT/'运行环境/python'),('unexpected estimator data read',p)
  assert out['read_guard']['counts']['blocked_reads']==0
  for name,val in out['counts'].items():
   if type(val) is int:totals[name]+=val
   elif isinstance(val,dict):totals.update({name+'.'+z:n for z,n in val.items() if type(n) is int})
 joined_rows={r['key']:r for r in read(H/'joined_results.json')};dataset_counts={s:Counter() for s in ('base','variants')};selected_sums={s:{} for s in dataset_counts};regret_sums={s:{} for s in dataset_counts}
 for p in read(H/'predictions.json'):
  key=p['key'];row=joined_rows[key];dataset=ixs[key]['dataset'];dh=add((1,estimates[key,'ALT1']),(-1,estimates[key,'OFF']));dt=add((1,origins[key,'ALT1']),(-1,origins[key,'OFF']));es={a:add((1,estimates[key,a]),(-1,origins[key,a])) for a in ('OFF','ALT1')};de=add((1,dh),(-1,dt));assert dh==coefficients(p['delta_hat_certificate'])==coefficients(row['delta_hat_certificate']) and dt==coefficients(row['delta_true_certificate']);assert de==add((1,es['ALT1']),(-1,es['OFF']))==coefficients(row['error_difference_certificate']);choice='ALT1' if sign(add((1,dh),(1,{1:Q(1,100000000)})))<0 else 'OFF';assert choice==p['prediction']['choice']==row['prediction']['choice'];sg=sign(dt);assert sg==row['true_sign'];selected=dt if choice=='ALT1' else {};regret=add((1,selected),(-1,dt if sg<0 else {}));assert coefficients(row['actual_selected_certificate'])==selected and coefficients(row['regret_certificate'])==regret;assert sign(regret)>=0
  for name,val in [('delta_hat',dh),('delta_true',dt),('error_difference',de),('actual_selected_delta',selected),('two_candidate_regret',regret)]:close(row[name],display(val))
  for a in ('OFF','ALT1'):assert coefficients(row['arms'][a]['error_certificate'])==es[a];close(row['arms'][a]['error'],display(es[a]))
  label=('caught_improvement' if choice=='ALT1' else 'missed_improvement') if sg<0 else ('wrongly_accepted_deterioration' if choice=='ALT1' else 'correctly_rejected_deterioration') if sg>0 else ('equal_true_biased_q1' if choice=='ALT1' else 'equal_true_retained_q0');assert label==row['classification'];dataset_counts[dataset][label]+=1;selected_sums[dataset]=add((1,selected_sums[dataset]),(1,selected));regret_sums[dataset]=add((1,regret_sums[dataset]),(1,regret));checks['independent_error_ranking_choice_regret']+=1
 for ds in dataset_counts:
  s=summary['datasets'][ds];assert dict(dataset_counts[ds])==s['classification'];assert coefficients(s['selected_delta_sum_certificate'])==selected_sums[ds] and coefficients(s['regret_sum_certificate'])==regret_sums[ds];assert s['selected_sum_sign']==sign(selected_sums[ds]);close(display(selected_sums[ds]),s['selected_delta_sum'])
 assert summary['gate']['passed'] is False and summary['gate']['original_I_suggest_q1'] is False and summary['gate']['original_T_and_two_A_avoid_q1'] is False and summary['gate']['base_selected_sum_strictly_negative'] is True
 workload=read(H/'workload.json');assert dict(totals)==workload['main_counts'] and dict(auditcounts)==workload['independent_counts'];assert workload['calls']==dict(fixed_prefix_extractions=38,new_tails=38,new_public_post=38,new_views=76,new_complete_core=0,new_true_finite_core=0,new_history_core=0)
 before=(H/'root_before.md').read_bytes();assert read(struct/'final_receipt.json')['root_sha256']==sha(H/'root_before.md');now=(ROOT/'当前进度与下一步.md').read_bytes();assert now.endswith(before)
 if (H/'root_after.md').exists():assert now==(H/'root_after.md').read_bytes()
 else:assert now==before
 sealed=0
 if (H/'final_receipt.json').exists():
  final=read(H/'final_receipt.json')
  for p,v in final['files'].items():assert sha(H/p)==v,p;sealed+=1
  assert final['root_sha256']==sha(ROOT/'当前进度与下一步.md')
 result=dict(passed=True,checks=dict(checks),counts=dict(C),pairs=19,arms=38,new_substitute_views_verified=76,saved_complete_candidates=38,predictions_sealed_before_truth=True,gate_passed=False,root_chain=True,sealed_files_checked=sealed,new_core=0,new_post=0,new_BFS=0,new_geometry=0,new_candidate_generation=0,seconds=time.perf_counter()-start,scope='read-only prefix/set/accounting reconstruction and independent physical-vertex integer/rational length certification; saved independent geometry/credit receipts hash bound')
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
