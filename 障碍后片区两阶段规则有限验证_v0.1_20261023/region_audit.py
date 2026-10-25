"""Independent BFS/reward/phase reconstruction. Does not import rule or native."""
import math,time
from collections import deque,Counter
def audit(c,raw,on=False):
 start=time.perf_counter();counts=Counter();F=set(map(tuple,c['free']));P=set(map(tuple,c['targets']));Q=P-set(map(tuple,c['covered']))-{tuple(c['current'])};path=list(map(tuple,raw['route']));trace=raw['trace'];L={k:set(map(tuple,v)) for k,v in c['labels'].items()};B=tuple(c['base']);phase='DEFAULT';checked=False;S=None;check=None;trans=[];receipts=[];cursor=0;release=None
 def nbr(p):return ((p[0]-1,p[1]),(p[0],p[1]-1),(p[0]+1,p[1]),(p[0],p[1]+1))
 def distances(p):
  counts['BFS_calls']+=1;d={p:0};todo=deque([p])
  while todo:
   assert time.perf_counter()-start<150,'audit deadline'
   a=todo.popleft();counts['BFS_popped']+=1
   for b in nbr(a):
    if b in F and b not in d:d[b]=d[a]+1;todo.append(b)
  return d
 def prepare(X,q0,index):
  active={k:Q&v for k,v in L.items() if Q&v};r={'index':index,'Q':sorted(Q),'counts':{k:len(v) for k,v in active.items()},'q0':q0,'representatives':{},'conditions':[],'activated':False,'reason':None};chosen=None
  if any(sum(p in v for v in L.values())!=1 for p in Q):r['reason']='missing_or_overlapping_label'
  elif len(active)<2:r['reason']='single_region'
  elif any(a<b and any(p in L[b] for q in L[a] for p in nbr(q)) for a in active for b in active):r['reason']='touching_original_labels'
  else:
   sizes=sorted((len(v),k) for k,v in active.items())
   if sizes[0][0]==sizes[1][0]:r['reason']='minimum_tie'
   else:
    chosen=sizes[0][1];r['S']=chosen
    if q0 not in active[chosen]:r['reason']='default_already_other'
    else:
     db=distances(B);dx=distances(X)
     if not Q<=db.keys() or not Q<=dx.keys():r['reason']='unreachable'
     else:
      reps={k:sorted(v,key=lambda p:(db[p],p))[0] for k,v in active.items()};r['representatives']=reps;rs=reps[chosen];ds=distances(rs)
      for k in active:
       if k!=chosen:
        p=reps[k];r['conditions'].append(dict(other=k,d_R_B=db[p],d_R_S=ds[p],d_S_B=db[rs],d_X_R=dx[p],d_X_S=dx[rs],on_return=db[p]==ds[p]+db[rs],detour_strict=dx[p]<dx[rs]+ds[p]))
      if all(e['on_return'] and e['detour_strict'] for e in r['conditions']):r.update(activated=True,reason='activated',S_pending_at_activation=sorted(active[chosen]))
      else:r['reason']='geometry_conditions_failed'
  return r,chosen
 assert raw['status']=='core_complete' and path[0]==tuple(c['current']) and path[-1]==B and set(path)<=F and P<=set(path)|set(map(tuple,c['covered']))
 assert len(path)-1<=min(4096,c['distance_budget'])
 assert all(sum(abs(x-y) for x,y in zip(a,b))==1 for a,b in zip(path,path[1:]))
 for i,e in enumerate(trace):
  X=path[cursor];prev=path[cursor-1] if cursor else (tuple(c['previous']) if c['previous'] is not None else None);goal=tuple(e['goal']);end=trace[i+1]['index'] if i+1<len(trace) else len(path)-1;seg=path[cursor:end+1]
  assert e['index']==cursor and tuple(e['current'])==X and e['pending_count']==len(Q) and seg[-1]==goal
  if e['kind']=='return':assert not Q and goal==B and end-cursor==distances(X)[B]
  else:
   assert (tuple(e['previous']) if e['previous'] is not None else None)==prev
   opts=sorted(Q&F&set(nbr(X)));ds=[math.dist(p,c['predator']) for p in opts];rows=[]
   for p,d in zip(opts,ds):
    rd=(d-min(ds))/(max(ds)-min(ds)) if max(ds)>min(ds) else 0.;rs=0. if prev is None else math.acos(max(-1,min(1,sum((prev[j]-X[j])*(p[j]-X[j]) for j in (0,1)))))/math.pi;rb=1-sum(a in Q&F for a in nbr(p))/4
    rows.append(dict(cell=p,distance_reward=rd,straight_reward=rs,boundary_reward=rb,score=rd+2*rs+.5*rb))
   if on and not rows and not checked:
    checked=True;dx=distances(X);q0=min(Q,key=lambda p:(dx[p],p));check,small=prepare(X,q0,cursor)
    if check['activated']:S=small;phase='OTHER';trans.append(dict(index=cursor,phase=phase,Q_S=len(Q&L[S]),Q_other=len(Q-L[S])))
   E=Q-L[S] if phase=='OTHER' else Q;filtered=[r for r in rows if r['cell'] in E]
   if on:
    assert e['phase']==phase and set(map(tuple,e['Q']))==Q and set(map(tuple,e['allowed']))==E
    actual=e['original_options'];assert len(actual)==len(rows)
    for a,b in zip(rows,actual):
     assert a['cell']==tuple(b['cell'])
     assert all(abs(a[k]-b[k])<1e-12 for k in ('score','distance_reward','straight_reward','boundary_reward'))
   if filtered:
    assert e['kind']=='local' and end==cursor+1 and goal==min(filtered,key=lambda r:(-r['score'],r['cell']))['cell']
    assert len(e['options'])==len(filtered)
    for a,b in zip(filtered,e['options']):
     assert a['cell']==tuple(b['cell']) and abs(a['score']-b['score'])<1e-12
   else:
    dx=distances(X);assert E and e['kind']=='recovery' and goal==min(E,key=lambda p:(dx[p],p)) and end-cursor==dx[goal]
   if phase=='OTHER':assert goal not in L[S]
  receipts.append(dict(index=cursor,end=end,kind=e['kind'],phase=phase,Q=sorted(Q),allowed=sorted(Q-L[S] if phase=='OTHER' else Q),goal=goal,new_tasks=sorted(Q&set(seg))))
  for j in range(cursor+1,end+1):
   Q.discard(path[j])
   if phase=='OTHER':
    if not Q:phase='DONE'
    elif Q<=L[S]:phase='TAIL';release=sorted(Q)
    elif not Q&L[S]:phase='CANCELLED'
    else:continue
    trans.append(dict(index=j,phase=phase,Q_S=len(Q&L[S]),Q_other=len(Q-L[S])))
  cursor=end
 assert not Q and cursor==len(path)-1
 if on:
  r=raw['rule'];norm=lambda x:__import__('json').loads(__import__('json').dumps(x))
  assert r['checked']==checked and r['S']==S and r['phase']==phase and r['check']==norm(check) and r['transitions']==norm(trans) and r['release_pending']==norm(release) and r['counts']['rule_distance_rows']<=3
 return dict(passed=True,check=check,S=S,phase=phase,transitions=trans,release_pending=release,decisions=receipts,counts=dict(counts),seconds=time.perf_counter()-start,connector_tie_scope='frozen deterministic path implementation bound; independent BFS shortestness')
