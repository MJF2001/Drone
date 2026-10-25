from pathlib import Path
import json,math,hashlib,sys,os,subprocess,collections,traceback
H=Path(__file__).resolve().parent;R=H.parent;O=H/'直达从零起飞真实障碍展示_v0.1_20261024'
def read(p):return json.loads(Path(p).read_text('utf-8'))
def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pts(a):return set(map(tuple,a))
def box(a,b,q,r=.5):
 lo,hi=0.,1.
 for k in (0,1):
  d=b[k]-a[k]
  if d==0:
   if not q[k]-r<a[k]<q[k]+r:return False
  else:
   x,y=sorted(((q[k]-r-a[k])/d,(q[k]+r-a[k])/d));lo=max(lo,x);hi=min(hi,y)
 return lo<hi

def reach(F,s):
 seen={tuple(s)};todo=collections.deque(seen)
 while todo:
  x,y=todo.popleft()
  for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
   if p in F and p not in seen:seen.add(p);todo.append(p)
 return seen

def cumulative(path):
 out=[0.]
 for a,b in zip(path,path[1:]):out.append(out[-1]+math.dist(a,b))
 return out

def credits(z):
 cum=cumulative(z['path']);out=[]
 for e in z['events']:
  if not e.get('new'):continue
  if e['kind']=='collect_here':s=0
  else:
   k=e['edge'];q=e['evidence']['witness']['t'];s=cum[k]+q['n']/q['d']*(cum[k+1]-cum[k])
  out.append([e['cell'],s])
 return out

def main():
 assert not O.exists();O.mkdir();[(O/k).mkdir() for k in ['inputs','outputs','jobs','logs']]
 guards=read(R/'中心区计时插桩影响核查_v0.1_20261022/source_guards.json');guards[str(H/'direct_flight_worker.py')]=sha(H/'direct_flight_worker.py');guards[str(Path(__file__).resolve())]=sha(__file__)
 dump(O/'source_guards.json',guards);dump(O/'active_freeze.json',{})
 dump(O/'protocol.json',dict(sizes=['small','medium','large'],geometry='archived initial I maps, all targets initially uninspected, own plans from base',seed=20261020,max_core=18,max_post=18,profile='OFF',worker_change='only initial non-task base may have empty H; core/post/audit unchanged',checkpoint='Each view stops at first saved vertex reached by an axial edge after >=30% actual service credit, with pending tasks; no additional flight forced. Last one-unit incoming direction is real traversed direction. Progress-based per-session event, NOT same wall time.',obstacle='Same cell for all four: never physically traversed in any prefix; open cell intersects all four old unexecuted routes, with remaining service after intersection, remaining task/base reachable. Lexicographic first qualified cell, selected before replanning without outcomes. Stop world if unavailable.',comparison='Complete flight and cumulative planning time; initial raw/post share core. After divergent histories each view gets own core+post, unused counterfactual view not charged as flight. Raw branch time excludes diagnostic unused post. Native20s,post18soft/20total,4096candidates,parent150s. Preserve deadlines and failure; no result-driven retries.'))
 assert box((0,0),(2,2),(1,1)) and not box((0,0),(2,0),(1,1)) and box((0,0),(2,0),(1,0))
 assert reach({(0,0),(1,0),(3,0)},(0,0))=={(0,0),(1,0)}
 dump(O/'prechecks.json',dict(passed=True,cases=4,core_calls=0))
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');ledger=[];worlds=[]
 def call(s,method,ident):
  assert len(ledger)<18
  dump(O/'inputs'/(ident+'.json'),s);job=dict(id=ident,case=s['name'],seed=20261020,method=method,config='OFF',input='inputs/'+ident+'.json');dump(O/'jobs'/(ident+'.json'),job);ledger.append(dict(id=ident,status='started'));dump(O/'ledger.json',ledger)
  with (O/'logs'/(ident+'.txt')).open('wb') as log:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'direct_flight_worker.py'),str(O),str(O/'jobs'/(ident+'.json'))],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150)
  d=read(O/'outputs'/(ident+'.json'));ledger[-1].update(status='passed' if p.returncode==0 and d['passed'] else 'failed',core=d['entry_ledger']);dump(O/'ledger.json',ledger);assert p.returncode==0 and d['passed'],(ident,d.get('failure'))
  print(ident,'passed',flush=True);return d
 try:
  for size in ['small','medium','large']:
   ini=read(R/'PPCPP_LAST新开发地图验证_v0.1_20261020/prep/inputs'/(size+'_I.json'));assert not ini['covered'] and ini['current']==ini['base'];P=pts(ini['published_targets']);F=pts(ini['free']);initial={m:call(ini,m,size+'_'+m+'_start') for m in ['PPCPP','P2_MULTI']};agents=[]
   for m,vs in [('PPCPP',['A','B']),('P2_MULTI',['C0','C'])]:
    for v in vs:
     d=initial[m];z=d['views'][v];path=z['path'];cum=cumulative(path);cs=credits(z);cut=None
     for k in range(1,len(path)-1):
      a,b=path[k-1:k+1];hh={tuple(q) for q,t in cs if t<=cum[k]+1e-9}
      if (a[0]==b[0] or a[1]==b[1]) and math.dist(a,b)>=1 and math.ceil(len(P)*.3)<=len(hh)<len(P) and tuple(b) in hh:cut=k;break
     assert cut is not None,(size,v,'no checkpoint')
     agents.append(dict(view=v,method=m,initial=d['job']['id'],path=path[:cut+1],old=path[cut:],H=sorted(hh),cut_distance=cum[cut],initial_credits=[[q,t] for q,t in cs if t<=cum[cut]+1e-9],seconds=d['timing']['raw_common_end_to_end' if v in ['A','C0'] else 'combined_end_to_end']))
   choices=[]
   for q in sorted(P):
    good=True
    for a in agents:
     if any(box(x,y,q) for x,y in zip(a['path'],a['path'][1:])):good=False;break
     hit=next((k for k,(x,y) in enumerate(zip(a['old'],a['old'][1:])) if box(x,y,q)),None)
     if hit is None or not ((pts(a['old'][hit+1:])&P)-pts(a['H'])-{q}) or not (P-{q}|{tuple(ini['base'])})<=reach(F-{q},a['path'][-1]):good=False;break
    if good:choices.append(q)
   world=dict(size=size,name=size+'_I_full_obstacle',initial=ini,agents=agents)
   if not choices:
    world.update(status='not_applicable',reason='no common unvisited old coverage route blocker');worlds.append(world);dump(O/'worlds.json',worlds);continue
   block=choices[0];world['obstacle']=block;dump(O/(size+'_pre_replan.json'),world)
   for a in agents:
    cur=a['path'][-1];prev0=a['path'][-2];previous=[cur[j]-(1 if cur[j]>prev0[j] else -1 if cur[j]<prev0[j] else 0) for j in (0,1)]
    snap=dict(ini,name=world['name']+'_'+a['view'],free=sorted(F-{block}),targets=sorted(P-{block}),covered=a['H'],current=cur,previous=previous,old_route=a['old'],deferred_targets=[block],distance_budget=ini['distance_budget']-a['cut_distance'])
    d=call(snap,a['method'],size+'_'+a['view']+'_obstacle');z=d['views'][a['view']];a['response']=d['job']['id'];a['full_path']=a['path']+z['path'][1:];a['credits']=a['initial_credits']+[[q,t+a['cut_distance']] for q,t in credits(z)];a['length']=cumulative(a['full_path'])[-1];a['seconds']+=d['timing']['raw_common_end_to_end' if a['view'] in ['A','C0'] else 'combined_end_to_end'];a['return_length']=a['length']-max(t for q,t in a['credits']);a['inspection_length']=a['length']-a['return_length'];a['final_H']=z['metrics']['final_H'];assert pts(a['final_H'])==P-{block}
   world['status']='complete';worlds.append(world);dump(O/'worlds.json',worlds)
  dump(O/'status.json',dict(completed=True,core_calls=len(ledger),worlds=[dict(size=w['size'],status=w['status']) for w in worlds]))
 except BaseException as e:
  dump(O/'failure.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
