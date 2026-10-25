"""Read-only hash, saved certificate, set and arithmetic checks. No searches."""
from pathlib import Path
import json,hashlib
from fractions import Fraction as Q
from collections import Counter
H=Path(__file__).resolve().parent;ROOT=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ps(x):return set(map(tuple,x))
def sig(c,old):return hashlib.sha256(json.dumps(dict(input={k:v for k,v in c.items() if k!='name'},old_order=old,seed=20261020),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify():
 checks=Counter();hashes=0
 for group in ('active_freeze.json','runtime_guards.json','source_guards.json','qualification_freeze.json'):
  for p,v in read(H/group).items():
   file=Path(p) if Path(p).is_absolute() else H/p;assert sha(file)==v,(group,p);hashes+=1
 old=Path(read(H/'plan.json')['old_package']);f=read(old/'final_receipt.json');assert f['root_sha256']==sha(H/'root_before.md')
 receipt=read(H/'source_snapshot/旧包成功核验回执.json');assert receipt['passed'] and receipt['final_receipt_sha256']==sha(old/'final_receipt.json')
 for p in ('expand_native.py','expand_hook.py','decision_audit.py','analysis_metrics.py','worker.py'):assert sha(H/p)==sha(old/p);checks['byte_identical_algorithm_files']+=1
 expected=(old/'common.py').read_text(encoding='utf-8').replace('len(starts)<42','len(starts)<36').replace("cap=6 if phase=='history' else 12","cap=0 if phase=='history' else 12")
 assert (H/'common.py').read_text(encoding='utf-8')==expected
 rows=read(H/'state_registry.json');assert len(rows)==12 and [r['id'] for r in rows]==[r['id'] for r in read(H/'plan.json')['slots']]
 sources={x['id']:x for x in read(H/'source_bindings.json')};pairs={p['id']:p for p in read(H/'pairs.json')};derived={p['id']:p for p in read(H/'derived_pairs.json')};seen={sig(read(old/r['input']),r['old_order']) for r in read(old/'state_registry.json')}
 for row in rows:
  src=sources[row['origin']];hist=read(src['history_output']);P=ps(hist['input']['published_targets']);oldc=read(src['old_input']);v=hist['post']['vertices'];refedge=hist['post']['edges'][src['fixed_global_edge']];assert [refedge['a'],refedge['b']]==src['edge_vertices'] and [refedge['left'],refedge['right']]==src['source_interval']
  if row['kind']=='B':
   k=row.get('cut')
   if k is not None:
    HH={tuple(x['point']) for x in hist['post']['credit_witnesses'] if x['edge']<k};assert HH==ps(row['H']) and v[k]==row['current'];assert len(HH)>=row['threshold']
    # Independent earliest cut scan of saved validated credit rows only.
    for earlier in range(1,k):
     done={tuple(x['point']) for x in hist['post']['credit_witnesses'] if x['edge']<earlier};a,z=v[earlier-1],v[earlier]
     assert not (len(done)>=row['threshold'] and tuple(z) in P and sum(abs(x-y) for x,y in zip(a,z))==1 and len(P-done)>=2)
    checks['B_saved_cut_mapping']+=1
   if row['status']=='cut_past_reference_block':assert row['cut']>src['fixed_global_edge'];checks['past_block_rejections']+=1
   if row['status']=='pending_target_blocked':assert tuple(src['old_obstacle']) in P-ps(row['H']);checks['pending_target_rejection']+=1
  if row['status']!='qualified':assert row['id'] not in pairs;continue
  c=read(H/row['input']);F=ps(c['free']);HH=ps(c['covered']);U=P-HH;assert ps(c['targets'])==P&F and ps(c['targets'])-HH==U and not P-F-HH
  assert sig(c,row['old_order'])==row['physical_signature'] and sig(c,row['old_order']) not in seen;seen.add(sig(c,row['old_order']));checks['unique_new_E']+=1
  if row['kind']=='A':
   assert HH==ps(oldc['covered']) and U==ps(oldc['targets'])-ps(oldc['covered']) and c['current']==oldc['current'] and c['previous']==oldc['previous'] and c['old_route']==oldc['old_route'] and row['old_order']==src['old_registry']['old_order']
   assert row['blocked_old_post']['edge']==src['fixed_global_edge'] and row['selected_obstacle']!=src['old_obstacle'];checks['A_same_edge_and_state']+=1
  else:assert row['selected_obstacle']==src['old_obstacle'] and c['free']==oldc['free'];checks['B_same_obstacle']+=1
  col=row['blocked_old_post'];w=col['interval'];t=Q(w['midpoint']['n'],w['midpoint']['d']);lo=Q(w['lower']['n'],w['lower']['d']);hi=Q(w['upper']['n'],w['upper']['d']);assert 0<=lo<t<hi<=1 and col['pending_at_edge_end']>=2
  edge=hist['post']['edges'][col['edge']]
  for j,z in enumerate(w['point']):assert Q(z['n'],z['d'])==Q(edge['a'][j])+t*(edge['b'][j]-edge['a'][j]) and abs(Q(z['n'],z['d'])-row['selected_obstacle'][j])<Q(1,2)
  assert row['independent_qualification']['passed'] and row['independent_qualification']['invalid_post_edges'][0]==col['edge'];checks['collision_and_saved_independent']+=1
  outs={arm:read(H/'outputs'/(row['id']+'__'+arm+'.json')) for arm in ('REF','OFF','ALT1')}
  for o in outs.values():assert o['eligible'] and o['passed'] and o['independent']['passed'] and o['decision_audit']['passed'] and o['post_envelope']['fallback'] is None and o['input']==c;checks['processing_reviews']+=1
  assert all(outs['OFF']['off_equivalence'].values()) and outs['ALT1']['decision_audit']['authorized_exceptions']==1;checks['OFF_equivalence_and_one_ALT']+=1
  tr=outs['OFF']['diagnostic']['trigger'];default=tuple(tr['default_goal']);pend=ps(tr['pending']);alt=next(tuple(q) for q in row['old_order'] if tuple(q) in pend and tuple(q)!=default);assert alt==tuple(tr['alternative_goal'])
  ref=outs['REF'];pending=set(U);cursor=0;first=None
  for i,e in enumerate(ref['native']['raw']['trace']):
   pending-=ps(ref['native']['raw']['route'][cursor:e['index']+1]);cursor=e['index'];assert len(pending)==e['pending_count']
   if e['kind']=='recovery' and len(pending)>=2:first=(i,cursor,set(pending));break
  assert first[0]==tr['trace_record'] and first[1]==tr['route_index'] and first[2]==pend;checks['first_trigger_and_fixed_candidate']+=1
  p=pairs[row['id']];assert p['independent_sign']['independent_from_physical_vertices'];a=list(map(tuple,outs['OFF']['native']['raw']['route']));z=list(map(tuple,outs['ALT1']['native']['raw']['route']))
  if a==z:assert p['raw_same'] and p['post_same'] and p['delta_post_sign']==0;checks['same_physical_route']+=1
  else:
   k=0
   while k<min(len(a),len(z)) and a[k]==z[k]:k+=1
   k-=1;QQ=U-set(a[:k+1]);h=p['H2'];assert h['common_index']==k and h['p']==list(a[k]) and ps(h['Qstar'])==QQ
   for arm,path in [('OFF',a),('ALT1',z)]:
    ss=max(next(i for i,vv in enumerate(path) if vv==q) for q in QQ);cc=h['C_'+arm];assert cc['C']==ss-k and k+cc['C']+len(path)-1-ss==len(path)-1;checks['shared_C_identities']+=1
   assert not h['L'];checks['H2_empty_L_not_support']+=1
  for key in ('phases_OFF','phases_ALT1'):
   phases=p[key];assert phases['total']==sum(phases[k] for k in ('before_trigger','recovery','after_own_goal_coverage','return_after_last'))
  d=derived[row['id']];assert d['origin_comparison']['same_target_pair']==(p['default_target']==src['old_pair']['default_target'] and p['alternative_target']==src['old_pair']['alternative_target'])
 for src in sources.values():
  scan=read(H/'qualification'/(src['id']+'__A_scan.json'));order=scan['first20'];b0=src['old_obstacle'];assert len(order)<=20 and order==sorted(order,key=lambda q:(sum(abs(x-y) for x,y in zip(q,b0)),q[0],q[1]));accepted=[x['cell'] for x in scan['attempts'] if x['status']=='qualified'];actual=[r['selected_obstacle'] for r in rows if r['origin']==src['id'] and r['kind']=='A' and r['status']=='qualified'];assert accepted==actual
 log=[json.loads(s) for s in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];starts=[s for s in log if s['event']=='started'];keys=[(s['job'],s['kind']) for s in starts];assert len(keys)==len(set(keys))
 calls={k:sum(s['kind']==k for s in starts) for k in ('core','post')};assert calls=={'core':21,'post':21} and all(s['arm']!='history' for s in starts)
 for arm in ('REF','OFF','ALT1'):
  for kind in ('core','post'):assert sum(s['arm']==arm and s['kind']==kind for s in starts)<=12
 qcounts=read(H/'qualification_ledger.json')['counts'];assert qcounts['BFS_calls']==7 and qcounts['BFS_calls']<=66 and qcounts['B_fixed_slot_checks']==6
 assert len(pairs)==7 and len(read(H/'完整新增视图指标.json'))==42 and len(read(H/'status.json')['not_run'])==15
 before=(H/'root_before.md').read_bytes();now=(ROOT/'当前进度与下一步.md').read_bytes();assert now.endswith(before)
 if (H/'root_after.md').exists():assert now==(H/'root_after.md').read_bytes()
 else:assert now==before
 sealed=0
 if (H/'final_receipt.json').exists():
  ff=read(H/'final_receipt.json')
  for p,v in ff['files'].items():assert sha(H/p)==v,p;sealed+=1
  assert sha(ROOT/'当前进度与下一步.md')==ff['root_sha256']
 result=dict(passed=True,hash_bindings_checked=hashes,sealed_files_checked=sealed,checks=dict(checks),actual_calls=calls,new_views=42,qualified=7,inapplicable_or_missing=5,duplicate=0,root_history_chain=True,previous_final_bound=True,new_core=0,new_post=0,new_geometry=0,new_BFS=0,saved_certificate_arithmetic_only=True)
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
