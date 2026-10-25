from pathlib import Path
import sys,os,subprocess,math,traceback
from run_direct_flight_v2 import read,dump,sha,pts,box,reach,cumulative,credits
H=Path(__file__).resolve().parent;R=H.parent;O=H/'直达ILZ紧邻三障碍展示_v0.1_20261024'
def nextcell(a,b):
 d=[b[k]-a[k] for k in (0,1)];m=max(map(abs,d));return tuple(a[k]+((1 if d[k]>0 else -1) if abs(d[k])==m else 0) for k in (0,1))
def main():
 assert not O.exists();O.mkdir();[(O/d).mkdir() for d in ['inputs','outputs','jobs','logs']]
 guards=read(R/'中心区计时插桩影响核查_v0.1_20261022/source_guards.json');guards[str(H/'direct_flight_worker_v2.py')]=sha(H/'direct_flight_worker_v2.py');guards[str(Path(__file__).resolve())]=sha(__file__)
 dump(O/'source_guards.json',guards);dump(O/'active_freeze.json',{})
 dump(O/'protocol.json',dict(layouts=['I','L','Z'],sizes=['small','medium','large'],max_core=126,max_post=126,seed=20261020,thresholds=[.2,.5,.75],coverage='actual inspected / current inspectable (deferred removed)',start='minimum target grid center as base; initially empty history; collect start at distance zero',trigger='Earliest saved vertex after threshold, incoming axial unit direction exists (or initial base). First open grid cell entered by next segment must be adjacent (Chebyshev1), never traversed earlier, pending. No distant candidate; tie at corner enters diagonal cell. Removal blocks next segment and leaves tasks/base reachable with at least one other pending task. If not eligible, execute old route to next real vertex, no forced extra leg. Stop session if unavailable.',limits='Original integer-grid/axial incoming interface only; not noncenter detection. own-progress event not simultaneous time, obstacle coordinates may differ. Same policy not same world paired causal test. Fixed archived maps, no outcome selection; native20/post18soft20total,4096. All actual calls include unused diagnostic post on raw branches.'))
 assert nextcell((0,0),(4,2))==(1,0) and nextcell((0,0),(2,4))==(0,1) and nextcell((0,0),(2,2))==(1,1) and nextcell((0,0),(-2,0))==(-1,0)
 dump(O/'prechecks.json',dict(passed=True,cases=4))
 ledger=[];worlds=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 def call(s,m,ident):
  assert len(ledger)<126;dump(O/'inputs'/(ident+'.json'),s);j=dict(id=ident,case=s['name'],seed=20261020,method=m,config='OFF',input='inputs/'+ident+'.json');dump(O/'jobs'/(ident+'.json'),j);ledger.append(dict(id=ident,status='started'));dump(O/'ledger.json',ledger)
  with (O/'logs'/(ident+'.txt')).open('wb') as log:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'direct_flight_worker_v2.py'),str(O),str(O/'jobs'/(ident+'.json'))],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150)
  d=read(O/'outputs'/(ident+'.json'));ledger[-1].update(status='passed' if d['passed'] and p.returncode==0 else 'failed',core=d['entry_ledger']);dump(O/'ledger.json',ledger);assert d['passed'] and p.returncode==0,(ident,d.get('failure'));print(ident,'passed',flush=True);return d
 def sec(d,v):return d['timing']['raw_common_end_to_end' if v in ('A','C0') else 'combined_end_to_end']
 try:
  for size in ['small','medium','large']:
   for family in ['I','L','Z']:
    cid=size+'_'+family;ini=read(R/'PPCPP_LAST新开发地图验证_v0.1_20261020/prep/inputs'/(cid+'.json'));ini.update(base=list(min(pts(ini['targets']))),covered=[],previous=None);ini['current']=ini['base'];ini['old_route']=[ini['base']];P=pts(ini['published_targets']);init={m:call(ini,m,cid+'_'+m+'_start') for m in ['PPCPP','P2_MULTI']};world=dict(name=cid+'_three_obstacles',size=size,family=family,initial=ini,agents=[])
    for m,vs in [('PPCPP',['A','B']),('P2_MULTI',['C0','C'])]:
     for v in vs:
      d=init[m];z=d['views'][v];F=pts(ini['free']);Hc=set();route=[ini['base']];credit=[];offset=0.;seconds=sec(d,v);phases=[dict(start_distance=0.,plan=z['path'],source=d['job']['id'],free=sorted(F))];events=[];status='complete'
      for j,threshold in enumerate([.2,.5,.75]):
       path=z['path'];cum=cumulative(path);cs=credits(z);cut=None;reached=None
       for k in range(len(path)-1):
        if k:route.append(path[k])
        Hnow=Hc|{tuple(q) for q,t in cs if t<=cum[k]+1e-9};ratio=len(Hnow&F)/len(P&F)
        if ratio<threshold-1e-12:continue
        if reached is None:reached=offset+cum[k]
        cur=path[k]
        if len(route)>1:
         prev0=route[-2]
         if not (prev0[0]==cur[0] or prev0[1]==cur[1]) or math.dist(prev0,cur)<1:continue
        b=nextcell(cur,path[k+1]);pending=(P&F)-Hnow
        if b not in pending or len(pending-{b})==0 or not box(cur,path[k+1],b):continue
        if any(box(a,c,b) for a,c in zip(route,route[1:])):continue
        if not ((P&F)-{b}|{tuple(ini['base'])})<=reach(F-{b},cur):continue
        cut=k;break
       if cut is None:
        status='not_applicable';route=route[:len(route)-(len(path)-2)] if False else route;break
       newcredits=[[q,t+offset] for q,t in cs if t<=cum[cut]+1e-9];credit+=newcredits;Hc=Hnow;offset+=cum[cut];F.remove(b)
       cur=route[-1];prev0=route[-2] if len(route)>1 else None;previous=[cur[k]-(1 if cur[k]>prev0[k] else -1 if cur[k]<prev0[k] else 0) for k in (0,1)] if prev0 else None
       event=dict(number=j+1,threshold=threshold,ratio=ratio,distance=offset,threshold_distance=reached,wait_distance=offset-reached,block=b,current=cur,next_endpoint=path[cut+1],old=path[cut:],prefix_count=len(route),history=sorted(Hc));events.append(event);dump(O/(cid+'_'+v+'_event'+str(j)+'_precall.json'),event)
       snap=dict(ini,name=cid+'_'+v+'_'+str(j),free=sorted(F),targets=sorted(P&F),covered=sorted(Hc),deferred_targets=sorted(P-F-Hc),current=cur,previous=previous,old_route=path[cut:],distance_budget=1000000-offset)
       d=call(snap,m,cid+'_'+v+'_'+str(j));z=d['views'][v];seconds+=sec(d,v);phases.append(dict(start_distance=offset,plan=z['path'],source=d['job']['id'],free=sorted(F)))
      if status=='complete':
       route+=z['path'][1:];credit += [[q,t+offset] for q,t in credits(z)];total=cumulative(route)[-1];final=z['metrics']['final_H'];assert pts(final)==P&F
      else:total=cumulative(route)[-1];final=sorted(Hc)
      agent=dict(view=v,method=m,status=status,full_path=route,credits=credit,seconds=seconds,length=total,final_H=final,events=events,phases=phases,deferred=sorted(P-F),return_length=total-max((t for q,t in credit),default=0));agent['inspection_length']=total-agent['return_length'];world['agents'].append(agent);dump(O/'partial.json',dict(worlds=worlds,current=world))
    world['status']='complete' if all(a['status']=='complete' for a in world['agents']) else 'partial';worlds.append(world);dump(O/'worlds.json',worlds)
  dump(O/'status.json',dict(completed=True,entries=len(ledger)))
 except BaseException as e:dump(O/'failure.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
