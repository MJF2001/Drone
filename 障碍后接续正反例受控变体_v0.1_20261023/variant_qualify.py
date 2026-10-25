from common import *
from qualification_primitives import slab,reachable,near
from collections import Counter,defaultdict
OLD=ROOT/'障碍后接续假设有限扩样_v0.1_20261023'
def signature(c,old):
 # name is an output identifier, never a physical input field.
 return sha_bytes(json.dumps(dict(input={k:v for k,v in c.items() if k!='name'},old_order=old,seed=20261020),sort_keys=True,separators=(',',':')).encode())
def sha_bytes(v):return hashlib.sha256(v).hexdigest()
def rebuild_done(hist,counts):
 v=hist['post']['vertices'];by=defaultdict(set);ind=defaultdict(set)
 for e in hist['post']['credit_witnesses']:by[e['edge']].add(tuple(e['point']));counts['saved_credit_rows']+=1
 for e in hist['views']['B']['events']:
  counts['independent_saved_credit_rows']+=1
  if e['new']:ind[e.get('edge',-1)].add(tuple(e['cell']))
 done=[set(by[-1])];other=set(ind[-1]);assert done[0]==other
 for k in range(len(v)-1):
  counts['credit_union_cell_operations']+=len(done[-1])+len(by[k]);done.append(done[-1]|by[k]);other=other|ind[k]
  assert done[-1]==other;counts['credit_prefix_states_checked']+=1
 return done
def choose_cut(v,done,P,threshold):return next((j for j in range(1,len(v)) if len(done[j])>=threshold and tuple(v[j]) in P and near(v[j-1],v[j]) and len(P-done[j])>=2),None)
def changed_fields(a,b):return sorted(k for k in set(a)|set(b) if k!='name' and a.get(k)!=b.get(k))
def prefix_distance(hist,cut,b,counts):
 E=b['exact'].Expr;value=E();v=hist['post']['vertices']
 for a,z in zip(v[:cut],v[1:cut+1]):value=value+E.sqrt(sum((x-y)**2 for x,y in zip(a,z)));counts['prefix_distance_terms']+=1
 lo,hi=value.interval();return dict(certificate=b['exact'].certificate(value),display=float((lo+hi)/2),scope='already executed old post prefix; not deducted from given remaining budget 10000')
def assess(cN,hist,cut,cell,done,counts,b,designated=None):
 start=time.perf_counter();deadline=start+20;F=ps(cN['free']);P=ps(cN['published_targets']);HH=ps(cN['covered']);U=P-HH;S=tuple(cN['current']);prev=tuple(cN['previous']);base=tuple(cN['base']);FE=F-{cell}
 result=dict(cell=norm(cell),status='checking');counts['candidate_qualification_attempts']+=1
 if cell in U:result['status']='pending_target_blocked';return result,None
 if cell not in F or cell in {S,prev,base}:result['status']='current_base_heading_invalid';return result,None
 assert U==P&FE-HH and not P-FE-HH
 v=hist['post']['vertices'];collision=None
 for k in range(cut,len(v)-1):
  assert time.perf_counter()<deadline,'qualification_deadline';counts['primary_cell_edge_tests']+=1;hit=slab(v[k],v[k+1],cell)
  if hit is not None:
   edge=hist['post']['edges'][k];collision=dict(edge=k,interval=hit,pending_at_edge_end=len(P-done[k+1]),source_left=edge['left'],source_right=edge['right']);break
 result['collision']=collision
 if collision is None:result['status']='grid_only_block' if cell in ps(cN['old_route']) else 'post_legal';return result,None
 if designated is not None and collision['edge']!=designated:result['status']='earlier_edge_invalid' if collision['edge']<designated else 'designated_edge_not_first_invalid';return result,None
 if not collision['interval']['strict_interior']:result['status']='touch_only';return result,None
 if collision['pending_at_edge_end']<2:result['status']='not_coverage_ge2';return result,None
 d,parents=reachable(FE,S,deadline,counts)
 if not U|{base}<=set(d):result['status']='unreachable';return result,None
 result.update(status='qualified',seconds=time.perf_counter()-start,reachable=len(d));indstart=time.perf_counter();idead=indstart+20;ic=Counter();invalid=[]
 for k in range(cut,len(v)-1):
  assert time.perf_counter()<idead,'independent_qualification_deadline';ic['independent_geometry_queries']+=1;counts['independent_geometry_queries']+=1
  if not b['IG'].legal(FE,v[k],v[k+1]):invalid.append(k)
 assert invalid and invalid[0]==collision['edge']
 for q,parent in parents.items():
  assert time.perf_counter()<idead,'independent_qualification_deadline';ic['tree_rows']+=1;counts['independent_tree_rows']+=1;assert q in FE
  if q==S:assert parent is None and d[q]==0
  else:assert parent in parents and near(parent,q) and d[parent]+1==d[q]
 assert U|{base}<=set(parents)
 cert=dict(start=norm(S),rows=[dict(cell=norm(q),parent=norm(parents[q]),distance=d[q]) for q in sorted(d)],independent=dict(passed=True,invalid_post_edges=invalid,counts=dict(ic),seconds=time.perf_counter()-indstart))
 ec=dict(cN,free=norm(sorted(FE)),targets=norm(sorted(P&FE)),deferred_targets=[]);phase_validate(ec,b['validate'])
 return result,(ec,cert)
def safe_assess(*args):
 try:return assess(*args)
 except AssertionError as ex:
  if str(ex) not in ('qualification_deadline','independent_qualification_deadline'):raise
  return dict(cell=norm(args[3]),status='qualification_unresolved',reason=str(ex)),None
def construct():
 start=time.perf_counter();b=bindings();plan=read(H/'plan.json');sources=read(H/'source_bindings.json');oldreg=read(OLD/'state_registry.json');seen={};rows=[];total=Counter();scans=[]
 for oldrow in oldreg:seen[signature(read(OLD/oldrow['input']),oldrow['old_order'])]='old:'+oldrow['id']
 def commit(row,cN,old_order,hist,cut,rawidx,cell,attempt,cert):
  ec=attempt[0];certificate=attempt[1];ec['name']=row['id'];sig=signature(ec,old_order)
  row.update(selected_obstacle=norm(cell),current=ec['current'],previous=ec['previous'],H=ec['covered'],U0=norm(sorted(ps(ec['targets'])-ps(ec['covered']))),old_order=old_order,cut=cut,source_raw_index=rawidx,blocked_old_post=cert['collision'],input='inputs/'+row['id']+'.json',physical_signature=sig,independent_qualification=certificate['independent'])
  if sig in seen:row.update(status='duplicate',duplicate_of=seen[sig]);return
  seen[sig]='new:'+row['id'];dump(H/row['input'],ec);row.update(status='qualified',input_sha256=sha(H/row['input']))
  dump(H/'qualification'/(row['id']+'__reachability.json'),certificate)
  dump(H/'history'/(row['id']+'.json'),dict(physical_prefix=hist['post']['vertices'][:cut+1],credits=[e for e in hist['post']['credit_witnesses'] if e['edge']<cut],old_actual_post_suffix=hist['post']['vertices'][cut:],old_raw_suffix=hist['native']['raw']['route'][rawidx:],old_order=old_order,raw_index=rawidx,post_cut=cut,source_history_output=cN['_source'] if '_source' in cN else row['history_output']))
 for src in sources:
  counts=Counter();sstart=time.perf_counter();hist=read(src['history_output']);oldc=read(src['old_input']);original=src['old_registry'];v=hist['post']['vertices'];P=ps(oldc['published_targets']);F=ps(hist['input']['free']);done=rebuild_done(hist,counts);cut=original['cut'];i=original['source_raw_index'];b0=tuple(src['old_obstacle']);edgeidx=src['fixed_global_edge'];assert v[edgeidx:edgeidx+2]==src['edge_vertices'];assert oldc['free']==norm(sorted(F-{b0}))
  assert ps(oldc['covered'])==done[cut] and hist['native']['raw']['route'][i]==oldc['current']
  baseN=dict(oldc,free=norm(sorted(F)),targets=norm(sorted(P)),deferred_targets=[]);U=P-ps(oldc['covered']);deadline=time.perf_counter()+20;a,z=src['edge_vertices'];pool=[]
  pool_timeout=False
  for cell in sorted(F-U-{tuple(oldc['current']),tuple(oldc['base']),tuple(oldc['previous']),b0}):
   counts['AABB_projections']+=1
   if time.perf_counter()>=deadline:pool_timeout=True;pool=[];break
   if all(2*max(a[d],z[d])>=2*cell[d]-1 and 2*min(a[d],z[d])<=2*cell[d]+1 for d in (0,1)):pool.append(cell)
  pool.sort(key=lambda p:(sum(abs(x-y) for x,y in zip(p,b0)),p[0],p[1]));scan=dict(origin=src['id'],fixed_global_edge=edgeidx,edge_vertices=src['edge_vertices'],pool_size=len(pool),first20=norm(pool[:20]),attempts=[],pool_timeout=pool_timeout);Arows=[]
  for cell in pool[:20]:
   before=time.perf_counter();check,qualified=safe_assess(baseN,hist,cut,cell,done,counts,b,edgeidx);check['seconds']=time.perf_counter()-before;scan['attempts'].append(check)
   if check['status']=='qualification_unresolved':scan['stop_reason']=check['reason'];break
   if qualified:
    n=len(Arows)+1;row=dict(next(s for s in plan['slots'] if s['origin']==src['id'] and s['variant']=='A'+str(n)),status='pending',history_output=src['history_output'],reference_global_edge=edgeidx,progress_description='same old physical event cut',attempts=[check])
    commit(row,baseN,original['old_order'],hist,cut,i,cell,qualified,check)
    newinput=qualified[0];fields=changed_fields(oldc,newinput);assert set(fields)<={'free','targets'};row['changed_physical_fields']=fields;assert ps(newinput['covered'])==ps(oldc['covered']) and ps(newinput['targets'])-ps(newinput['covered'])==U
    Arows.append(row)
    if len(Arows)==2:break
  for n in range(len(Arows)+1,3):Arows.append(dict(next(s for s in plan['slots'] if s['origin']==src['id'] and s['variant']=='A'+str(n)),status='qualification_unresolved' if pool_timeout or scan.get('stop_reason') else 'missing_A_candidate',history_output=src['history_output'],reference_global_edge=edgeidx,attempts=[]))
  olddistance=prefix_distance(hist,cut,b,counts)
  for ar in Arows:ar['already_flown_distance']=olddistance
  rows.extend(Arows);scans.append(scan);dump(H/'qualification'/(src['id']+'__A_scan.json'),scan)
  for spec in (s for s in plan['slots'] if s['origin']==src['id'] and s['kind']=='B'):
   row=dict(spec,status='pending',history_output=src['history_output'],reference_global_edge=edgeidx,attempts=[]);threshold=(spec['progress_percent']*len(P)+99)//100;newcut=choose_cut(v,done,P,threshold);counts['B_fixed_slot_checks']+=1;row['threshold']=threshold
   if newcut is None:row['status']='no_cut';rows.append(row);continue
   rawidx=hist['post']['edges'][newcut-1]['right'];assert hist['native']['raw']['route'][rawidx]==v[newcut];HH=done[newcut];old_order=[e['point'] for e in hist['post']['locked_nominal_anchors'] if e['index']>rawidx];newN=dict(baseN,current=v[newcut],previous=v[newcut-1],covered=norm(sorted(HH)),old_route=hist['native']['raw']['route'][rawidx:]);row.update(cut=newcut,source_raw_index=rawidx,current=v[newcut],previous=v[newcut-1],H=norm(sorted(HH)),U0=norm(sorted(P-HH)),old_order=old_order,selected_obstacle=norm(b0),already_flown_post_prefix_vertices=newcut)
   row['already_flown_distance']=prefix_distance(hist,newcut,b,counts)
   dump(H/'history'/(row['id']+'__proposed.json'),dict(physical_prefix=v[:newcut+1],credits=[e for e in hist['post']['credit_witnesses'] if e['edge']<newcut],source_raw_index=rawidx,old_order=old_order,history_output=src['history_output'],already_flown_distance=row['already_flown_distance']))
   if newcut>edgeidx:row['status']='cut_past_reference_block';rows.append(row);continue
   before=time.perf_counter();check,qualified=safe_assess(newN,hist,newcut,b0,done,counts,b);check['seconds']=time.perf_counter()-before;row['attempts'].append(check)
   if qualified:
    commit(row,newN,old_order,hist,newcut,rawidx,b0,qualified,check);fields=changed_fields(oldc,qualified[0]);assert set(fields)<={'covered','current','previous','old_route'};row['changed_physical_fields']=fields
   else:row['status']=check['status']
   rows.append(row)
  total.update(counts);dump(H/'qualification'/(src['id']+'__counts.json'),dict(counts=counts,seconds=time.perf_counter()-sstart));dump(H/'state_registry.json',rows)
  print('QUALIFIED_VARIANTS',src['id'],[(r['variant'],r['status']) for r in rows if r['origin']==src['id']],flush=True)
 assert len(rows)==12 and [r['id'] for r in rows]==[r['id'] for r in plan['slots']]
 assert total['BFS_calls']<=66 and sum(len(s['attempts']) for s in scans)<=60
 dump(H/'qualification_ledger.json',dict(counts=dict(total),seconds=time.perf_counter()-start,real_core=0,real_post=0,new_histories=0));return rows
