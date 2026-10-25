"""Coordinate labels, saved sequence comparisons and exact accounting only.
Imports no planner, post processor, geometry predicate or graph algorithm.
"""
from common import *
import traceback
def map_blocks(m):
 mapping={};blocks=[]
 for i,(a,b,c,d) in enumerate(m['rectangles'],1):
  bid='B'+str(i).zfill(2);cells={(x,y) for x in range(a,b+1) for y in range(c,d+1)}
  for p in cells:assert p not in mapping;mapping[p]=bid;COUNTS['block_coordinate_labels']+=1
  blocks.append(dict(id=bid,rectangle=[a,b,c,d],cells=len(cells)))
 return mapping,blocks
def count_blocks(points,mapping,blocks):
 out={b['id']:0 for b in blocks}
 for p in points:out[mapping[tuple(p)]]+=1;COUNTS['block_membership_counts']+=1
 return out
def summarize(rows,scope,mapping,blocks):
 # rows have an immutable original credit rank and a physical/native marker.
 filtered=[r for r in rows if tuple(r['task']) in scope];seen=set();runs=[]
 for rank,r in enumerate(filtered):
  q=tuple(r['task']);assert q not in seen;seen.add(q);bid=mapping[q]
  if not runs or runs[-1]['block']!=bid:runs.append(dict(block=bid,start_scope_rank=rank,end_scope_rank=rank,first_full_rank=r['full_rank'],last_full_rank=r['full_rank']))
  else:runs[-1].update(end_scope_rank=rank,last_full_rank=r['full_rank'])
 assert seen==scope
 completion=[];byblock=[]
 for b in blocks:
  tasks=scope&{q for q,z in mapping.items() if z==b['id']};rr=[(i,r) for i,r in enumerate(filtered) if tuple(r['task']) in tasks];nr=sum(z['block']==b['id'] for z in runs)
  record=dict(block=b['id'],remaining_in_this_scope=len(tasks),status='complete_before_scope' if not tasks else 'completed',first_scope_rank=rr[0][0] if rr else None,last_scope_rank=rr[-1][0] if rr else None,first_marker=rr[0][1]['marker'] if rr else None,completion_marker=rr[-1][1]['marker'] if rr else None,service_runs=nr,interleaved_in_service_labels=nr>1)
  byblock.append(record)
  if rr:completion.append((rr[-1][0],b['id']))
 return dict(task_sequence=filtered,compressed_block_sequence=[r['block'] for r in runs],runs=runs,blocks=byblock,completion_order=[z[1] for z in sorted(completion)],last_completed_block=mapping[tuple(filtered[-1]['task'])] if filtered else None,last_task=filtered[-1]['task'] if filtered else None,interleaved_blocks=[b['block'] for b in byblock if b['interleaved_in_service_labels']],scope_tasks=norm(sorted(scope)))
def native_rows(o,mapping):
 c=o['input'];U=ps(c['targets'])-ps(c['covered']);seen=set();rows=[];path=o['native']['raw']['route'];events={tuple(e['cell']):e for e in o['views']['A']['events'] if e['new']}
 for i,point in enumerate(path):
  COUNTS['native_vertices_scanned']+=1;q=tuple(point)
  if q in U and q not in seen:
   seen.add(q);rows.append(dict(task=norm(q),block=mapping[q],full_rank=len(rows),marker=dict(native_vertex=i,recorded_raw_credit_edge=events[q].get('edge',-1)),saved_credit=events[q]))
 assert seen==U
 assert [r['task'] for r in rows]==[e['cell'] for e in o['views']['A']['events'] if e['new']]
 return rows
def post_rows(o,mapping,raw_rows):
 raw_indices={tuple(r['task']):r['marker']['native_vertex'] for r in raw_rows};rows=[]
 for eventindex,e in enumerate(o['views']['B']['events']):
  COUNTS['saved_post_credit_events_scanned']+=1
  if not e['new']:continue
  q=tuple(e['cell']);edge=e.get('edge',-1);span=None if edge<0 else [o['post']['edges'][edge]['left'],o['post']['edges'][edge]['right']]
  evidence=e.get('evidence',{});witness=evidence.get('witness',e.get('witness'))
  rows.append(dict(task=e['cell'],block=mapping[q],full_rank=len(rows),marker=dict(post_edge=edge,witness=witness,source_raw_span=span,native_first_service_index=raw_indices[q],event_index=eventindex),saved_credit=e))
 assert [r['task'] for r in rows]==[e['point'] for e in o['post']['credit_witnesses']]
 assert len({tuple(r['task']) for r in rows})==len(rows)
 return rows
def boundary(o,tr):
 k=tr['route_index'];found=[]
 if k==0:found.append(0)
 for j,e in enumerate(o['post']['edges']):
  COUNTS['source_index_boundary_tests']+=1
  if e['left']==k:found.append(j)
  if e['right']==k:found.append(j+1)
 found=sorted(set(found));raw=o['native']['raw']['route']
 if len(found)==1 and o['post']['vertices'][found[0]]==raw[k]:return dict(status='exact_source_index_and_vertex',raw_trigger_index=k,post_vertex=found[0],point=raw[k])
 spans=[dict(edge=j,left=e['left'],right=e['right']) for j,e in enumerate(o['post']['edges']) if e['left']<k<e['right']]
 return dict(status='unknown_trigger_bypassed_or_not_uniquely_mapped',raw_trigger_index=k,candidate_vertices=found,straddling_edges=spans,scope_rule='retain whole post sequence; do not force a synchronized split')
def arm_data(o,tr,mapping,blocks):
 c=o['input'];U=ps(c['targets'])-ps(c['covered']);pending=ps(tr['pending']);raw=o['native']['raw']['route'];k=tr['route_index'];nr=native_rows(o,mapping);pr=post_rows(o,mapping,nr)
 assert U-ps(raw[:k+1])==pending
 before_native={tuple(r['task']) for r in nr if r['marker']['native_vertex']<=k};assert U-before_native==pending
 native=summarize(nr,pending,mapping,blocks);bind=boundary(o,tr);fullpost=summarize(pr,U,mapping,blocks)
 if bind['status']=='exact_source_index_and_vertex':
  j=bind['post_vertex'];early={tuple(r['task']) for r in pr if r['marker']['post_edge']<j};early_pending=pending&early;postremaining=U-early
  assert postremaining==pending-early_pending
  post_scope=summarize(pr,postremaining,mapping,blocks);bind.update(native_pending_credited_before_post_boundary=norm(sorted(early_pending)),actual_post_remaining_at_boundary=norm(sorted(postremaining)),same_as_native_pending=not early_pending)
 else:post_scope=None
 segment=o['diagnostic']['trigger']['actual_recovery_path'];visits={}
 for label,q in [('q0',tr['default_goal']),('q1',tr['alternative_goal'])]:visits[label]=[i for i,p in enumerate(segment) if p==q]
 recovery=dict(vertices=segment,goal=o['diagnostic']['trigger']['chosen_goal'],q_visits=visits,q0_then_q1_in_same_connection=bool(visits['q0'] and visits['q1'] and visits['q0'][0]<visits['q1'][0]),new_task_sequence=[r for r in nr if k<r['marker']['native_vertex']<=k+len(segment)-1])
 lastindex=max(r['marker']['native_vertex'] for r in nr);ret=len(raw)-1-lastindex;lastcell=raw[lastindex]
 assert lastcell==o['native']['raw']['route'][lastindex]
 stages=o['views']['B']['metrics']['stages'];posttotal=o['views']['B']['metrics']['length_certificate'];assert same(add(add(stages['to_first_witness'],stages['between_first_last_witness']),stages['after_last_witness_return']),posttotal)
 return dict(native_full=summarize(nr,U,mapping,blocks),native_from_trigger=native,post_full=fullpost,post_from_mapped_trigger=post_scope,post_boundary=bind,recovery=recovery,last_native_service=dict(vertex=lastindex,cell=lastcell,block=mapping[tuple(lastcell)]),raw_return_edges=ret,post_return_after_last_saved_witness=stages['after_last_witness_return'],post_return_display=value(stages['after_last_witness_return']),post_stage_convention=stages['convention'],length_raw=len(raw)-1,length_post=o['views']['B']['metrics']['length'],length_post_certificate=posttotal,turns_raw=o['views']['A']['metrics']['turns'],turns_post=o['views']['B']['metrics']['turns'],raw_tail_sha256=digest(raw[k:]),post_vertices_sha256=digest(o['post']['vertices']))
def analyze():
 start=time.perf_counter();plan=read(BASE/'plan.json');maps={m['id']:m for m in plan['maps']};registries={'base':{r['id']:r for r in read(BASE/'state_registry.json')},'variants':{r['id']:r for r in read(VAR/'state_registry.json')}};datasets=[('base',BASE),('variants',VAR)];indices=[];errors=[];blocksystems={};full=[]
 for ident,m in maps.items():
  mapping,blocks=map_blocks(m);blocksystems[ident]=dict(mapping=mapping,blocks=blocks)
 dump(H/'block_systems.json',{ident:dict(source_rectangles=maps[ident]['rectangles'],blocks=z['blocks'],target_cells=len(z['mapping']),unique_membership=True,definition='original pre-existing rectangles; not a connectivity partition') for ident,z in blocksystems.items()})
 for dataset,pack in datasets:
  pp=read(pack/'pairs.json')
  for saved in pp:
   ident=saved['id'];row=registries[dataset][ident];key=dataset+'__'+ident
   try:
    o={arm:read(pack/'outputs'/(ident+'__'+arm+'.json')) for arm in ('OFF','ALT1')};c=o['OFF']['input'];tr=o['OFF']['diagnostic']['trigger'];t1=o['ALT1']['diagnostic']['trigger'];mapping=blocksystems[row['base_geometry']]['mapping'];blocks=blocksystems[row['base_geometry']]['blocks'];P=ps(c['published_targets']);U=ps(c['targets'])-ps(c['covered']);HH=ps(c['covered']);pending=ps(tr['pending'])
    assert set(mapping)==P and c==o['ALT1']['input']
    for arm,z in o.items():assert z['passed'] and z['eligible'] and z['independent']['passed'] and z['decision_audit']['passed']
    assert all(o['OFF']['off_equivalence'].values()) and o['ALT1']['decision_audit']['authorized_exceptions']==1
    for fld in ('current','previous','pending','default_goal','alternative_goal','route_index','trace_record'):assert tr[fld]==t1[fld]
    old=row['old_order'];ranks={}
    for j,q in enumerate(old):ranks.setdefault(tuple(q),j)
    first=next((tuple(q) for q in old if tuple(q) in pending),None);q0=tuple(tr['default_goal']);q1=tuple(tr['alternative_goal']);assert tr['tags']['q0_old_rank']==ranks.get(q0) and tr['tags']['q1_old_rank']==ranks.get(q1)
    perblock=count_blocks(pending,mapping,blocks);m=maps[row['base_geometry']];FN={(x,y) for x in range(m['xmax']+1) for y in range(m['ymax']+1)};obstacles=FN-ps(c['free']);assert obstacles=={tuple(row['selected_obstacle'])}
    available=dict(current=tr['current'],previous=tr['previous'],pending=norm(sorted(pending)),pending_sha256=digest(norm(sorted(pending))),pending_by_block=perblock,unfinished_blocks=sum(n>0 for n in perblock.values()),q0=q0,q1=q1,d0=tr['default_distance'],d1=tr['alternative_distance'],q0_block=mapping[q0],q1_block=mapping[q1],same_target_block=mapping[q0]==mapping[q1],q0_block_pending=perblock[mapping[q0]],q1_block_pending=perblock[mapping[q1]],q0_old_rank=ranks.get(q0),q1_old_rank=ranks.get(q1),q0_already_first_pending_old_order=q0==first,current_block=mapping.get(tuple(tr['current']),'non_target_flyable_cell'),known_obstacles=norm(sorted(obstacles)),event_initial_H_by_block=count_blocks(HH,mapping,blocks),event_initial_U_by_block=count_blocks(U,mapping,blocks),event_initial_H_count=len(HH),event_initial_U_count=len(U),F_sha256=digest(c['free']),P_sha256=digest(c['published_targets']),base=c['base'],resource_budget=c['distance_budget'],predator=c['predator'],seed=20261020,availability='report-stage extraction from saved input and trigger prefix only; not online observed or used to select')
    arms={arm:arm_data(z,tr,mapping,blocks) for arm,z in o.items()};rawdelta=arms['ALT1']['length_raw']-arms['OFF']['length_raw'];postdelta=add(arms['ALT1']['length_post_certificate'],arms['OFF']['length_post_certificate'],-1);assert rawdelta==saved['delta_raw'] and same(postdelta,saved['delta_post_certificate']);geomdelta=add(postdelta,number(rawdelta),-1)
    assert arms['OFF']['raw_return_edges']==saved['phases_OFF']['return_after_last'] and arms['ALT1']['raw_return_edges']==saved['phases_ALT1']['return_after_last']
    rawret=arms['ALT1']['raw_return_edges']-arms['OFF']['raw_return_edges'];h2=saved['H2'];rawsame=o['OFF']['native']['raw']['route']==o['ALT1']['native']['raw']['route'];C=None
    if not rawsame:
     k=h2['common_index'];assert o['OFF']['native']['raw']['route'][:k+1]==o['ALT1']['native']['raw']['route'][:k+1];cc={a:arms[a]['last_native_service']['vertex']-k for a in arms};assert cc['OFF']==h2['C_OFF']['C'] and cc['ALT1']==h2['C_ALT1']['C'];assert cc['ALT1']-cc['OFF']+rawret==rawdelta;C=dict(common_p=h2['p'],common_index=k,C_OFF=cc['OFF'],C_ALT1=cc['ALT1'],delta_C=cc['ALT1']-cc['OFF'],delta_raw_return=rawret,identity_holds=True)
    else:assert rawdelta==0 and rawret==0
    context={k:v for k,v in c.items() if k!='name'};record=dict(id=ident,key=key,dataset=dataset,base_geometry=row['base_geometry'],origin=row.get('origin'),variant=row.get('variant'),source=dict(package=str(pack),OFF=str(pack/'outputs'/(ident+'__OFF.json')),ALT1=str(pack/'outputs'/(ident+'__ALT1.json')),input=str(pack/row['input']),source_pair=str(pack/'pairs.json'),OFF_sha256=sha(pack/'outputs'/(ident+'__OFF.json')),ALT1_sha256=sha(pack/'outputs'/(ident+'__ALT1.json'))),decision_available=available,after_route_known=dict(arms=arms,original_H2=h2,shared_p_C=C,rawsame=rawsame,classification=saved['classification'],delta_recovery=saved['delta_recovery'],delta_raw=rawdelta,delta_post=saved['delta_post_certificate'],delta_post_display=saved['delta_post_display'],delta_geometry=geomdelta,delta_geometry_display=value(geomdelta),delta_native_return=rawret,native_compressed_sequences_equal=arms['OFF']['native_from_trigger']['compressed_block_sequence']==arms['ALT1']['native_from_trigger']['compressed_block_sequence'],native_completion_order_equal=arms['OFF']['native_from_trigger']['completion_order']==arms['ALT1']['native_from_trigger']['completion_order'],causal_scope='sequence and cost correspondence only; not independent mediator causality'),identity=dict(full_E_and_old_order_sha256=digest(dict(input=context,old_order=old,seed=20261020)),local_trigger_sha256=digest(dict(current=tr['current'],previous=tr['previous'],pending=norm(sorted(pending)))),trigger_and_targets_sha256=digest(dict(current=tr['current'],previous=tr['previous'],pending=norm(sorted(pending)),q0=q0,q1=q1)),paired_native_tails_sha256=digest(dict(OFF=arms['OFF']['raw_tail_sha256'],ALT1=arms['ALT1']['raw_tail_sha256']))))
    dump(H/'pairs'/(key+'.json'),record);full.append(record);indices.append(dict(key=key,id=ident,dataset=dataset,base_geometry=row['base_geometry'],origin=row.get('origin'),file='pairs/'+key+'.json',same_target_block=available['same_target_block'],q0_block=available['q0_block'],q1_block=available['q1_block'],q0_block_pending=available['q0_block_pending'],q1_block_pending=available['q1_block_pending'],unfinished_blocks=available['unfinished_blocks'],native_OFF_runs=arms['OFF']['native_from_trigger']['compressed_block_sequence'],native_ALT1_runs=arms['ALT1']['native_from_trigger']['compressed_block_sequence'],native_OFF_completion=arms['OFF']['native_from_trigger']['completion_order'],native_ALT1_completion=arms['ALT1']['native_from_trigger']['completion_order'],native_OFF_last=arms['OFF']['last_native_service'],native_ALT1_last=arms['ALT1']['last_native_service'],delta_C=C['delta_C'] if C else None,delta_return=rawret,delta_raw=rawdelta,delta_post=saved['delta_post_display'],delta_geometry=value(geomdelta),classification=saved['classification']))
   except BaseException as ex:errors.append(dict(key=key,error=repr(ex),traceback=traceback.format_exc()))
 assert len(indices)+len(errors)==19
 duplicates={}
 for level in ('full_E_and_old_order_sha256','local_trigger_sha256','trigger_and_targets_sha256','paired_native_tails_sha256'):
  groups={}
  for x in full:groups.setdefault(x['identity'][level],[]).append(x['key'])
  duplicates[level]=[dict(hash=k,members=v) for k,v in groups.items() if len(v)>1]
 relations=[]
 for x in full:
  if x['dataset']!='variants':continue
  orig=next(y for y in full if y['dataset']=='base' and y['id']==x['origin']);a=x['decision_available'];z=orig['decision_available'];cx=read(x['source']['OFF'])['input'];co=read(orig['source']['OFF'])['input'];fields=[k for k in sorted(set(cx)|set(co)) if k!='name' and cx.get(k)!=co.get(k)]
  relations.append(dict(key=x['key'],origin=orig['key'],input_fields_differing=fields,same_local_trigger=x['identity']['local_trigger_sha256']==orig['identity']['local_trigger_sha256'],same_target_pair=(a['q0'],a['q1'])==(z['q0'],z['q1']),same_F=cx['free']==co['free'],same_base=cx['base']==co['base'],same_resource=cx['distance_budget']==co['distance_budget'],same_predator=cx['predator']==co['predator'],same_old_order=registries['variants'][x['id']]['old_order']==registries['base'][orig['id']]['old_order'],same_OFF_tail=x['after_route_known']['arms']['OFF']['raw_tail_sha256']==orig['after_route_known']['arms']['OFF']['raw_tail_sha256'],same_ALT1_tail=x['after_route_known']['arms']['ALT1']['raw_tail_sha256']==orig['after_route_known']['arms']['ALT1']['raw_tail_sha256'],complete_E_not_merged=True))
 dump(H/'pair_index.json',indices);dump(H/'duplicate_levels.json',dict(groups=duplicates,relations=relations,scope='all19 retained; same local trigger or tail never merges complete input'));dump(H/'gaps.json',[r for r in registries['variants'].values() if r['status']!='qualified']);dump(H/'errors.json',errors)
 dump(H/'analysis_receipt.json',dict(passed=not errors,source_pairs=19,processed=len(indices),processing_routes=len(indices)*2,saved_views=len(indices)*4,errors=len(errors),counts=dict(COUNTS),wall_seconds=time.perf_counter()-start,new_core=0,new_post=0,new_history=0,new_BFS=0,new_shortest_path=0,new_visibility=0,new_counterfactual_routes=0,new_candidates=0))
 print(json.dumps(dict(processed=len(indices),errors=errors,duplicate_groups={k:[g['members'] for g in v] for k,v in duplicates.items()}),ensure_ascii=False,indent=2))
if __name__=='__main__':analyze()
