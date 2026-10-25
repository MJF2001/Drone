import os,sys,json,time,hashlib,subprocess,random,math,collections,importlib.util,csv,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sys.path.insert(0,str(P))
import runtime,p2_adapter,candidate
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=load('stress_metric',M/'metrics.py').metrics;cross=load('stress_cross',M/'crosscheck.py').calculate
def adj(p):
 x,y=p;return ((x+1,y),(x,y+1),(x-1,y),(x,y-1))
def graph(f,base):
 d={base:0};q=collections.deque([base])
 while q:
  p=q.popleft()
  for n in adj(p):
   if n in f and n not in d:d[n]=d[p]+1;q.append(n)
 assert len(d)==len(f),'disconnected fixture'
 # Independent bridge detection by DFS low-link; graph-only, not a planner.
 sys.setrecursionlimit(10000);tin={};low={};bridges=[]
 def visit(v,parent=None):
  tin[v]=low[v]=len(tin)
  for n in adj(v):
   if n not in f or n==parent:continue
   if n in tin:low[v]=min(low[v],tin[n])
   else:
    visit(n,v);low[v]=min(low[v],low[n])
    if low[n]>tin[v]:bridges.append([v,n])
 visit(base)
 return dict(free=len(f),max_base_distance=max(d.values()),degree_counts=dict(collections.Counter(sum(n in f for n in adj(p)) for p in f)),bridges=len(bridges))
def imports():return {str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
def seal(name,parent):
 files=read(parent)
 if 'files' in files:files=files['files']
 for p,h in files.items():assert sha(p)==h,p
 paths=set(files)|imports()|{str(p.resolve()) for p in H.rglob('*') if p.is_file() and p.name not in ('actual_order.jsonl',)}
 save(H/name,{p:sha(p) for p in sorted(paths)})
def worker(jp,out):
 j=read(jp);ss=read(H/j['seal']);hs={}
 for p in imports():
  if Path(p).is_relative_to(R):assert p in ss and sha(p)==ss[p],p;hs[p]=sha(p)
 inp=H/j['input'];assert sha(inp)==ss[str(inp.resolve())];payload=inp.read_bytes()
 x=runtime.run_payload(payload,'PPCPP',20,j['seed']) if j['method']=='PPCPP' else p2_adapter.run_payload(payload,20,j['seed'])
 save(out,dict(job=j,result=x,imports=hs,input_sha256=sha(inp)))
def execute(order,folder):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 for i,j in enumerate(order):
  out=H/folder/(j['id']+'.json');assert not out.exists()
  try:
   p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(H/'jobs'/(j['id']+'.json')),str(out)],env=env,timeout=90,capture_output=True)
   code=p.returncode;(H/'logs'/(j['id']+'.txt')).write_bytes(p.stdout+p.stderr)
  except subprocess.TimeoutExpired as e:code='watchdog';(H/'logs'/(j['id']+'.txt')).write_text(str(e),encoding='utf8')
  with (H/'actual_order.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(id=j['id'],phase=folder,code=code))+'\n')
  if code!=0:raise RuntimeError(('technical stop',j['id'],code))
  print(folder,i+1,'/',len(order),flush=True)
def setup():
 for d in ('inputs','jobs','outputs','prep','logs','figures'):(H/d).mkdir()
 order=[]
 for w,h in ((21,15),(31,21)):
  f={(x,y) for x in range(w) for y in range(h)};name=f'base_{w}_{h}'
  c=dict(name=name,free=sorted(f),targets=sorted(f),covered=[],published_targets=sorted(f),deferred_targets=[],initial_targets=sorted(f),current=[0,0],base=[0,0],previous=None,predator=[-1,0],old_route=[],distance_budget=10*w*h)
  save(H/'inputs'/(name+'.json'),c);j=dict(id=name,input='inputs/'+name+'.json',method='PPCPP',seed=20261021,seal='prep_seal.json');save(H/'jobs'/(name+'.json'),j);order.append(j)
 save(H/'prep_order.json',order);seal('prep_seal.json',R/'PPCPP四方向共同预算正式比较_v0.1_20261020/seal.json')
def layouts(w,h):
 full={(x,y) for x in range(w) for y in range(h)}
 walls={(x,y) for i,x in enumerate(range(2,w-1,2)) for y in range(h) if y!=(1 if i%2==0 else h-2)}
 rooms={(x,y) for x,y in full if (x>0 and x%4==0 and y%4!=1) or (y>0 and y%4==0 and x%4!=1)}
 rng=random.Random(20261021+w);start=(1,1);f={start};seen={start};stack=[start]
 while stack:
  x,y=stack[-1];ns=[(x+dx,y+dy) for dx,dy in ((2,0),(0,2),(-2,0),(0,-2)) if 0<x+dx<w-1 and 0<y+dy<h-1 and (x+dx,y+dy) not in seen]
  if not ns:stack.pop();continue
  n=rng.choice(ns);seen.add(n);f.add(n);f.add(((x+n[0])//2,(y+n[1])//2));stack.append(n)
 f|={(0,0),(0,1)}
 return dict(control=full,serpentine=full-walls,rooms=full-rooms,maze=f)
def build():
 states=[]
 for j in read(H/'prep_order.json'):
  c=read(H/j['input']);x=read(H/'prep'/(j['id']+'.json'))['result'];assert x['eligible'];route=list(map(tuple,x['raw']['route']));assert metric(c,route)==cross(c,route)
  w=max(p[0] for p in route)+1;h=max(p[1] for p in route)+1;full=set(map(tuple,c['free']))
  for progress in (10,30):
   hist=set();idx=None
   for i,p in enumerate(route):
    hist.add(p)
    if len(hist)>=math.ceil(w*h*progress/100):idx=i;break
   cur=route[idx]
   for kind,f0 in layouts(w,h).items():
    f=set(f0);added=[]
    if cur not in f:
     dest=min(f,key=lambda p:(abs(p[0]-cur[0])+abs(p[1]-cur[1]),p));p=cur;added.append(p);f.add(p)
     for axis in (0,1):
      while p[axis]!=dest[axis]:
       q=list(p);q[axis]+=1 if dest[axis]>p[axis] else -1;p=tuple(q);f.add(p);added.append(p)
    g=graph(f,(0,0));name=f'{w}x{h}_{kind}_p{progress}'
    cc=dict(c,name=name,free=sorted(f),targets=sorted(f),covered=sorted(hist),deferred_targets=sorted(full-f-hist),current=list(cur),previous=list(route[idx-1]) if idx else None,old_route=route[idx:])
    runtime.validate(cc);save(H/'inputs'/(name+'.json'),cc)
    states.append(dict(name=name,w=w,h=h,kind=kind,progress=progress,history_index=idx,prep=j['id'],connection_opened=added,obstacles=len(full-f),obstacle_fraction=len(full-f)/len(full),pending=len(f-hist-{cur}),deferred=len(full-f-hist),structure=g))
 assert len(states)==16;save(H/'states.json',states)
 order=[]
 for i,s in enumerate(states):
  for rep in range(3):
   methods=['PPCPP','P2_MULTI'];methods=methods if (i+rep)%2==0 else methods[::-1]
   for m in methods:
    j=dict(id=f'{s["name"]}__{rep}__{m}',case=s['name'],rep=rep,method=m,seed=20261020+rep,input='inputs/'+s['name']+'.json',seal='formal_seal.json');save(H/'jobs'/(j['id']+'.json'),j);order.append(j)
 save(H/'formal_order.json',order);seal('formal_seal.json',H/'prep_seal.json');print('STRUCTURE/PREPARATION PASS',len(order),flush=True)
def analysis():
 rows=[]
 for j in read(H/'formal_order.json'):
  x=read(H/'outputs'/(j['id']+'.json'))['result'];c=read(H/j['input']);r=x['raw'].get('route',[]);m=None
  if r:m=metric(c,r);assert m==cross(c,r) and m['complete_legal']
  rows.append(dict(**j,seconds=x['entry_seconds'],status=x['raw'].get('status'),valid=bool(m),timely=bool(m) and x['entry_seconds']<20,metrics=m))
 return rows
def analyze():
 rows=analysis();save(H/'analysis.json',rows)
 flat=[dict(**{k:v for k,v in r.items() if k!='metrics'},**(r['metrics'] or {})) for r in rows]
 fields=list(dict.fromkeys(k for r in flat for k in r))
 with (H/'完整调用指标.csv').open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)
 for m in ('PPCPP','P2_MULTI'):
  rr=[r for r in rows if r['method']==m];print(m,len(rr),sum(r['valid'] for r in rr),sum(r['timely'] for r in rr),statistics.mean(r['seconds'] for r in rr),flush=True)
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='worker':worker(sys.argv[2],sys.argv[3])
 elif mode=='setup':setup()
 elif mode=='prep':execute(read(H/'prep_order.json'),'prep')
 elif mode=='build':build()
 elif mode=='run':execute(read(H/'formal_order.json'),'outputs')
 elif mode=='analyze':analyze()
 elif mode=='verify':
  for p,h in read(H/'formal_seal.json').items():assert sha(p)==h,p
  for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
  assert analysis()==read(H/'analysis.json');print('PASS: source hashes, output manifest, full routes double metrics; no solver calls.')
