"""Fixed scientific policy. No true outcome or saved route suffix inputs."""
from collections import Counter
from decimal import Decimal
import time
def ps(x):return set(map(tuple,x))
def normpoint(x):return None if x is None else list(x)
def adjacent_pending(q,pending,free):
 x,y=q;return any(p in pending and p in free for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
def clip(path,choice_index,q,pending,free,previous,local_cap=16,total_cap=64):
 """Extractor only: sequential saved vertices; predicate before each next edge.
 Does not query later trace/goal/end point or take real return edges.
 """
 q=tuple(q);remaining=set(pending);free=set(free);out=[tuple(path[choice_index])];arrived=out[-1]==q;local=0;i=choice_index
 while True:
  if not remaining:reason='all_pending_collected';break
  if len(out)-1>=total_cap:reason='total_64';break
  if arrived and not adjacent_pending(out[-1],remaining,free):reason='next_recovery_after_q';break
  if arrived and local>=local_cap:reason='local_16';break
  a=out[-1];i+=1;b=tuple(path[i]);assert a in free and b in free and abs(a[0]-b[0])+abs(a[1]-b[1])==1
  if arrived:assert b in remaining;local+=1
  out.append(b);remaining.discard(b)
  if b==q:arrived=True
 return dict(path=[list(p) for p in out],current=list(out[-1]),previous=list(out[-2]) if len(out)>1 else normpoint(previous),pending=[list(p) for p in sorted(remaining)],new_tasks=[list(p) for p in sorted(set(pending)-remaining)],edges=len(out)-1,local_edges=local,q_arrived=arrived,reason=reason,source_start=choice_index,source_stop=i)
class Unavailable(Exception):
 def __init__(self,reason,details=None):super().__init__(reason);self.details=details
def validate_packet(packet,whitelist):
 assert set(packet)==set(whitelist),'input_whitelist'
 assert packet['schema']=='shadow_crop_v1','input_schema'
def tail(packet,path_query,deadline,edge_cap=4096):
 c=packet['event'];F=ps(c['free']);start=packet['stop_state'];remaining=ps(start['pending']);old=list(map(tuple,packet['old_order']));counts=Counter({k:0 for k in ('old_order_entries_scanned','old_entries_skipped','old_duplicate_entries','task_path_queries','return_path_queries','path_queries','tail_new_edges','tail_new_tasks','incidental_tasks')});route=[tuple(start['current'])];visits=[];seen=set()
 def fail(reason):raise Unavailable(reason,dict(route=[list(p) for p in route],visits=visits,counts=dict(counts),pending_after=[list(p) for p in sorted(remaining)]))
 if remaining-set(old):fail('old_order_missing_tasks')
 def append_connection(goal,rank,kind):
  if time.perf_counter()>=deadline:fail('tail_soft_deadline')
  counts['path_queries']+=1;counts['task_path_queries' if kind=='task' else 'return_path_queries']+=1
  segment=tuple(map(tuple,path_query(route[-1],goal)));assert segment and segment[0]==route[-1] and segment[-1]==goal
  before=set(remaining);begin=len(route)-1
  for a,b in zip(segment,segment[1:]):
   if time.perf_counter()>=deadline:fail('tail_soft_deadline')
   if counts['tail_new_edges']>=edge_cap:fail('tail_edge_cap')
   assert a in F and b in F and abs(a[0]-b[0])+abs(a[1]-b[1])==1
   route.append(b);remaining.discard(b);counts['tail_new_edges']+=1
  new=before-remaining;counts['tail_new_tasks']+=len(new);counts['incidental_tasks']+=len(new-{goal})
  visits.append(dict(kind=kind,old_rank=rank,goal=list(goal),tail_start=begin,tail_stop=len(route)-1,pending_before=[list(p) for p in sorted(before)],new_tasks=[list(p) for p in sorted(new)]))
 for rank,goal in enumerate(old):
  counts['old_order_entries_scanned']+=1
  duplicate=goal in seen;seen.add(goal);counts['old_duplicate_entries']+=int(duplicate)
  if duplicate or goal not in remaining:counts['old_entries_skipped']+=1;continue
  append_connection(goal,rank,'task')
 assert not remaining
 append_connection(tuple(c['base']),None,'return')
 if time.perf_counter()>=deadline:fail('tail_soft_deadline')
 return dict(route=[list(p) for p in route],visits=visits,counts=dict(counts),pending_after=[])
def join(common,finite,tailpath):
 a=list(map(tuple,common));b=list(map(tuple,finite));c=list(map(tuple,tailpath));assert a and b and c and a[-1]==b[0] and b[-1]==c[0]
 out=a+b[1:]+c[1:];assert all(x!=y for x,y in zip(out,out[1:]));return [list(p) for p in out]
def decide(eligible,delta_interval,exact_zero=False):
 if not eligible:return dict(choice='OFF',reason='unavailable',delta_sign=None)
 lo,hi=map(Decimal,delta_interval);eps=Decimal('0.00000001')
 if hi < -eps:return dict(choice='ALT1',reason='estimated_improvement',delta_sign=-1)
 if exact_zero:return dict(choice='OFF',reason='estimated_equal',delta_sign=0)
 if lo>=-eps and hi<0:return dict(choice='OFF',reason='negative_within_numeric_guard',delta_sign=-1)
 if lo>0:return dict(choice='OFF',reason='estimated_deterioration',delta_sign=1)
 return dict(choice='OFF',reason='numerically_uncertain',delta_sign=None)
