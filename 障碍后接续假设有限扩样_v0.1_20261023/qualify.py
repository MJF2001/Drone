from common import *
from fractions import Fraction as Q
from collections import deque,Counter
def near(a,b):return sum(abs(x-y) for x,y in zip(a,b))==1
def slab(a,b,cell):
 lo,hi=Q(0),Q(1)
 for v,w,c in zip(a,b,cell):
  d=w-v;left=Q(2*c-1,2);right=Q(2*c+1,2)
  if d==0:
   if not left<=v<=right:return None
  else:
   l,u=sorted(((left-v)/d,(right-v)/d));lo=max(lo,l);hi=min(hi,u)
   if lo>hi:return None
 mid=(lo+hi)/2;point=[Q(a[z])+mid*(b[z]-a[z]) for z in (0,1)]
 strict=lo<hi and all(abs(point[z]-cell[z])<Q(1,2) for z in (0,1))
 rat=lambda x:dict(n=x.numerator,d=x.denominator)
 return dict(lower=rat(lo),upper=rat(hi),midpoint=rat(mid),point=[rat(x) for x in point],strict_interior=strict)
def reachable(F,S,deadline,counts):
 counts['BFS_calls']+=1;parents={S:None};d={S:0};q=deque([S])
 while q:
  assert time.perf_counter()<deadline,'qualification_deadline'
  x,y=q.popleft();counts['BFS_popped']+=1
  for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   counts['BFS_neighbors']+=1
   if p in F and p not in d:d[p]=d[x,y]+1;parents[p]=(x,y);q.append(p)
 return d,parents
def prepare_states():
 b=bindings();plan=read(H/'plan.json');registry=[];used=set()
 for slot in plan['slots']:
  ident=slot['id'];row=dict(slot,status='pending',attempts=[],counts={},core_calls=0,post_calls=0);counts=Counter();start=time.perf_counter()
  try:
   hist=read(H/'outputs'/('history__'+slot['base_geometry']+'.json'))
   if not hist['passed'] or not hist['eligible']:row['status']='history_failed';continue
   c=hist['input'];P=ps(c['published_targets']);F=ps(c['free']);post=hist['post'];v=list(map(tuple,post['vertices']));raw=list(map(tuple,hist['native']['raw']['route']));credits=post['credit_witnesses']
   # All services on an edge are complete at its end; no witness midpoint
   # is used as a claim about unique physical first entry time.
   done=[set() for _ in v]
   for j in range(len(v)):done[j]={tuple(e['point']) for e in credits if e['edge']<j}
   j=next((j for j in range(1,len(v)) if len(done[j])>=slot['threshold'] and v[j] in P and near(v[j-1],v[j]) and len(P-done[j])>=2),None)
   if j is None:row['status']='no_cut';continue
   i=post['edges'][j-1]['right'];assert raw[i]==v[j];HH=done[j];U=P-HH;S=v[j];prev=v[j-1]
   identity=(slot['base_geometry'],j)
   if identity in used:row.update(status='duplicate_snapshot',cut=j);continue
   used.add(identity)
   old=[e['point'] for e in post['locked_nominal_anchors'] if e['index']>i]
   row.update(cut=j,source_raw_index=i,current=norm(S),previous=norm(prev),H=norm(sorted(HH)),U0=norm(sorted(U)),old_order=old,history_id=hist['job']['id'],history_sha256=sha(H/'outputs'/(hist['job']['id']+'.json')))
   dump(H/'history'/(ident+'.json'),dict(physical_prefix=norm(v[:j+1]),credits=[e for e in credits if e['edge']<j],old_actual_post_suffix=norm(v[j:]),old_raw_suffix=norm(raw[i:]),old_order=old,raw_index=i,post_cut=j))
   pool={};deadline=time.perf_counter()+20
   allowed=F-U-{S,tuple(c['base']),prev}
   for k in range(j,len(v)-1):
    if len(P-done[k+1])<2:continue
    a,z=v[k],v[k+1]
    for cell in sorted(allowed):
     counts['AABB_projections']+=1
     if counts['AABB_projections']%512==0:assert time.perf_counter()<deadline,'pool_deadline'
     if all(2*max(a[d],z[d])>=2*cell[d]-1 and 2*min(a[d],z[d])<=2*cell[d]+1 for d in (0,1)):pool.setdefault(cell,k)
   ordered=sorted(pool,key=lambda p:(pool[p],p[0],p[1]));row['pool_size']=len(ordered);row['candidate_order_first20']=[dict(cell=norm(p),first_possible_edge=pool[p]) for p in ordered[:20]]
   if not ordered:row['status']='empty_pool';continue
   for n,cell in enumerate(ordered[:20]):
    astart=time.perf_counter();deadline=astart+20;attempt=dict(slot=n+1,cell=norm(cell),first_possible_edge=pool[cell]);row['attempts'].append(attempt)
    counts['candidate_attempts']+=1;FE=F-{cell};assert U==P&FE-HH and not P-FE-HH and S in FE and prev in FE and tuple(c['base']) in FE
    collision=None
    for k in range(j,len(v)-1):
     assert time.perf_counter()<deadline,'qualification_deadline'
     counts['primary_cell_edge_tests']+=1;hit=slab(v[k],v[k+1],cell)
     if hit is not None:collision=dict(edge=k,interval=hit,pending_at_edge_end=len(P-done[k+1]),source_left=post['edges'][k]['left'],source_right=post['edges'][k]['right']);break
    attempt['collision']=collision
    if collision is None:attempt['status']='grid_only_block' if cell in raw[i:] else 'post_legal';attempt['seconds']=time.perf_counter()-astart;continue
    if not collision['interval']['strict_interior']:attempt['status']='touch_only';attempt['seconds']=time.perf_counter()-astart;continue
    if collision['pending_at_edge_end']<2:attempt['status']='not_coverage_ge2';attempt['seconds']=time.perf_counter()-astart;continue
    d,parents=reachable(FE,S,deadline,counts)
    if not U|{tuple(c['base'])}<=set(d):attempt['status']='unreachable';attempt['seconds']=time.perf_counter()-astart;continue
    attempt.update(status='selected',seconds=time.perf_counter()-astart,reachable=len(d));indstart=time.perf_counter();idead=indstart+20;indcounts=Counter();invalid=[]
    for k in range(j,len(v)-1):
     assert time.perf_counter()<idead,'qualification_independent_deadline'
     indcounts['independent_geometry_queries']+=1
     if not b['IG'].legal(FE,v[k],v[k+1]):invalid.append(k)
    assert invalid and invalid[0]==collision['edge'],'qualification geometry disagreement'
    assert S in parents and parents[S] is None and d[S]==0
    for q,parent in parents.items():
     assert time.perf_counter()<idead,'qualification_independent_deadline'
     indcounts['tree_rows']+=1;assert q in FE
     if q!=S:assert parent in parents and near(parent,q) and d[parent]+1==d[q]
    assert U|{tuple(c['base'])}<=set(parents)
    cert=dict(start=norm(S),rows=[dict(cell=norm(q),parent=norm(parents[q]),distance=d[q]) for q in sorted(d)],independent=dict(passed=True,invalid_post_edges=invalid,counts=dict(indcounts),seconds=time.perf_counter()-indstart))
    dump(H/'qualification'/(ident+'__reachability.json'),cert)
    ec=dict(c,name=ident,phase='event_response',free=norm(sorted(FE)),targets=norm(sorted(P&FE)),covered=norm(sorted(HH)),current=norm(S),previous=norm(prev),old_route=norm(raw[i:]),deferred_targets=[])
    phase_validate(ec,b['validate']);dump(H/'inputs'/(ident+'.json'),ec)
    row.update(status='qualified',selected_obstacle=norm(cell),blocked_old_post=collision,input='inputs/'+ident+'.json',input_sha256=sha(H/'inputs'/(ident+'.json')),independent_qualification=cert['independent']);break
   else:row['status']='exhausted_20'
  except AssertionError as ex:
   if str(ex) in ('pool_deadline','qualification_deadline','qualification_independent_deadline'):row.update(status='qualification_unresolved',reason=str(ex))
   else:row.update(status='qualification_contract_error',reason=repr(ex));raise
  finally:
   row['counts']=dict(counts);row['seconds']=time.perf_counter()-start;registry.append(row);dump(H/'qualification'/(ident+'.json'),row);dump(H/'state_registry.json',registry)
   print('QUALIFICATION',ident,row['status'],len(row['attempts']),flush=True)
 return registry
