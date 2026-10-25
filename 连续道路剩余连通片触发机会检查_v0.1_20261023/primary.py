"""Description/trigger only. No solver imports, parents or path reconstruction."""
from collections import deque
import time
def points(v):
 assert isinstance(v,(list,tuple))
 for p in v:assert isinstance(p,(list,tuple)) and len(p)==2 and all(type(z) is int for z in p)
 return set(map(tuple,v))
def components(S,C):
 t=time.perf_counter();C['component_calls']+=1;left=set(S);out=[]
 while left:
  p=min(left);left.remove(p);stack=[p];part={p}
  while stack:
   x,y=stack.pop();C['component_cells']+=1
   for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    C['component_neighbor_checks']+=1
    if q in left:left.remove(q);stack.append(q);part.add(q)
  out.append(sorted(part))
 C['component_seconds']+=time.perf_counter()-t
 return sorted(out,key=lambda p:p[0])
def row(F,X,C):
 t=time.perf_counter();C['distance_rows']+=1;dist={X:0};todo=deque([X])
 while todo:
  x,y=todo.popleft();C['distance_cells']+=1
  for p in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
   C['distance_neighbor_checks']+=1
   if p in F and p not in dist:dist[p]=dist[x,y]+1;todo.append(p)
 C['distance_seconds']+=time.perf_counter()-t
 return dist
def extract(c,raw,initial):
 F=points(c['free']);T=points(c['targets']);H=points(c['covered']);P=points(c['published_targets']);D=points(c['deferred_targets']);assert T==P&F and D==P-F-H
 start=tuple(c['current']);new={start}&T-H;assert new==points(initial['new_H'])
 first=next((i for i,e in enumerate(raw['trace']) if e['kind']=='recovery'),None)
 if first is None:return dict(has_recovery=False,U=sorted(T-H),Q=None,prefix=None,trace_prefix=None)
 e=raw['trace'][first];k=e['index'];prefix=raw['route'][:k+1];assert tuple(prefix[0])==start and points(prefix)<=F
 assert all(sum(abs(a[j]-b[j]) for j in (0,1))==1 for a,b in zip(prefix,prefix[1:]))
 Q=T-H-points(prefix);X=tuple(prefix[-1]);prev=tuple(prefix[-2]) if len(prefix)>1 else tuple(c['previous']) if c['previous'] is not None else None
 assert Q and len(Q)==e['pending_count'] and X==tuple(e['current']) and prev==(tuple(e['previous']) if e['previous'] is not None else None)
 for a in raw['trace'][:first+1]:
  at=a['index'];assert 0<=at<=k and tuple(raw['route'][at])==tuple(a['current'])
  assert a['pending_count']==len(T-H-points(prefix[:at+1]))
  p=tuple(prefix[at-1]) if at else tuple(c['previous']) if c['previous'] is not None else None
  assert p==(tuple(a['previous']) if a['previous'] is not None else None)
 assert Q.isdisjoint(H|points(prefix))
 return dict(has_recovery=True,U=sorted(T-H),Q=sorted(Q),X=X,previous=prev,q0=tuple(e['goal']),raw_index=k,trace_index=first,prefix=prefix,trace_prefix=raw['trace'][:first+1],predicted_new=sorted((T-H)&points(prefix)))
def judge(Q,F,B,X,q0,parts,getrow):
 result=dict(component_sizes=[len(p) for p in parts],S=None,representatives=None,conditions=None,trigger=False,reason=None,q0_verified=None)
 dx=getrow(X);assert Q<=dx.keys();assert q0==min(Q,key=lambda p:(dx[p],p)),'q0 not original complete-Q nearest';result['q0_verified']=True
 if len(parts)<2:result['reason']='single_component';return result
 n=min(map(len,parts));small=[i for i,p in enumerate(parts) if len(p)==n]
 if len(small)!=1:result['reason']='minimum_tie';return result
 s=small[0];result['S']=f'C{s+1:02}';result['S_members']=parts[s]
 if q0 not in parts[s]:result['reason']='default_already_other';return result
 db=getrow(B);assert Q<=db.keys();reps=[min(p,key=lambda z:(db[z],z)) for p in parts];rs=reps[s];ds=getrow(rs);result['representatives']={f'C{i+1:02}':p for i,p in enumerate(reps)};result['conditions']=[]
 for i,r in enumerate(reps):
  if i==s:continue
  result['conditions'].append(dict(other=f'C{i+1:02}',d_R_B=db[r],d_R_S=ds[r],d_S_B=db[rs],d_X_R=dx[r],d_X_S=dx[rs],on_return=db[r]==ds[r]+db[rs],detour_strict=dx[r]<dx[rs]+ds[r]))
 result['trigger']=all(p['on_return'] and p['detour_strict'] for p in result['conditions']);result['reason']='trigger_opportunity' if result['trigger'] else 'geometry_conditions_failed';return result
