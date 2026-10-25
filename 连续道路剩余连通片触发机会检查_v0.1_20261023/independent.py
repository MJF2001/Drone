"""Independent union-find, distance wavefronts and gate reconstruction."""
import time
def components(S,C):
 start=time.perf_counter();C['component_calls']+=1;parent={p:p for p in S}
 def root(p):
  while parent[p]!=p:p=parent[p]
  return p
 for x,y in sorted(S):
  C['component_cells']+=1
  for q in ((x,y+1),(x+1,y)):
   C['component_neighbor_checks']+=1
   if q in parent:
    a,b=root((x,y)),root(q)
    if a!=b:parent[b]=a
 groups={}
 for p in S:groups.setdefault(root(p),[]).append(p)
 C['component_seconds']+=time.perf_counter()-start
 return sorted((sorted(v) for v in groups.values()),key=lambda v:v[0])
def row(F,S,C):
 start=time.perf_counter();C['distance_rows']+=1;d={S:0};front={S};level=0
 while front:
  following=set()
  for x,y in front:
   C['distance_cells']+=1
   for q in ((x,y-1),(x-1,y),(x,y+1),(x+1,y)):
    C['distance_neighbor_checks']+=1
    if q in F and q not in d:following.add(q)
  level+=1
  for p in following:d[p]=level
  front=following
 C['distance_seconds']+=time.perf_counter()-start
 return d
def extract(c,raw,initial):
 target={tuple(p) for p in c['targets']};covered={tuple(p) for p in c['covered']};pending=target-covered;U=sorted(pending);free={tuple(p) for p in c['free']};start=tuple(c['current']);assert {tuple(p) for p in initial['new_H']}==({start}&pending)
 cursor=0;prefix=[];found=None
 for i,record in enumerate(raw['trace']):
  end=record['index']
  while cursor<=end:
   p=tuple(raw['route'][cursor]);assert p in free
   if prefix:assert abs(p[0]-prefix[-1][0])+abs(p[1]-prefix[-1][1])==1
   prefix.append(p);pending.discard(p);cursor+=1
  X=prefix[-1];prev=prefix[-2] if len(prefix)>1 else tuple(c['previous']) if c['previous'] is not None else None
  assert X==tuple(record['current']) and len(pending)==record['pending_count']
  if record['kind']!='return':assert prev==(tuple(record['previous']) if record['previous'] is not None else None)
  if record['kind']=='recovery':found=(i,end,record,X,prev);break
  if record['kind']=='return':break
 if found is None:return dict(has_recovery=False,U=U,Q=None,prefix=None,trace_prefix=None)
 i,end,e,X,prev=found
 assert pending and not pending&covered
 return dict(has_recovery=True,U=U,Q=sorted(pending),X=X,previous=prev,q0=tuple(e['goal']),raw_index=end,trace_index=i,prefix=prefix,trace_prefix=raw['trace'][:i+1],predicted_new=sorted((target-covered)-pending))
def judge(Q,F,B,X,q0,parts,getrow):
 out=dict(component_sizes=[len(p) for p in parts],S=None,representatives=None,conditions=None,trigger=False,reason=None,q0_verified=None)
 dist=getrow(X);assert set(Q)<=set(dist);ordered=sorted(Q,key=lambda p:(dist[p],p));assert ordered[0]==q0,'independent q0 mismatch';out['q0_verified']=True
 if len(parts)==1:out['reason']='single_component';return out
 sizes=sorted((len(p),i) for i,p in enumerate(parts))
 if sizes[0][0]==sizes[1][0]:out['reason']='minimum_tie';return out
 chosen=sizes[0][1];out['S']=f'C{chosen+1:02}';out['S_members']=parts[chosen]
 if q0 not in parts[chosen]:out['reason']='default_already_other';return out
 db=getrow(B);reps=[sorted(p,key=lambda a:(db[a],a))[0] for p in parts];center=reps[chosen];dr=getrow(center);out['representatives']={f'C{i+1:02}':p for i,p in enumerate(reps)};facts=[];ok=True
 for i,p in enumerate(reps):
  if i!=chosen:
   eq=(dr[p]+db[center]==db[p]);strict=(dist[center]+dr[p]>dist[p]);facts.append(dict(other=f'C{i+1:02}',d_R_B=db[p],d_R_S=dr[p],d_S_B=db[center],d_X_R=dist[p],d_X_S=dist[center],on_return=eq,detour_strict=strict));ok=ok and eq and strict
 out['conditions']=facts;out['trigger']=ok;out['reason']='trigger_opportunity' if ok else 'geometry_conditions_failed';return out
