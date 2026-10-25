from pathlib import Path
import json,sys,hashlib,subprocess,os,collections
H=Path(__file__).resolve().parent;R=H.parent;O=H/'前方未飞覆盖路段受阻展示_v0.1_20261024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pts(a):return set(map(tuple,a))
def worker(jp,out):
 j=read(jp);assert sha(j['input'])==j['input_sha256'];c=read(j['input'])
 if j['method']=='LOCAL_P2':
  sys.path.insert(0,str(R/'PPCPP局部P2混合开发诊断_v0.1_20261020'));import entry
  x=entry.run(json.dumps(dict(state=c,marker=j['marker'])).encode(),'LOCAL_P2',20,j['seed'])
 else:
  sys.path.insert(0,str(R/'PPCPP四方向接口适配验收_v0.1_20261020'));import entry
  x=entry.run(json.dumps(c).encode(),'COMBO',20,j['seed'])
 write(out,dict(job=j,result=x,imports={str(Path(m.__file__).resolve()):sha(m.__file__) for m in sys.modules.values() if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(R)}))
def main():
 assert not O.exists();O.mkdir();[(O/k).mkdir() for k in ['inputs','results','jobs','logs']]
 prep=R/'PPCPP_LAST新开发地图验证_v0.1_20261020';cases=[]
 for family in ['I','L','Z']:
  base='medium_'+family;pr=read(prep/'prep/results'/(base+'.json'));initial=read(pr['job']['input']);w=read(prep/'witnesses'/(base+'_obstacle_p30.json'));prefix=w['history'];plan=pr['raw']['route'];assert prefix==plan[:w['cut']+1]
  F=pts(initial['free']);P=pts(initial['targets']);seen=pts(prefix);covered=P&seen;chosen=None
  for i,b in enumerate(plan[w['cut']+1:],start=w['cut']+1):
   q=tuple(b)
   if q in seen or q not in P or q==tuple(initial['base']):continue
   if not (pts(plan[i+1:])&P-seen-{q}):continue
   free=F-{q};reach={tuple(prefix[-1])};queue=collections.deque(reach)
   while queue:
    x,y=queue.popleft()
    for z in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
     if z in free and z not in reach:reach.add(z);queue.append(z)
   if (P-{q})|{tuple(initial['base'])}<=reach:chosen=(q,i);break
  assert chosen is not None
  q,i=chosen;c=dict(initial,name=base+'_front_block',free=sorted(F-{q}),targets=sorted(P-{q}),covered=sorted(covered),current=prefix[-1],previous=prefix[-2],old_route=plan[w['cut']:],published_targets=sorted(P),deferred_targets=[q],distance_budget=initial['distance_budget']-len(prefix)+1)
  ip=O/'inputs'/(c['name']+'.json');write(ip,c)
  cases.append(dict(id=c['name'],initial=initial,snapshot=c,prefix=prefix,cut=len(prefix)-1,marker=[q],old_plan=plan,evidence=dict(unvisited=q not in seen,old_plan_hit_index=i,steps_ahead=i-w['cut'],uncollected_after_block=len(pts(plan[i+1:])&P-seen-{q}),all_remaining_reachable=True),input=str(ip.resolve()),input_sha256=sha(ip),prefix_source=str((prep/'prep/results'/(base+'.json')).resolve()),prefix_source_sha256=sha(prep/'prep/results'/(base+'.json'))))
 methods=['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP','LOCAL_P2','ORIENT4'];old=R/'七算法共同预算比较_v0.3_Cstar07_20261020';sources=read(old/'protocol.json')['sources'];sources={str((R/k).resolve()):v for k,v in sources.items()}
 for folder in ['PPCPP局部P2混合开发诊断_v0.1_20261020','PPCPP四方向接口适配验收_v0.1_20261020']:
  seal=read(R/folder/'environment_seal.json')['files']
  for f,v in seal.items():
   if Path(f).is_relative_to(R) and Path(f).suffix=='.py':assert sha(f)==v;sources[f]=v
 sources[str((old/'worker.py').resolve())]=sha(old/'worker.py');sources[str(Path(__file__).resolve())]=sha(__file__)
 protocol=dict(cases=cases,methods=methods,seed=20261020,budget=20,max_entries=24,selection='I/L/Z medium original preparation prefixes p30; first future original-task cell never visited, with later uncollected task and full reachability after blocking; fixed before new solves.',comparison='Same actual prefix, stop position, history and one obstacle for all eight methods. Not independent initial planning. No any-angle/central-zone model.',sources=sources)
 write(O/'protocol.json',protocol);records=[];ledger=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 for c in cases:
  for method in methods:
   for f,v in sources.items():assert sha(f)==v,f
   ident=c['id']+'__'+method;j=dict(id=ident,run_id=ident,case_id=c['id'],method=method,input=c['input'],input_sha256=c['input_sha256'],budget=20,seed=20261020,marker=c['marker']);jp=O/'jobs'/(ident+'.json');out=O/'results'/(ident+'.json');write(jp,j);e=dict(id=ident,status='started');ledger.append(e);write(O/'call_ledger.json',ledger)
   cmd=[sys.executable,'-B','-X','utf8',str(__file__),'worker',str(jp),str(out)] if method in ['LOCAL_P2','ORIENT4'] else [sys.executable,'-B','-X','utf8',str(old/'worker.py'),str(jp),str(out)]
   with (O/'logs'/(ident+'.log')).open('wb') as log:p=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   e['returncode']=p.returncode;write(O/'call_ledger.json',ledger);assert p.returncode==0
   d=read(out);x=d.get('result',d);raw=x['raw'];r=raw['route'];s=c['snapshot'];assert r and r[0]==s['current'] and r[-1]==s['base'] and pts(r)<=pts(s['free']);assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(r,r[1:]));assert pts(s['targets'])<=pts(s['covered'])|pts(r);assert len(r)-1<=s['distance_budget']
   e.update(status='valid',seconds=x['entry_seconds'],timely=x['entry_seconds']<=20.010);write(O/'call_ledger.json',ledger)
   records.append(dict(case=c['id'],method=method,route=r,seconds=x['entry_seconds'],timely=e['timely'],source=str(out.resolve()),source_sha256=sha(out)));print(ident,len(r)-1,flush=True)
 for f,v in sources.items():assert sha(f)==v
 write(O/'results.json',dict(protocol=protocol,records=records,actual_entries=len(ledger)))
if __name__=='__main__':
 if len(sys.argv)>1:worker(sys.argv[2],sys.argv[3])
 else:main()
