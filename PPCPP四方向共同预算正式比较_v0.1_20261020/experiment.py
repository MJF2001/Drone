import os,sys,json,hashlib,subprocess,time,statistics,csv
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
O=R/'PPCPP四方向接口适配验收_v0.1_20261020';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
sys.path.insert(0,str(P));sys.path.insert(0,str(O))
import entry,audit_orient,runtime,p2_adapter,candidate
def imports():
 return {str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
def worker(jp,out):
 j=read(jp);seal=read(H/'seal.json');hs={}
 for p in imports():
  if Path(p).is_relative_to(R):assert p in seal and sha(p)==seal[p],p;hs[p]=sha(p)
 inp=H/j['input'];assert sha(inp)==j['input_sha256'];payload=inp.read_bytes()
 if j['method']=='ORIENT4':x=entry.run(payload,'COMBO',20,j['seed'])
 elif j['method']=='PPCPP':x=runtime.run_payload(payload,'PPCPP',20,j['seed'])
 else:x=p2_adapter.run_payload(payload,20,j['seed'])
 save(out,dict(job=j,result=x,imports=hs))
def setup():
 for d in ('inputs','jobs','outputs','logs'): (H/d).mkdir()
 cases=sorted((O/'inputs').glob('*.json'));assert len(cases)==54
 for p in cases:(H/'inputs'/p.name).write_bytes(p.read_bytes())
 order=[];methods=['PPCPP','ORIENT4','P2_MULTI']
 for i,p in enumerate(cases):
  for rep in range(3):
   offset=(i+rep)%3
   for m in methods[offset:]+methods[:offset]:
    j=dict(id=f'{p.stem}__{rep}__{m}',case=p.stem,rep=rep,seed=20261020+rep,method=m,budget=20,input='inputs/'+p.name,input_sha256=sha(p));save(H/'jobs'/f'{j["id"]}.json',j);order.append(j)
 save(H/'order.json',order)
 prior=read(O/'environment_seal.json')['files']
 for p,h in prior.items():assert sha(p)==h,p
 paths=set(prior)|imports()|{str(p.resolve()) for p in H.rglob('*') if p.is_file()}
 save(H/'seal.json',{p:sha(p) for p in sorted(paths)})
 print('PRESEALED',len(paths),'jobs',len(order),flush=True)
def run():
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 for i,j in enumerate(read(H/'order.json')):
  out=H/'outputs'/f'{j["id"]}.json';assert not out.exists()
  start=time.time()
  try:
   p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,capture_output=True,timeout=90)
   (H/'logs'/f'{j["id"]}.txt').write_bytes(p.stdout+p.stderr);code=p.returncode
  except subprocess.TimeoutExpired as e:
   code='watchdog';(H/'logs'/f'{j["id"]}.txt').write_text(str(e),encoding='utf8')
  with (H/'actual_order.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(id=j['id'],code=code,wall=time.time()-start))+'\n')
  if code!=0:print('TECHNICAL STOP',j['id'],code,flush=True);return
  if (i+1)%27==0:print('completed',i+1,'/486',flush=True)
 print('FORMAL FINISHED',flush=True)
def compute():
 rows=[];groups={};fail=[]
 for j in read(H/'order.json'):
  p=H/'outputs'/f'{j["id"]}.json'
  if not p.exists():fail.append(dict(id=j['id'],reason='missing'));continue
  x=read(p)['result'];c=read(H/j['input']);raw=x['raw'];route=raw.get('route',[])
  if not route:fail.append(dict(id=j['id'],reason=raw.get('status')));continue
  m=audit_orient.metric(c,route);assert m==audit_orient.cross(c,route) and m['complete_legal']
  if j['method']=='ORIENT4':audit_orient.check(c,x)
  if j['method']=='PPCPP':audit_orient.scalar.audit(c,raw['branches']['P0'])
  row=dict(**j,seconds=x['entry_seconds'],timely=x['entry_seconds']<20,metrics=m,source=raw.get('source'),direction=raw.get('selected_degree'));rows.append(row)
  groups.setdefault((j['case'],j['rep']),{})[j['method']]=x
 for g in groups.values():
  if 'PPCPP' in g and 'ORIENT4' in g:
   assert audit_orient.semantics(g['PPCPP']['raw']['branches']['P0'])==audit_orient.semantics(g['ORIENT4']['raw']['candidates'][0]['raw'])
 summary={}
 for method in ('PPCPP','ORIENT4','P2_MULTI'):
  rr=[r for r in rows if r['method']==method];ts=[r['seconds'] for r in rr]
  summary[method]=dict(n=len(rr),timely=sum(r['timely'] for r in rr),mean_ms=statistics.mean(ts)*1000,median_ms=statistics.median(ts)*1000,max_ms=max(ts)*1000,totals={k:sum(r['metrics'][k] for r in rr)/3 for k in rr[0]['metrics'] if isinstance(rr[0]['metrics'][k],(int,float)) and not isinstance(rr[0]['metrics'][k],bool)})
 pairs={}
 for other in ('PPCPP','P2_MULTI'):
  ds=[]
  for key,g in groups.items():
   if all(m in g and g[m]['entry_seconds']<20 and g[m]['raw'].get('route') for m in ('ORIENT4',other)):
    ds.append(len(g['ORIENT4']['raw']['route'])-len(g[other]['raw']['route']))
  pairs[other]=dict(n=len(ds),short=sum(d<0 for d in ds),equal=ds.count(0),long=sum(d>0 for d in ds),delta_sum=sum(ds))
 return dict(rows=rows,summary=summary,pairs=pairs,failures=fail)
def analyze():
 a=compute();save(H/'analysis.json',a)
 rr=[dict(**{k:v for k,v in r.items() if k!='metrics'},**r['metrics']) for r in a['rows']]
 with (H/'全部调用指标.csv').open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
 print(json.dumps({k:v for k,v in a.items() if k!='rows'},ensure_ascii=False),flush=True)
def verify():
 for p,h in read(H/'seal.json').items():assert sha(p)==h,p
 for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
 assert compute()==read(H/'analysis.json')
 print('PASS: source seal, manifest, all routes double metrics, orientation decisions, P0 equivalence, aggregates. No solver calls.')
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='worker':worker(sys.argv[2],sys.argv[3])
 elif mode=='setup':setup()
 elif mode=='run':run()
 elif mode=='analyze':analyze()
 elif mode=='verify':verify()
