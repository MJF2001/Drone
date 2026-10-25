"""Independent original-source prefix scan and saved replacement validation.
No imports from clip/tail/join. No candidate generation or path tie rewrite.
"""
from common import *
from collections import Counter,deque
import math
def original(slot):
 ix=next(x for x in read(STRUCT/'pair_index.json') if x['key']==slot['key']);r=read(STRUCT/ix['file']);o=read(r['source'][slot['arm']]);reg=next(x for x in read((BASE if ix['dataset']=='base' else VAR)/'state_registry.json') if x['id']==ix['id']);return o,reg,r
def prefix(slot,packet):
 start=time.perf_counter();o,reg,r=original(slot);c=o['input'];raw=list(map(tuple,o['native']['raw']['route']));tr=o['diagnostic']['trigger'];k=tr['route_index'];q=tuple(tr['chosen_goal']);F=ps(c['free']);U=ps(c['targets'])-ps(c['covered']);pending=U-set(raw[:k+1]);assert packet['event']==c and packet['old_order']==reg['old_order'] and packet['seed']==20261020;assert packet['common_prefix']==norm(raw[:k+1]);assert packet['choice_state']==dict(current=tr['current'],previous=tr['previous'],pending=tr['pending'],source_index=k);assert packet['selected_q']==list(q)
 # An independent edge-index scan classifies each consumed edge by q-arrival,
 # checks the earliest eligible stop predicate at EVERY source vertex.
 stop=None;arrival=k if raw[k]==q else None;local=0;work=Counter()
 for i in range(k,len(raw)):
  if i>k:
   a,b=raw[i-1:i+1];assert a in F and b in F and abs(a[0]-b[0])+abs(a[1]-b[1])==1
   if arrival is not None:local+=1;assert b in pending
   pending.discard(b)
   if arrival is None and b==q:arrival=i
   work['source_edges_checked']+=1
  x,y=raw[i];opts={a for a in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if a in pending and a in F};work['stop_state_checks']+=1
  reasons=[]
  if not pending:reasons.append('all_pending_collected')
  if i-k>=64:reasons.append('total_64')
  if arrival is not None and not opts and pending:reasons.append('next_recovery_after_q')
  if local>=16:reasons.append('local_16')
  if reasons:stop=i;reason=reasons[0];break
 assert stop is not None
 state=packet['stop_state'];assert packet['finite_prefix']==norm(raw[k:stop+1])
 assert state==dict(current=list(raw[stop]),previous=list(raw[stop-1]) if stop>k else tr['previous'],pending=norm(sorted(pending)),new_tasks=norm(sorted(ps(tr['pending'])-pending)),edges=stop-k,local_edges=local,q_arrived=arrival is not None,reason=reason,source_start=k,source_stop=stop)
 # Every used source local edge matches original reward including true heading.
 for e in o['native']['raw']['trace']:
  if e['index']<k or e['index']>=stop:continue
  if e['kind']!='local':assert e['index']==k;continue
  i=e['index'];left=U-set(raw[:i+1]);x,y=raw[i];prev=raw[i-1] if i else tuple(c['previous']);opts=sorted(a for a in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if a in F and a in left);ds=[math.dist(a,c['predator']) for a in opts];lo,hi=min(ds),max(ds);scores=[]
  for a,d in zip(opts,ds):
   rd=(d-lo)/(hi-lo) if hi>lo else 0;rs=math.acos(max(-1,min(1,(prev[0]-x)*(a[0]-x)+(prev[1]-y)*(a[1]-y))))/math.pi;rb=1-sum(b in left and b in F for b in ((a[0]-1,a[1]),(a[0]+1,a[1]),(a[0],a[1]-1),(a[0],a[1]+1)))/4;scores.append((-(rd+2*rs+.5*rb),a));work['reward_options_checked']+=1
  assert raw[i+1]==min(scores)[1]
 return dict(passed=True,seconds=time.perf_counter()-start,source_route_sha256=r['source'][slot['arm']+'_sha256'],counts=dict(work),common_edges=k,finite_edges=stop-k,cut_reason=reason,old_order_matches_original_registry=True)
def replacement(slot,packet,out):
 start=time.perf_counter();assert out['passed'];counts=Counter();c=packet['event'];F=ps(c['free']);pending=ps(packet['stop_state']['pending']);route=list(map(tuple,out['tail']['route']));visits=out['tail']['visits'];old=list(map(tuple,packet['old_order']));assert pending<=set(old);assert route[0]==tuple(packet['stop_state']['current']);cursor=0;vi=0;seen=set();cache={}
 def shortest(a,b):
  counts['independent_distance_queries']+=1
  if a not in cache:
   ds={a:0};queue=deque([a]);counts['independent_BFS']+=1
   while queue:
    x,y=queue.popleft();counts['independent_BFS_popped']+=1
    for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
     counts['independent_BFS_neighbors']+=1
     if q in F and q not in ds:ds[q]=ds[x,y]+1;queue.append(q)
   cache[a]=ds
  return cache[a][b]
 def visit(goal,rank,kind):
  nonlocal vi,cursor,pending
  v=visits[vi];vi+=1;assert v['kind']==kind and v['old_rank']==rank and tuple(v['goal'])==goal and v['tail_start']==cursor;end=v['tail_stop'];segment=route[cursor:end+1];assert segment and segment[-1]==goal and v['pending_before']==norm(sorted(pending))
  for a,b in zip(segment,segment[1:]):assert a in F and b in F and abs(a[0]-b[0])+abs(a[1]-b[1])==1;counts['independent_tail_unit_edges']+=1
  assert end-cursor==shortest(route[cursor],goal);new=pending&set(segment);pending-=new;assert v['new_tasks']==norm(sorted(new));cursor=end
 for rank,goal in enumerate(old):
  duplicate=goal in seen;seen.add(goal);counts['old_scan_checks']+=1
  if duplicate or goal not in pending:continue
  visit(goal,rank,'task')
 assert not pending;visit(tuple(c['base']),None,'return');assert vi==len(visits) and cursor==len(route)-1<=4096
 joined=packet['common_prefix']+packet['finite_prefix'][1:]+out['tail']['route'][1:];assert joined==out['raw']['route'];full=list(map(tuple,joined));assert full[0]==tuple(c['current']) and full[-1]==tuple(c['base']);assert ps(c['targets'])<=ps(c['covered'])|set(full);assert len(full)-1==out['Jhat_raw']<=c['distance_budget'];assert c['covered']==packet['event']['covered']
 from frozen_shadow_center_20261023 import metrics
 from frozen_shadow_center_20261023.audit import _post_saved
 for name,view in out['views'].items():
  v=metrics.evaluate(c,view['path'],independent=True,grid=name=='A');assert v['metrics']==view['metrics'] and v['events']==view['events'];counts.update({'credit_'+name+'_'+k:z for k,z in v['counts'].items()})
 n=len(full)-1;u=len(ps(c['targets'])-ps(c['covered']));post=_post_saved.audit_one({'id':slot['id'],'limits':{'candidate_geometry':4096,'independent_geometry':n,'independent_service_intersections':n*u}},out['post_request_utf8'].encode(),out['post_response_utf8'].encode());assert post['passed'];counts.update({'post_'+k:v for k,v in post['counts'].items()});assert out['Jhat_post']==out['views']['B']['metrics']['length'] and out['Jhat_certificate']==out['views']['B']['metrics']['length_certificate']
 return dict(passed=True,counts=dict(counts),seconds=time.perf_counter()-start,post=post,tie_check='original path implementation and import-only diff hash bound; independent BFS checks shortestness, does not replace tie policy',source_suffix_used=False)
