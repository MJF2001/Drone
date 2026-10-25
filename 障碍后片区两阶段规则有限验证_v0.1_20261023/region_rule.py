"""One fixed first-recovery rule. No rollout, no post feedback, no global state."""
import time
from collections import deque

def adjacent(p):
 x,y=p
 return ((x+1,y),(x,y+1),(x-1,y),(x,y-1))

class Priority:
 def __init__(self,labels,free,base,tick,enabled=True):
  self.labels={k:set(map(tuple,v)) for k,v in labels.items()};self.free=set(free);self.base=base;self.tick=tick
  self.enabled=enabled;self.checked=False;self.S=None;self.phase='DEFAULT';self.check=None;self.transitions=[]
  self.rows={};self.counts={'rule_distance_rows':0,'rule_BFS_popped':0,'rule_distance_lookups':0,'local_changes':0,'recovery_changes':0}
  self.seconds=0.;self.release_pending=None
 def row(self,p):
  if p not in self.rows:
   assert len(self.rows)<3,'rule three-row bound'
   d={p:0};todo=deque([p]);self.counts['rule_distance_rows']+=1
   while todo:
    self.tick();q=todo.popleft();self.counts['rule_BFS_popped']+=1
    for r in adjacent(q):
     if r in self.free and r not in d:d[r]=d[q]+1;todo.append(r)
   self.rows[p]=d
  return self.rows[p]
 def lookup(self,row,q):
  self.counts['rule_distance_lookups']+=1
  return row[q]
 def inspect(self,Q,X,q0,index):
  if not self.enabled or self.checked:return
  begin=time.perf_counter();self.checked=True
  r={'index':index,'Q':sorted(Q),'counts':{},'q0':q0,'representatives':{},'conditions':[],'activated':False,'reason':None}
  self.check=r
  try:
   active={k:v&Q for k,v in self.labels.items() if v&Q};r['counts']={k:len(v) for k,v in active.items()}
   owners={p:[k for k,v in self.labels.items() if p in v] for p in Q}
   if any(len(v)!=1 for v in owners.values()):r['reason']='missing_or_overlapping_label';return
   if len(active)<2:r['reason']='single_region';return
   for k in active:
    for l in active:
     if k<l and any(q in self.labels[l] for p in self.labels[k] for q in adjacent(p)):
      r['reason']='touching_original_labels';return
   size=min(map(len,active.values()));small=[k for k,v in active.items() if len(v)==size]
   if len(small)!=1:r['reason']='minimum_tie';return
   S=small[0];r['S']=S
   if q0 not in active[S]:r['reason']='default_already_other';return
   db=self.row(self.base);dx=self.row(X)
   if any(q not in db or q not in dx for q in Q):r['reason']='unreachable';return
   reps={k:min(v,key=lambda q:(self.lookup(db,q),q)) for k,v in active.items()};r['representatives']=reps;rs=reps[S];ds=self.row(rs)
   for k in active:
    if k==S:continue
    rr=reps[k];e={'other':k,'d_R_B':self.lookup(db,rr),'d_R_S':self.lookup(ds,rr),'d_S_B':self.lookup(db,rs),'d_X_R':self.lookup(dx,rr),'d_X_S':self.lookup(dx,rs)}
    e['on_return']=e['d_R_B']==e['d_R_S']+e['d_S_B'];e['detour_strict']=e['d_X_R']<e['d_X_S']+e['d_R_S'];r['conditions'].append(e)
   if not all(z['on_return'] and z['detour_strict'] for z in r['conditions']):r['reason']='geometry_conditions_failed';return
   self.S=S;self.phase='OTHER';r['activated']=True;r['reason']='activated';r['S_pending_at_activation']=sorted(active[S])
   self.transitions.append({'index':index,'phase':'OTHER','Q_S':len(Q&self.labels[S]),'Q_other':len(Q-self.labels[S])})
  finally:self.seconds+=time.perf_counter()-begin
 def allowed(self,Q):
  return Q-self.labels[self.S] if self.enabled and self.phase=='OTHER' else Q
 def filter(self,options,Q):
  E=self.allowed(Q)
  return [r for r in options if tuple(r['cell']) in E] if self.enabled and self.phase=='OTHER' else options
 def moved(self,Q,index):
  if not self.enabled or self.phase!='OTHER':return
  if not Q:self.phase='DONE'
  elif not Q-self.labels[self.S]:self.phase='TAIL';self.release_pending=sorted(Q)
  elif not Q&self.labels[self.S]:self.phase='CANCELLED'
  else:return
  self.transitions.append({'index':index,'phase':self.phase,'Q_S':len(Q&self.labels[self.S]),'Q_other':len(Q-self.labels[self.S])})
 def export(self):
  return {'enabled':self.enabled,'checked':self.checked,'check':self.check,'S':self.S,'phase':self.phase,'transitions':self.transitions,'release_pending':self.release_pending,'counts':self.counts,'preparation_seconds':self.seconds,'detailed_profile':False}
