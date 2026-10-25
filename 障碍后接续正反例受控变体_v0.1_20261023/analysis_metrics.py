"""Saved-result diagnostics; no planning or visibility searches."""
from common import *
from fractions import Fraction as Q
from math import isqrt
def adj(p):x,y=p;return {(x-1,y),(x+1,y),(x,y-1),(x,y+1)}
def common_point(a,b):
 k=0
 while k<min(len(a),len(b)) and a[k]==b[k]:k+=1
 return k-1
def witness(path,k,q):
 service=next((j for j in range(k+1,len(path)) if path[j]==q),None)
 if service is None:return dict(status='uncompleted',segments=None),set()
 seg=[];indices=set();i=k+1
 inside=lambda p:sum(abs(x-y) for x,y in zip(p,q))<=1
 while i<=service:
  if inside(path[i-1]) and not inside(path[i]):
   j=i
   while j<=service and not inside(path[j]):j+=1
   if j>service:return dict(status='unclosed',segments=None),set()
   seg.append(dict(start=i-1,end=j,length=j-i+1,vertices=norm(path[i-1:j+1])));indices.update(range(i-1,j));i=j+1
  else:i+=1
 return dict(status='complete',first_native_service_index=service,segments=seg),indices
def shared_C(path,k,Qstar):
 if not Qstar:return None
 indexes=[next((j for j in range(k+1,len(path)) if path[j]==q),None) for q in Qstar]
 if any(j is None for j in indexes):return None
 s=max(indexes);C=s-k;ret=len(path)-1-s
 assert k+C+ret==len(path)-1
 return dict(common_prefix_edges=k,last_common_pending_service_index=s,C=C,return_after_common_pending=ret,identity_total=k+C+ret)
def h2(c,off,alt,trigger):
 a=list(map(tuple,off['native']['raw']['route']));z=list(map(tuple,alt['native']['raw']['route']));k=common_point(a,z)
 if a==z:return dict(classification='undetermined_same_physical_route',C_difference=0,W_difference=0)
 if k<0 or k+1>=min(len(a),len(z)):return dict(classification='undetermined_terminal_prefix')
 p=a[k];Qstar=ps(c['targets'])-ps(c['covered'])-set(a[:k+1]);L=(adj(p)&Qstar)-{a[k+1]};Ca=shared_C(a,k,Qstar);Cz=shared_C(z,k,Qstar)
 out=dict(common_index=k,p=norm(p),Qstar=norm(sorted(Qstar)),u_OFF=norm(a[k+1]),u_ALT1=norm(z[k+1]),L=norm(sorted(L)),C_OFF=Ca,C_ALT1=Cz,witnesses={},definition='common physical p, fixed Adj4 leftover and radius1; W is edge-union descriptive travel, not deletable waste')
 if not Ca or not Cz:out['classification']='undetermined_empty_or_uncompleted';return out
 allsets=[]
 for arm,path in [('OFF',a),('ALT1',z)]:
  edges=set();rows=[]
  for q in sorted(L):
   w,ee=witness(path,k,q);edges|=ee
   for seg in w.get('segments') or []:seg['new_tasks']=norm(sorted((ps(c['targets'])-ps(c['covered'])-set(path[:seg['start']+1]))&set(path[seg['start']+1:seg['end']+1])))
   rows.append(dict(task=norm(q),**w))
  out['witnesses'][arm]=dict(tasks=rows,edge_union=sorted(edges),W=len(edges));allsets.append(edges)
 prev=a[k-1] if k else (tuple(c['previous']) if c['previous'] is not None else None)
 turn=None
 if prev is not None:
  v=(p[0]-prev[0],p[1]-prev[1]);w=(a[k+1][0]-p[0],a[k+1][1]-p[1]);turn=v[0]*w[1]!=v[1]*w[0] or v[0]*w[0]+v[1]*w[1]<0
 event=off['native']['raw']['trace'][trigger['trace_record']];next_event=off['native']['raw']['trace'][trigger['trace_record']+1]
 end=next_event['index'];at_end=k==end and tuple(event['goal'])==p;local=next_event['kind']=='local'
 out.update(at_default_recovery_end=at_end,default_next_local=local,default_turn=turn,C_difference=Cz['C']-Ca['C'],W_difference=len(allsets[1])-len(allsets[0]))
 out['classification']='candidate_compatible' if L and at_end and local and turn and len(allsets[0])>len(allsets[1]) and Cz['C']<Ca['C'] else 'undetermined_or_not_supported_by_fixed_witness'
 return out
def phases(raw,trigger):
 route=list(map(tuple,raw['route']));U=ps(trigger['pending']);k=trigger['route_index'];re=raw['trace'][trigger['trace_record']+1]['index'];last=max(next(i for i,p in enumerate(route) if p==q) for q in U)
 v=[k,re-k,last-re,len(route)-1-last];assert sum(v)==len(route)-1
 return dict(before_trigger=v[0],recovery=v[1],after_own_goal_coverage=v[2],return_after_last=v[3],last_native_cell=norm(route[last]),total=sum(v))
def independent_sign(saved):
 terms={int(t['r']):Q(t['c']['n'],t['c']['d']) for t in saved['terms']}
 if not terms:return 0,dict(bits=0,terms=0)
 for bits in (16,32,64,128,256,512):
  scale=1<<bits;lo=hi=Q(0)
  for r,c in terms.items():
   n=isqrt(r*scale*scale);a=Q(n,scale);b=a if n*n==r*scale*scale else Q(n+1,scale)
   lo+=c*(a if c>0 else b);hi+=c*(b if c>0 else a)
  if lo>0:return 1,dict(bits=bits,terms=len(terms),lower=str(lo),upper=str(hi))
  if hi<0:return -1,dict(bits=bits,terms=len(terms),lower=str(lo),upper=str(hi))
 return None,dict(bits=512,terms=len(terms),status='numeric_unresolved')
def independent_path_terms(path):
 # Independent construction from physical integer vertices, not Expr terms.
 from collections import Counter
 out=Counter()
 for a,b in zip(path,path[1:]):
  n=sum((x-y)**2 for x,y in zip(a,b))
  if n:
   d=max(k for k in range(1,isqrt(n)+1) if n%(k*k)==0);out[n//(d*d)]+=d
 return out
def pair(row,off,alt,b):
 start=time.perf_counter();tr=off['diagnostic']['trigger'];ta=alt['diagnostic']['trigger']
 for k in ('trace_record','route_index','current','previous','pending','default_goal','alternative_goal'):assert tr[k]==ta[k]
 E=b['exact'].Expr;cert=b['exact'].certificate
 x=E.load(off['views']['B']['metrics']['length_certificate']['exact']);y=E.load(alt['views']['B']['metrics']['length_certificate']['exact']);delta=y-x
 sg=delta.sign();ind,receipt=independent_sign(delta.save());assert ind==sg
 t0=independent_path_terms(off['post']['vertices']);t1=independent_path_terms(alt['post']['vertices']);diff={r:Q(t1[r]-t0[r]) for r in t0.keys()|t1.keys() if t1[r]!=t0[r]}
 assert diff==delta.terms,'independent route arithmetic disagrees';receipt['independent_from_physical_vertices']=True
 da=ta['alternative_distance']-ta['default_distance'];assert da>=0
 rawdelta=len(alt['native']['raw']['route'])-len(off['native']['raw']['route']);same_raw=off['native']['raw']['route']==alt['native']['raw']['route'];same_post=off['post']['vertices']==alt['post']['vertices'];pa=phases(off['native']['raw'],tr);pz=phases(alt['native']['raw'],ta)
 strict=da>0 and sg<0 and not same_raw and off['post_envelope']['fallback'] is None and alt['post_envelope']['fallback'] is None
 h=h2(off['input'],off,alt,tr)
 if h['classification']=='candidate_compatible':h['classification']='compatible_with_narrow_H2' if sg<0 else 'W_and_C_reduced_but_complete_not_shorter'
 out=dict(id=row['id'],base_geometry=row['base_geometry'],family=row['family'],valid_pair=True,default_target=tr['default_goal'],alternative_target=tr['alternative_goal'],candidate_tags=tr['tags'],delta_recovery=da,delta_raw=rawdelta,delta_post_certificate=cert(delta),delta_post_display=alt['views']['B']['metrics']['length']-off['views']['B']['metrics']['length'],delta_post_sign=sg,independent_sign=receipt,delta_percent=100*(alt['views']['B']['metrics']['length']-off['views']['B']['metrics']['length'])/off['views']['B']['metrics']['length'],raw_same=same_raw,post_same=same_post,classification='same_physical_route_zero' if same_raw and same_post else 'same_raw_post_difference_excluded' if same_raw else 'shorter' if sg<0 else 'longer' if sg>0 else 'equal_different_route',strict_H1=strict,phases_OFF=pa,phases_ALT1=pz,H2=h,H3_return_required_for_raw_gain=rawdelta<0 and (sum([pz[k]-pa[k] for k in ('before_trigger','recovery','after_own_goal_coverage')])>=0) and pz['return_after_last']<pa['return_after_last'],H4_post_required_for_net_gain=sg<0 and rawdelta>=0,delta_geometry_display=(alt['views']['B']['metrics']['length']-off['views']['B']['metrics']['length'])-rawdelta)
 old=ps([]);prefix=off['native']['raw']['route'][:tr['route_index']+1];ref=off['input']['old_route'];equal=prefix==ref[:len(prefix)] and len(prefix)<=len(ref)
 block=row['blocked_old_post'];offset=row['source_raw_index'];lo,hi=block['source_left']-offset,block['source_right']-offset
 out['old_plan_correspondence']=dict(E_prefix_equals_old_raw_suffix_prefix=equal,old_blocked_post_edge=block['edge'],old_blocked_source_interval_from_cut=[lo,hi],trigger_relation='before_blocked_source_interval' if equal and tr['route_index']<lo else 'within_blocked_source_interval' if equal and tr['route_index']<=hi else 'after_blocked_source_interval' if equal else 'unknown_no_unique_prefix_correspondence',interpretation_only=True)
 assert time.perf_counter()-start<30
 out['metric_audit_seconds']=time.perf_counter()-start
 return out
