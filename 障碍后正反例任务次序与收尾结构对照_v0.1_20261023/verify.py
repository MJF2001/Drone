"""Independent reread of original paths and engine credits; no production imports.
Rectangle inequalities, original event streams and independent exact arithmetic.
"""
from pathlib import Path
from collections import Counter
from itertools import groupby
from fractions import Fraction
from math import isqrt
import json,hashlib,time
H=Path(__file__).resolve().parent;ROOT=H.parent;C=Counter()
BASE=ROOT/'障碍后接续假设有限扩样_v0.1_20261023';VAR=ROOT/'障碍后接续正反例受控变体_v0.1_20261023'
def read(p):
 b=Path(p).read_bytes();C['files_read']+=1;C['bytes_read']+=len(b);return json.loads(b.decode('utf-8-sig'))
def sha(p):
 b=Path(p).read_bytes();C['hash_files']+=1;C['hash_bytes']+=len(b);return hashlib.sha256(b).hexdigest()
def canon(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def points(x):return {tuple(v) for v in x}
def coef(c):
 d=Counter()
 for t in c['exact']['terms']:d[t['r']]+=Fraction(t['c']['n'],t['c']['d']);C['saved_radical_terms']+=1
 return {r:q for r,q in d.items() if q}
def plus(*signed):
 d=Counter()
 for sign,x in signed:
  for r,q in x.items():d[r]+=sign*q;C['radical_coefficient_additions']+=1
 return {r:q for r,q in d.items() if q}
def length_terms(path):
 d=Counter()
 for a,b in zip(path,path[1:]):
  n=(b[0]-a[0])**2+(b[1]-a[1])**2;C['coordinate_length_terms']+=1
  if not n:continue
  outside=1
  for k in range(1,isqrt(n)+1):
   C['square_factor_trials']+=1
   if n%(k*k)==0:outside=k
  d[n//(outside*outside)]+=outside
 return dict(d)
def verify_summary(actual,seq,tag,block_ids):
 # seq is independently reconstructed tuples(task, native/post marker).
 ids=[tag(q) for q,m in seq];runs=[k for k,g in groupby(ids)];assert [r['task'] for r in actual['task_sequence']]==[list(q) for q,m in seq]
 assert actual['compressed_block_sequence']==runs and actual['scope_tasks']==[list(q) for q in sorted(q for q,m in seq)]
 remaining=Counter(ids);done=[];first={};last={}
 for i,((q,mark),bid) in enumerate(zip(seq,ids)):
  C['independent_sequence_rows']+=1;first.setdefault(bid,(i,mark));last[bid]=(i,mark);remaining[bid]-=1
  if remaining[bid]==0:done.append(bid)
  r=actual['task_sequence'][i];assert r['block']==bid
  for k,v in mark.items():assert r['marker'][k]==v
 assert actual['completion_order']==done and actual['last_completed_block']==(ids[-1] if ids else None) and actual['last_task']==(list(seq[-1][0]) if seq else None)
 by={r['block']:r for r in actual['blocks']};counts=Counter(ids)
 for bid in block_ids:
  b=by[bid];assert b['remaining_in_this_scope']==counts[bid] and b['service_runs']==runs.count(bid) and b['interleaved_in_service_labels']==(runs.count(bid)>1)
  assert b['first_scope_rank']==(first[bid][0] if bid in first else None) and b['last_scope_rank']==(last[bid][0] if bid in last else None)
  if bid in first:
   for k,v in first[bid][1].items():assert b['first_marker'][k]==v
   for k,v in last[bid][1].items():assert b['completion_marker'][k]==v
 C['sequence_summaries_verified']+=1
def verify():
 start=time.perf_counter();checks=Counter()
 for path,v in read(H/'source_guards.json').items():assert sha(path)==v,path
 m_by={m['id']:m for m in read(BASE/'plan.json')['maps']};reg={'base':{r['id']:r for r in read(BASE/'state_registry.json')},'variants':{r['id']:r for r in read(VAR/'state_registry.json')}};index=read(H/'pair_index.json');assert len(index)==19
 assert len([r for r in index if r['dataset']=='base'])==12 and len([r for r in index if r['dataset']=='variants'])==7
 partitions=read(H/'descriptive_run_costs.json');identities=[];loaded={};postbound=Counter()
 for ix in index:
  record=read(H/ix['file']);row=reg[ix['dataset']][ix['id']];m=m_by[row['base_geometry']];rects=m['rectangles'];block_ids=['B'+str(i+1).zfill(2) for i in range(len(rects))]
  def tag(q):
   labels=[]
   for i,(x0,x1,y0,y1) in enumerate(rects):
    C['rectangle_inequality_tests']+=1
    if x0<=q[0]<=x1 and y0<=q[1]<=y1:labels.append(block_ids[i])
   assert len(labels)==1,(q,labels);return labels[0]
  source={arm:read(record['source'][arm]) for arm in ('OFF','ALT1')};loaded[ix['key']]=source
  for arm in source:assert sha(record['source'][arm])==record['source'][arm+'_sha256']
  c=source['OFF']['input'];U=points(c['targets'])-points(c['covered']);HH=points(c['covered']);P=points(c['published_targets']);tr=source['OFF']['diagnostic']['trigger'];k0=tr['route_index'];F=points(c['free'])
  rectP=set()
  for a,b,d,e in rects:rectP.update((x,y) for x in range(a,b+1) for y in range(d,e+1))
  assert rectP==P
  for q in P:tag(q)
  pending=U-points(source['OFF']['native']['raw']['route'][:k0+1]);assert pending==points(tr['pending'])
  feature=record['decision_available'];assert feature['pending']==[list(q) for q in sorted(pending)] and feature['pending_sha256']==canon([list(q) for q in sorted(pending)])
  pc=Counter(tag(q) for q in pending);hc=Counter(tag(q) for q in HH);uc=Counter(tag(q) for q in U)
  assert feature['pending_by_block']=={b:pc[b] for b in block_ids} and feature['event_initial_H_by_block']=={b:hc[b] for b in block_ids} and feature['event_initial_U_by_block']=={b:uc[b] for b in block_ids}
  q0,q1=tuple(tr['default_goal']),tuple(tr['alternative_goal']);assert feature['q0_block']==tag(q0) and feature['q1_block']==tag(q1) and feature['same_target_block']==(tag(q0)==tag(q1)) and feature['unfinished_blocks']==len(pc)
  order=list(map(tuple,row['old_order']));assert feature['q0_old_rank']==(order.index(q0) if q0 in order else None) and feature['q1_old_rank']==order.index(q1) and feature['q0_already_first_pending_old_order']==(next(q for q in order if q in pending)==q0)
  assert feature['d0']==tr['default_distance'] and feature['d1']==tr['alternative_distance']
  FN={(x,y) for x in range(m['xmax']+1) for y in range(m['ymax']+1)};assert feature['known_obstacles']==[list(q) for q in sorted(FN-F)]
  checks['decision_information_from_original_prefix']+=1;arm_expected={};native_sequences={}
  for arm,o in source.items():
   assert o['input']==c and o['passed'] and o['independent']['passed'] and o['decision_audit']['passed'];a=record['after_route_known']['arms'][arm];raw=o['native']['raw']['route'];remaining=set(U);seq=[];first_indices={}
   for i,p in enumerate(raw):
    C['raw_source_vertices_scanned']+=1;q=tuple(p)
    if q in remaining:remaining.remove(q);first_indices[q]=i;seq.append((q,dict(native_vertex=i,recorded_raw_credit_edge=i-1)))
   assert not remaining;native_sequences[arm]=seq;verify_summary(a['native_full'],seq,tag,block_ids)
   trigger_seq=[(q,mark) for q,mark in seq if q in pending];verify_summary(a['native_from_trigger'],trigger_seq,tag,block_ids)
   # Independent post sequence uses engine credit_witnesses rather than the
   # primary analysis' actual-view events stream.
   postseq=[]
   for e in o['post']['credit_witnesses']:
    q=tuple(e['point']);edge=e['edge'];w=e['evidence']['witness'] if 'evidence' in e else e['witness'];span=[o['post']['edges'][edge]['left'],o['post']['edges'][edge]['right']] if edge>=0 else None
    postseq.append((q,dict(post_edge=edge,witness=w,source_raw_span=span,native_first_service_index=first_indices[q])));C['engine_credit_rows_scanned']+=1
   assert {q for q,mark in postseq}==U;verify_summary(a['post_full'],postseq,tag,block_ids)
   endpoints=[0]+[e['right'] for e in o['post']['edges']]
   if k0 in endpoints:
    j=endpoints.index(k0);assert o['post']['vertices'][j]==raw[k0];assert a['post_boundary']['status']=='exact_source_index_and_vertex' and a['post_boundary']['post_vertex']==j
    before={q for q,mark in postseq if mark['post_edge']<j};assert a['post_boundary']['native_pending_credited_before_post_boundary']==[list(q) for q in sorted(before&pending)];postscope=[(q,mark) for q,mark in postseq if q not in before];verify_summary(a['post_from_mapped_trigger'],postscope,tag,block_ids);postbound['exact']+=1
   else:assert a['post_from_mapped_trigger'] is None;postbound['unknown']+=1
   lastq,lastmark=seq[-1];assert a['last_native_service']['cell']==list(lastq) and a['last_native_service']['vertex']==lastmark['native_vertex'] and a['raw_return_edges']==len(raw)-1-lastmark['native_vertex']
   assert a['last_native_service']['block']==tag(lastq)
   recovery=o['diagnostic']['trigger']['actual_recovery_path'];assert a['recovery']['vertices']==recovery
   for name,q in [('q0',q0),('q1',q1)]:assert a['recovery']['q_visits'][name]==[i for i,z in enumerate(recovery) if tuple(z)==q]
   post_terms=length_terms(o['post']['vertices']);assert post_terms==coef(a['length_post_certificate'])
   stages=o['views']['B']['metrics']['stages'];assert plus((1,coef(stages['to_first_witness'])),(1,coef(stages['between_first_last_witness'])),(1,coef(stages['after_last_witness_return'])))==post_terms
   assert coef(a['post_return_after_last_saved_witness'])==coef(stages['after_last_witness_return'])
   arm_expected[arm]=dict(n=len(raw)-1,last=lastmark['native_vertex'],return_edges=len(raw)-1-lastmark['native_vertex'],post=post_terms)
   checks['original_route_and_credit_views_verified']+=2
  raw0=source['OFF']['native']['raw']['route'];raw1=source['ALT1']['native']['raw']['route'];n0,n1=arm_expected['OFF']['n'],arm_expected['ALT1']['n'];ret_delta=arm_expected['ALT1']['return_edges']-arm_expected['OFF']['return_edges'];after=record['after_route_known'];assert after['delta_raw']==n1-n0 and after['delta_native_return']==ret_delta
  dd=plus((1,arm_expected['ALT1']['post']),(-1,arm_expected['OFF']['post']));assert coef(after['delta_post'])==dd and coef(after['delta_geometry'])==plus((1,dd),(-1,{1:Fraction(n1-n0)}))
  if raw0!=raw1:
   shared=0
   for i,(x,y) in enumerate(zip(raw0,raw1)):
    if x!=y:break
    shared=i
   cc=after['shared_p_C'];assert cc['common_index']==shared and cc['common_p']==raw0[shared]
   assert cc['C_OFF']==arm_expected['OFF']['last']-shared and cc['C_ALT1']==arm_expected['ALT1']['last']-shared and cc['delta_C']+ret_delta==n1-n0;checks['shared_p_C_identities']+=1
  else:assert after['shared_p_C'] is None and after['rawsame'] and n1==n0
  for arm in ('OFF','ALT1'):
   partition=partitions[ix['key']]['arms'][arm];begin=partition['start_vertex'];seq=[(q,m) for q,m in native_sequences[arm] if m['native_vertex']>begin];groups=[list(g) for bid,g in groupby(seq,key=lambda qm:tag(qm[0]))];spans=sum(g[-1][1]['native_vertex']-g[0][1]['native_vertex'] for g in groups);gaps=sum(b[0][1]['native_vertex']-a[-1][1]['native_vertex'] for a,b in zip(groups,groups[1:]));lead=groups[0][0][1]['native_vertex']-begin if groups else 0
   assert partition['span_sum']==spans and partition['gap_sum']==gaps and partition['to_first_new_service_edges']==lead and partition['total_to_last_service']==lead+spans+gaps;checks['credit_run_edge_partitions']+=1
  context={k:v for k,v in c.items() if k!='name'};identity=dict(full_E_and_old_order_sha256=canon(dict(input=context,old_order=row['old_order'],seed=20261020)),local_trigger_sha256=canon(dict(current=tr['current'],previous=tr['previous'],pending=[list(q) for q in sorted(pending)])),trigger_and_targets_sha256=canon(dict(current=tr['current'],previous=tr['previous'],pending=[list(q) for q in sorted(pending)],q0=list(q0),q1=list(q1))),paired_native_tails_sha256=canon(dict(OFF=canon(raw0[k0:]),ALT1=canon(raw1[k0:]))));assert identity==record['identity'];identities.append((ix['key'],identity))
  checks['pairs_independently_verified']+=1
 dup=read(H/'duplicate_levels.json')['groups']
 for level in dup:
  gg={}
  for key,identity in identities:gg.setdefault(identity[level],[]).append(key)
  expected=[v for v in gg.values() if len(v)>1];assert sorted(sorted(v) for v in expected)==sorted(sorted(g['members']) for g in dup[level])
 assert len(read(H/'gaps.json'))==5 and not read(H/'errors.json') and read(H/'analysis_receipt.json')['processed']==19
 before=(H/'root_before.md').read_bytes();assert read(VAR/'final_receipt.json')['root_sha256']==sha(H/'root_before.md') and read(BASE/'final_receipt.json')['root_sha256']==sha(VAR/'root_before.md')
 current=(ROOT/'当前进度与下一步.md').read_bytes();assert current.endswith(before)
 if (H/'root_after.md').exists():assert current==(H/'root_after.md').read_bytes()
 else:assert current==before
 sealed=0
 if (H/'final_receipt.json').exists():
  final=read(H/'final_receipt.json')
  for p,v in final['files'].items():assert sha(H/p)==v,p;sealed+=1
  assert sha(ROOT/'当前进度与下一步.md')==final['root_sha256']
 result=dict(passed=True,pairs=19,processing_routes=38,saved_views=76,checks=dict(checks),post_boundaries=dict(postbound),counts=dict(C),sealed_files_checked=sealed,wall_seconds=time.perf_counter()-start,root_history_chain=True,method='independent rectangle inequalities and original native path stream; post engine credits instead of primary actual-view events; independent integer/rational length reconstruction',new_core=0,new_post=0,new_history=0,new_BFS=0,new_shortest_path=0,new_visibility=0,new_counterfactual=0,new_candidates=0)
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
