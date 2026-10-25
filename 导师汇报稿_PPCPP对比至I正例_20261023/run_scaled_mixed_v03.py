"""Bounded report-only size and multi-event experiment. No frozen code changes."""
from pathlib import Path
import json,sys,os,subprocess,collections,math,hashlib
from run_front_block import read,write,sha,pts
H=Path(__file__).resolve().parent;R=H.parent;O=H/'分尺度严格受阻与综合展示_v0.3_20261024';PREV=H/'分尺度严格受阻与综合展示_v0.2_20261024';OLD=R/'七算法共同预算比较_v0.3_Cstar07_20261020'
METHODS=['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP','LOCAL_P2','ORIENT4']
def reachable(F,start):
 seen={tuple(start)};q=collections.deque(seen)
 while q:
  x,y=q.popleft()
  for z in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
   if z in F and z not in seen:seen.add(z);q.append(z)
 return seen
def valid(s,r):
 assert r and r[0]==s['current'] and r[-1]==s['base'] and pts(r)<=pts(s['free']);assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]));assert pts(s['targets'])<=pts(s['covered'])|pts(r);assert len(r)-1<=s['distance_budget']
def main():
 assert not O.exists();O.mkdir();[(O/k).mkdir() for k in ['inputs','jobs','results','logs']]
 sources=read(H/'前方未飞覆盖路段受阻展示_v0.1_20261024/protocol.json')['sources'];sources[str(Path(__file__).resolve())]=sha(__file__)
 configs=[dict(size=s,n=n,h=h,width=width,leg=leg) for s,n,h,width,leg in [('small',10,6,5,5),('medium',20,8,6,7),('large',30,10,8,9)]]
 protocol=dict(configs=configs,methods=METHODS,seed=20261020,budget=20,max_new_entries=139,sources=sources,
 rules='Mixed: reuse one genuine PPCPP initial plan for common initial prefix; each method then executes independently. First event at common initial prefix reaching 20% original tasks; subsequent events after exactly 4 additional executed unit moves each (shared flight-step checkpoints, NOT coverage thresholds): straight expansion, obstacle1, corner expansion, obstacle2, obstacle3. Publish each only at its local checkpoint; same geometry across methods. All methods paused at checkpoint before event selection. Obstacles chosen without solving candidates: never visited by ANY method, on ALL remaining old coverage plans, some pending task after first hit for each, all remaining tasks/base reachable. Prefer newly published area then minimum total distance from current positions, lexical tie-break. Shapes:1cell, horizontal2(vertical2 fallback), L3; singleton fallback only if larger fixed templates have no qualified placement. Stop world if no placement. No outcome-conditioned retries. Obstacles may be ahead not immediately next to every current position.',
 limitations='Common executed-step checkpoints and common-coordinate events; no planning-wait flight model; one seed. No general ranking across differing completed/deferred sets. Time includes only calls actually made, not archived preparation. Synthetic mixed maps, frozen historical algorithms.')
 write(O/'protocol.json',protocol);ledger=[];worlds=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 def call(cid,method,s,marker,stage):
  for f,v in sources.items():assert sha(f)==v,f
  ident=cid+'__'+method+'__'+str(stage);ip=O/'inputs'/(ident+'.json');jp=O/'jobs'/(ident+'.json');out=O/'results'/(ident+'.json');write(ip,s)
  job=dict(id=ident,run_id=ident,case_id=cid,method=method,input=str(ip.resolve()),input_sha256=sha(ip),marker=marker,budget=20,seed=20261020);write(jp,job);e=dict(id=ident,status='started');ledger.append(e);write(O/'call_ledger.json',ledger)
  cmd=[sys.executable,'-B','-X','utf8',str(H/'run_front_block.py'),'worker',str(jp),str(out)] if method in ['LOCAL_P2','ORIENT4'] else [sys.executable,'-B','-X','utf8',str(OLD/'worker.py'),str(jp),str(out)]
  cached=PREV/'results'/(ident+'.json')
  if cached.exists() and read(PREV/'inputs'/(ident+'.json'))==read(ip):
   out.write_bytes(cached.read_bytes());e.update(returncode=0,reused=True,cached_sha256=sha(cached))
  else:
   with (O/'logs'/(ident+'.log')).open('wb') as log:p=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   e.update(returncode=p.returncode,reused=False);write(O/'call_ledger.json',ledger);assert p.returncode==0,ident
  d=read(out);x=d.get('result',d);valid(s,x['raw']['route']);e.update(status='valid',seconds=x['entry_seconds'],timely=x['entry_seconds']<=20.010);write(O/'call_ledger.json',ledger)
  print(ident,len(x['raw']['route'])-1,flush=True)
  return dict(plan=x['raw']['route'],seconds=x['entry_seconds'],source=str(out.resolve()),sha256=sha(out),timely=e['timely'],raw=x['raw'])
 def finish(world,agents):
  for a in agents.values():
   a['route']+=a['plan'][1:];a['covered']=sorted(pts(a['covered'])|pts(a['plan'])&pts(world['published']));a['steps']=len(a['route'])-1;a['deferred']=sorted(pts(world['published'])-pts(world['free'])-pts(a['covered']));a.pop('plan',None)
  world['sessions']=list(agents.values());world['status']='complete';worlds.append(world);write(O/'worlds.json',worlds)
 # Reuse prior medium single event; new small/large single events derived from their saved common histories.
 prior=read(H/'前方未飞覆盖路段受阻展示_v0.1_20261024/results.json');c=prior['protocol']['cases'][0];worlds.append(dict(kind='reuse_single',size='medium',source=str((H/'前方未飞覆盖路段受阻展示_v0.1_20261024/results.json').resolve()),source_sha256=sha(H/'前方未飞覆盖路段受阻展示_v0.1_20261024/results.json'),case=c['id'],status='complete'))
 prep=R/'PPCPP_LAST新开发地图验证_v0.1_20261020'
 for size in ['small','large']:
  name=size+'_I';pr=read(prep/'prep/results'/(name+'.json'));ini=read(pr['job']['input']);wit=read(prep/'witnesses'/(name+'_obstacle_p30.json'));prefix=wit['history'];P=pts(ini['targets']);F=pts(ini['free']);seen=pts(prefix);old=pr['raw']['route'];block=None
  for i,q0 in enumerate(old[len(prefix):],len(prefix)):
   q=tuple(q0)
   if q in seen or q not in P or not(pts(old[i+1:])&P-seen-{q}):continue
   if (P-{q})|{tuple(ini['base'])}<=reachable(F-{q},prefix[-1]):block=[q];break
  assert block
  snap=dict(ini,name=name+'_front',free=sorted(F-pts(block)),targets=sorted(P-pts(block)),covered=sorted(P&seen),current=prefix[-1],previous=prefix[-2],old_route=old[len(prefix)-1:],deferred_targets=block,distance_budget=ini['distance_budget']-len(prefix)+1)
  world=dict(id=name+'_single',kind='single',size=size,initial=ini,free=snap['free'],published=ini['published_targets'],events=[dict(name='前方未飞覆盖格受阻',remove=block)],sessions=[])
  agents={}
  for m in METHODS:
   r=call(world['id'],m,snap,block,0);agents[m]=dict(method=m,route=list(prefix),covered=snap['covered'],plan=r['plan'],events=[dict(step=len(prefix)-1,name=world['events'][0]['name'])],phases=[dict(start_step=0,plan=old,free=ini['free'],published=ini['published_targets'],seconds=0),dict(start_step=len(prefix)-1,free=snap['free'],published=ini['published_targets'],**r)])
  finish(world,agents)
 # New synthetic mixed maps, fixed dimensions/expansions, checkpoint-dependent obstruction selected before branch calls.
 for cfg in configs:
  size=cfg['size'];n=cfg['n'];hh=cfg['h'];width=cfg['width'];leg=cfg['leg'];cid=size+'_mixed';P0={(x,y) for x in range(n) for y in range(hh)};F={(x,y) for x in range(-1,n) for y in range(hh)};P=set(P0);base=[-1,0]
  ini=dict(name=cid,free=sorted(F),targets=sorted(P),published_targets=sorted(P),covered=[],current=base,base=base,previous=None,predator=[-2,0],initial_targets=sorted(P),old_route=[],deferred_targets=[],distance_budget=1000000)
  first=call(cid,'PPCPP',ini,[],'prepare');agents={m:dict(method=m,route=[base],covered=[],plan=first['plan'],events=[],phases=[dict(start_step=0,free=sorted(F),published=sorted(P),**first)]) for m in METHODS}
  world=dict(id=cid,kind='mixed',size=size,initial=ini,events=[],preparation_seconds=first['seconds'],status='running');stopped=False
  common_cut=next(i for i in range(len(first['plan'])) if len(pts(first['plan'][:i+1])&P0)>=math.ceil(len(P0)*.20))
  for event_index,fraction in enumerate([.20,.30,.40,.50,.60]):
   threshold=math.ceil(len(P0)*fraction)
   for a in agents.values():
    done=pts(a['covered']);cut=None
    for i,q0 in enumerate(a['plan']):
     q=tuple(q0)
     if q in P:done.add(q)
     if i:a['route'].append(q0)
     if len(a['route'])-1>=common_cut+4*event_index:cut=i;break
    if cut is None:stopped=True;world['reason']='initial-progress checkpoint unreachable';break
    a['covered']=sorted(done);a['plan']=a['plan'][cut:]
   if stopped:break
   priorP=set(P);marker=[];e=dict(trigger_step=common_cut+4*event_index)
   if event_index in [0,2]:
    add={(x,y) for x in range(n,n+width) for y in (range(hh) if event_index==0 else range(hh,hh+leg))};F|=add;P|=add;marker=sorted(add-priorP);e.update(name='直线扩展' if event_index==0 else '拐角扩展',add_free=sorted(add),add_targets=marker,remove=[])
   else:
    visited=set().union(*(pts(a['route']) for a in agents.values()));eligible=(P&F)-visited
    for a in agents.values():eligible&=pts(a['plan'])
    shapes=([[(0,0)]] if event_index==1 else [[(0,0),(1,0)],[(0,0),(0,1)],[(0,0)]] if event_index==3 else [[(0,0),(1,0),(1,1)],[(0,0),(1,0),(0,1)],[(0,0),(0,1),(-1,1)],[(0,0)]])
    choices=[]
    for shape in shapes:
     for x,y in sorted(eligible):
      B={(x+dx,y+dy) for dx,dy in shape}
      if not B<=eligible or len(P0-B)<math.ceil(len(P0)*.20):continue
      ok=True
      for a in agents.values():
       plan=list(map(tuple,a['plan']));idx=next((i for i,q in enumerate(plan) if q in B),None);pending=P-pts(a['covered'])-B
       if idx is None or not pts(plan[idx+1:])&pending or not (((P&F)-B)|{tuple(base)})<=reachable(F-B,a['route'][-1]):ok=False;break
      if ok:choices.append((len(B&P0),sum(min(abs(x-q[0])+abs(y-q[1]) for q in B) for x,y in [a['route'][-1] for a in agents.values()]),sorted(B)))
     if choices:break
    if not choices:stopped=True;world['reason']='No joint unvisited coverage-blocking placement under fixed templates';break
    marker=min(choices)[2];F-=pts(marker);e.update(name='障碍'+str((event_index+1)//2),add_free=[],add_targets=[],remove=marker,qualification={m:dict(unvisited=not pts(marker)&pts(a['route']),old_route_first_hit=next(i for i,q in enumerate(a['plan']) if tuple(q) in pts(marker)),current=a['route'][-1]) for m,a in agents.items()})
   world['events'].append(e);write(O/(cid+'_event'+str(event_index)+'_precall.json'),dict(event=e,states={m:dict(current=a['route'][-1],actual_route=a['route'],covered=a['covered'],old_route=a['plan']) for m,a in agents.items()}))
   for m,a in agents.items():
    snap=dict(ini,name=cid+'_'+str(event_index),free=sorted(F),targets=sorted(P&F),published_targets=sorted(P),covered=a['covered'],initial_targets=sorted(priorP),current=a['route'][-1],previous=a['route'][-2],old_route=a['plan'],deferred_targets=sorted(P-F-pts(a['covered'])),distance_budget=1000000-len(a['route'])+1)
    r=call(cid,m,snap,marker,event_index);a['events'].append(dict(step=len(a['route'])-1,name=e['name']));a['phases'].append(dict(start_step=len(a['route'])-1,free=sorted(F),published=sorted(P),**r));a['plan']=r['plan']
  world.update(free=sorted(F),published=sorted(P))
  if stopped:world.update(status='qualification_stop',sessions=list(agents.values()));worlds.append(world);write(O/'worlds.json',worlds);continue
  finish(world,agents)
 assert len(ledger)<=139
 write(O/'results.json',dict(protocol=protocol,worlds=worlds,entries=len(ledger),new_entries=sum(not e.get('reused',False) for e in ledger),reused_entries=sum(e.get('reused',False) for e in ledger),predecessor_attempts=len(read(PREV/'call_ledger.json'))))
 print('FINISHED',len(ledger),[(w.get('id',w.get('case')),w['status']) for w in worlds],flush=True)
if __name__=='__main__':main()
