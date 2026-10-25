"""Fixed earliest cut and ONE blocked cell per slot; no response outcomes read."""
from region_common import *
from collections import deque,Counter
from fractions import Fraction as R
def near(a,b):return sum(abs(x-y) for x,y in zip(a,b))==1
def slab(a,b,p):
 lo,hi=R(0),R(1)
 for j in (0,1):
  if a[j]==b[j]:
   if not R(p[j])-R(1,2)<a[j]<R(p[j])+R(1,2):return None
  else:
   l,h=sorted(((R(p[j])-R(1,2)-a[j])/(b[j]-a[j]),(R(p[j])+R(1,2)-a[j])/(b[j]-a[j])));lo=max(lo,l);hi=min(hi,h)
 if lo>=hi:return None
 t=(lo+hi)/2
 if not all(abs(a[j]+t*(b[j]-a[j])-p[j])<R(1,2) for j in (0,1)):return None
 return {'lo':[lo.numerator,lo.denominator],'hi':[hi.numerator,hi.denominator],'strict':True}
def qualify_all():
 assert not (H/'qualification_freeze.json').exists();b=bindings();rows=[]
 for slot in read(H/'plan.json')['slots']:
  start=time.perf_counter();counts=Counter();sid=slot['id'];row=dict(id=sid,status='pending',obstacle=slot['obstacle'],obstacle_attempts=1,alternative_cuts=0,counts={});hist=read(H/'outputs'/('history__'+sid+'.json'));row['history_sha256']=sha(H/'outputs'/('history__'+sid+'.json'))
  try:
   if not hist['passed'] or not hist['eligible']:row['status']='history_ineligible';continue
   c=hist['input'];P=ps(c['published_targets']);F=ps(c['free']);V=list(map(tuple,hist['post']['vertices']));raw=list(map(tuple,hist['native']['raw']['route']));C0=ps(slot['C0']);done=set();prefix_H=[set()]
   # An independent center-region implementation reconstructs all actual prefix
   # credits; source edge endpoints give the only permitted grid interface cut.
   for k,(a,z) in enumerate(zip(V,V[1:])):
    for p in P:
     counts['qualification_target_box_tests']+=1
     if all(5*max(a[j],z[j])>5*p[j]-1 and 5*min(a[j],z[j])<5*p[j]+1 for j in (0,1)):
      if b['region'].intersection(a,z,p,counts):done.add(p)
    prefix_H.append(set(done))
   from_saved=[set(tuple(e['cell']) for e in hist['views']['B']['events'] if e['new'] and (e['kind']=='collect_here' or e['edge']<j)) for j in range(len(V))]
   assert prefix_H==from_saved,'independent prefix credit disagreement'
   cut=next((j for j in range(1,len(V)) if C0<=prefix_H[j] and V[j] in P and near(V[j-1],V[j])),None)
   row['cut']=cut
   if cut is None:row['status']='no_registered_cut';continue
   HH=prefix_H[cut];U=P-HH;X=V[cut];previous=V[cut-1];i=hist['post']['edges'][cut-1]['right'];assert raw[i]==X and hist['post']['edges'][cut-1]['b']==list(X)
   assert X in HH and C0<=HH and near(previous,X)
   row.update(source_raw_index=i,current=X,previous=previous,H=sorted(HH),Q=sorted(U),event_label_counts={k:len(U&ps(v)) for k,v in slot['labels'].items()},true_heading_independent=True)
   prefix={'post_prefix':V[:cut+1],'post_suffix':V[cut:],'raw_suffix':raw[i:],'cut':cut,'source_raw_index':i,'covered':sorted(HH),'independent_prefix_counts':dict(counts),'history_sha256':row['history_sha256']};dump(H/'history'/(sid+'.json'),prefix)
   obstacle=tuple(slot['obstacle']);FE=F-{obstacle};assert obstacle in F,'static obstacle not free'
   row['checks']={'obstacle_not_current_or_base':obstacle not in {X,tuple(c['base'])},'obstacle_not_uncollected_task':obstacle not in U,'responsibility_unchanged':P&FE-HH==U and not P-FE-HH,'heading_available':previous in FE}
   hits=[]
   for k in range(cut,len(V)-1):
    counts['single_registered_cell_strict_edge_tests']+=1;e=slab(V[k],V[k+1],obstacle)
    if e:
     counts['independent_blockage_geometry']+=1;assert not b['IG'].legal(FE,V[k],V[k+1]),'independent blockage disagreement';hits.append(dict(edge=k,interval=e,source_left=hist['post']['edges'][k]['left'],source_right=hist['post']['edges'][k]['right']))
   row['blocked_actual_post_edges']=hits;row['checks']['actual_post_suffix_strictly_blocked']=bool(hits)
   expected={'S':4,'R':12}
   if sid.startswith('G4'):expected={'S':4 if sid.endswith('A') else 7,'R':8}
   elif sid=='G5-A':expected={'R':12}
   elif sid=='G5-B':expected={'S':4,'R':12}
   elif sid.startswith('G6'):expected={'S':4,'R':12,'T':16}
   actual={k:v for k,v in row['event_label_counts'].items() if v};row['checks']['registered_event_task_structure']=actual==expected;row['expected_event_counts']=expected
   # Reachability is audited even when the fixed obstacle misses the old plan.
   d={X:0};parents={X:None};todo=deque([X]);counts['reachability_BFS_calls']+=1
   while todo:
    a=todo.popleft();counts['reachability_BFS_popped']+=1
    for z in ((a[0]+1,a[1]),(a[0],a[1]+1),(a[0]-1,a[1]),(a[0],a[1]-1)):
     if z in FE and z not in d:d[z]=d[a]+1;parents[z]=a;todo.append(z)
   independent={X};front=[X]
   while front:
    a=front.pop();counts['independent_reachability_popped']+=1
    for z in ((a[0],a[1]-1),(a[0]-1,a[1]),(a[0],a[1]+1),(a[0]+1,a[1])):
     if z in FE and z not in independent:independent.add(z);front.append(z)
   assert independent==set(d)
   assert all(p==X or (near(p,parents[p]) and d[parents[p]]+1==d[p]) for p in d)
   row['checks']['all_tasks_base_reachable']=U|{tuple(c['base'])}<=set(d)
   dump(H/'qualification'/(sid+'__reachability.json'),{'rows':[dict(cell=p,distance=d[p],parent=parents[p]) for p in sorted(d)],'independent_passed':True})
   if all(row['checks'].values()):
    ec=dict(c,name=sid,phase='event_response',free=sorted(FE),targets=sorted(P&FE),covered=sorted(HH),current=X,previous=previous,old_route=raw[i:],deferred_targets=[]);phase_validate(norm(ec),b['validate']);dump(H/slot['event_input'],ec);row.update(status='qualified',input=slot['event_input'],input_sha256=sha(H/slot['event_input']))
   else:row.update(status='ineligible',failed_checks=[k for k,v in row['checks'].items() if not v])
  finally:
   row['counts']=dict(counts);row['seconds']=time.perf_counter()-start;rows.append(norm(row));dump(H/'qualification'/(sid+'.json'),row);dump(H/'state_registry.json',rows);print('QUAL',sid,row['status'],row.get('failed_checks'),flush=True)
 freeze={str(p.relative_to(H)):sha(p) for d in ('qualification','history','inputs') for p in (H/d).glob('*.json')};freeze['state_registry.json']=sha(H/'state_registry.json');dump(H/'qualification_freeze.json',freeze)
 return rows
if __name__=='__main__':qualify_all()
