"""One predeclared mixed-event demonstration, original frozen versions; no retries."""
from pathlib import Path
import json,os,subprocess,sys,time,hashlib,collections
from run_continuous_demo_v03 import read,write,digest,points,audit,turns,check_sources
H=Path(__file__).resolve().parent;ROOT=H.parent;OLD=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';OUT=H/'六算法综合连续事件演示_v0.1'
METHODS=['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP'];SEED=20261018

def main():
 assert not OUT.exists(),'Do not overwrite or rerun existing experiment'
 source=read(OLD/'protocol.json');check_sources(source)
 old=read(H/'七算法从零起飞事件演示_v0.3/results.json')['worlds'][0]
 F=points(old['initial']['free']);P=points(old['initial']['published']);F0=set(F);P0=set(P)
 events=[dict(name='直线扩展',threshold=12,add_targets=sorted(points(old['after']['published'])-P),add_free=[],remove=[]),
 dict(name='障碍一：单格',threshold=21,add_targets=[],add_free=[],remove=[[14,1]]),
 dict(name='拐角扩展',threshold=30,add_targets=[[x,y] for x in range(12,17) for y in range(5,10)],add_free=[[x,y] for x in range(11,18) for y in range(5,11)],remove=[]),
 dict(name='障碍二：横向两格',threshold=39,add_targets=[],add_free=[],remove=[[15,3],[16,3]]),
 dict(name='障碍三：L形三格',threshold=48,add_targets=[],add_free=[],remove=[[13,6],[14,6],[14,7]])]
 # Geometry-only preflight, no routes or planner results used for event selection.
 stages=[]
 for e in events:
  P|=points(e['add_targets']);F|=points(e['add_free']);F-=points(e['remove'])
  reached={tuple(old['initial']['base'])};q=collections.deque(reached)
  while q:
   x,y=q.popleft()
   for z in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
    if z in F and z not in reached:reached.add(z);q.append(z)
  assert P&F<=reached and tuple(old['initial']['base']) in F
  stages.append(dict(free=sorted(F),published=sorted(P)))
 OUT.mkdir();[(OUT/k).mkdir() for k in ['inputs','jobs','results','logs']]
 protocol=dict(world='mixed_small_original_core4',initial=old['initial'],predator=old['predator'],events=events,stages=stages,methods=METHODS,seed=SEED,
  trigger='Unique actually collected INITIAL tasks / fixed initial 60 tasks:20%,35%,50%,65%,80%. New tasks never change trigger denominator; each method has independent history.',
  event_policy='Fixed coordinates and shapes, cumulative persistent events; stop session if current/base becomes blocked or returned plan invalid; no relocating event, no alternate planner, no retry.',
  model='Original frozen versions; unit cardinal moves; cell-center collection; no any-angle or central collection zones.',max_entries=36,budget_seconds=20,timely_tolerance=.010,watchdog_seconds=90,
  sources=source['sources'],versions=source['versions'],worker_sha256=digest(OLD/'worker.py'),runner_sha256=digest(Path(__file__)),preflight='All cumulative stages connected to base; geometry-only reachability checked before planner calls',
  comparison='Report completed and deferred sets; distance ranking only for identical physical completed/deferred sets; single small synthetic mixed world not general evidence')
 write(OUT/'protocol.json',protocol)
 env=os.environ.copy()
 for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='1'
 ledger=[];sessions=[]
 for method in METHODS:
  F=set(F0);P=set(P0);Hdone=set();route=[old['initial']['base']];old_route=[];phases=[];status='running';event_index=0
  session=dict(method=method,status=status,route=route,phases=phases,events=[],seed=SEED)
  for phase in range(6):
   check_sources(source)
   ident=method+'__phase'+str(phase)
   snapshot=dict(name=ident,free=sorted(F),targets=sorted(P&F),published_targets=sorted(P),covered=sorted(Hdone),deferred_targets=sorted(P-F-Hdone),
    current=route[-1],base=old['initial']['base'],previous=route[-2] if len(route)>1 else None,old_route=old_route,initial_targets=sorted(P0),predator=old['predator'],distance_budget=old['initial']['distance_budget']-(len(route)-1))
   ip=OUT/'inputs'/(ident+'.json');jp=OUT/'jobs'/(ident+'.json');dest=OUT/'results'/(ident+'.json');write(ip,snapshot)
   job=dict(run_id=ident,case_id='mixed_small_original_core4',input=str(ip),input_sha256=digest(ip),method=method,budget=20,seed=SEED);write(jp,job)
   entry=dict(id=ident,method=method,phase=phase,status='started');ledger.append(entry);write(OUT/'call_ledger.json',ledger)
   try:
    with (OUT/'logs'/(ident+'.log')).open('wb') as log:r=subprocess.run([sys.executable,'-B','-X','utf8',str(OLD/'worker.py'),str(jp),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    assert r.returncode==0 and dest.exists(),ident
    result=read(dest);audit(snapshot,result['route']);entry.update(status='valid',seconds=result['entry_seconds'],timely=result['entry_seconds']<=20.010)
    plan=result['route'];start=len(route)-1;cut=len(plan)-1
    for j,pos in enumerate(plan):
     if tuple(pos) in P:Hdone.add(tuple(pos))
     if j:route.append(pos)
     if event_index<5 and len(Hdone&P0)>=events[event_index]['threshold']:
      cut=j;break
    phases.append(dict(index=phase,start_step=start,end_step=len(route)-1,plan=plan,seconds=result['entry_seconds'],result_id=ident,free=sorted(F),published=sorted(P),history_before=snapshot['covered']))
    if event_index==5:
     assert route[-1]==old['initial']['base'] and P&F<=Hdone
     status='complete';break
    if len(Hdone&P0)<events[event_index]['threshold']:
     status='trigger_not_reached';break
    e=events[event_index];F|=points(e['add_free']);P|=points(e['add_targets']);F-=points(e['remove']);old_route=plan[cut:]
    session['events'].append(dict(index=event_index,name=e['name'],step=len(route)-1,initial_collected=len(Hdone&P0),threshold=e['threshold'],current=route[-1],history=sorted(Hdone)))
    event_index+=1
    if tuple(route[-1]) not in F or tuple(old['initial']['base']) not in F:
     status='occupied_event_stop';break
   except Exception as ex:
    entry.update(status='failed',error=repr(ex));status='technical_stop';write(OUT/'call_ledger.json',ledger);raise
   finally:write(OUT/'call_ledger.json',ledger)
   print(ident,entry['status'],len(route)-1,flush=True)
  session.update(status=status,steps=len(route)-1,completed=sorted(Hdone),deferred=sorted(P-F-Hdone),total_seconds=sum(p['seconds'] for p in phases),timely=all(p['seconds']<=20.010 for p in phases),**turns(route))
  sessions.append(session);write(OUT/'sessions.json',sessions)
 check_sources(source);assert len(ledger)<=36
 write(OUT/'results.json',dict(protocol=protocol,sessions=sessions,actual_entries=len(ledger),complete=sum(s['status']=='complete' for s in sessions)))
 print('DONE',len(ledger),[s['status'] for s in sessions],flush=True)
if __name__=='__main__':main()
