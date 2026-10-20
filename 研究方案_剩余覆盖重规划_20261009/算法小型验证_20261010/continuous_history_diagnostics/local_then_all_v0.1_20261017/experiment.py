from pathlib import Path
import sys,json,os,time,subprocess,hashlib,datetime,traceback
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';SOURCE=D/'source_snapshot'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def init():
 sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(SOURCE))
 import portable_frozen
 return portable_frozen
def verify_hashes(pr):
 for p,h in pr['protected_hashes'].items():assert sha(p)==h,('protected mismatch',p)
def worker(j,dest):
 try:
  assert sha(j['case'])==j['case_sha256'];pf=init()
  from prepare_road_range_diagnostic_20261015 import snapshot
  from audit_helpers import route_errors
  def route_check(c,r):
   e=route_errors(c,r);return dict(valid=not e,errors=e,steps=len(r)-1 if r else None)
  import fixed_scope_candidate as candidate
  c=read(j['case']);s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']))
  started=utc()
  if j['method']=='LOCAL_THEN_ALL':
   import local_then_all
   raw=local_then_all.solve(s,initial,j['method'],j['budget'],j['seed'])
  else:raw=candidate.solve(s,initial,'LITERAL',j['budget'],j['seed'],scope_name=j['method'].replace('FIX_','R_'))
  ended=utc();loaded={}
  for n,m in list(sys.modules.items()):
   f=getattr(m,'__file__',None)
   if f and Path(f).is_file() and (str(SOURCE) in str(f) or str(ALGO/'.deps') in str(f)):
    loaded[n]={'path':str(Path(f).resolve()),'sha256':sha(f)}
  write(dest,dict(job=j,worker_status='returned',pid=os.getpid(),started_utc=started,ended_utc=ended,raw=raw,
   independent_route_check=route_check(c,raw.get('route',[])),loaded_modules=loaded))
  return 0
 except BaseException:
  write(dest,dict(job=j,worker_status='exception',pid=os.getpid(),ended_utc=utc(),traceback=traceback.format_exc()));return 1

def run_batch(mode):
 pre=mode=='preflight';protocol=read(D/('preflight_protocol.json' if pre else 'protocol.json'));verify_hashes(protocol)
 folder=D/('preflight' if pre else 'formal');folder.mkdir(exist_ok=True)
 ledger=folder/'attempts.jsonl';done={}
 if ledger.exists():
  for line in ledger.read_text(encoding='utf-8').splitlines():
   x=json.loads(line);assert x['run_id'] not in done;done[x['run_id']]=x
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
 for j in protocol['jobs']:
  rid=j['run_id']
  if rid in done:
   assert done[rid]['worker_status']=='returned','Cannot silently retry prior exception/interrupted entry';continue
  # Wait for competing Python calculations; never terminate another session.
  while True:
   probe=subprocess.run(['powershell','-NoProfile','-Command',"Get-Process python,pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],capture_output=True,text=True)
   other=[int(v) for v in probe.stdout.split() if v.isdigit() and int(v)!=os.getpid()]
   if not other:break
   with (folder/'competition.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(utc=utc(),pids=other))+'\n')
   print('WAIT_COMPETING',other,flush=True);time.sleep(20)
  dest=folder/(rid+'.json');assert not dest.exists(),'orphan output requires manual diagnosis'
  jobfile=folder/(rid+'.job.json');write(jobfile,j)
  log=folder/(rid+'.log');cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'worker',str(jobfile),str(dest)]
  started=utc();t=time.perf_counter()
  with log.open('x',encoding='utf-8') as out:
   child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
   launch={'run_id':rid,'pid':child.pid,'started_utc':started,'command':cmd,'case_sha256':sha(j['case']),'worker_sha256':sha(__file__),'candidate_sha256':sha(SOURCE/'fixed_scope_candidate.py')}
   write(folder/(rid+'.launch.json'),launch)
   try:code=child.wait(timeout=j['budget']+30);watchdog=False
   except subprocess.TimeoutExpired:child.kill();child.wait();code=child.returncode;watchdog=True
  result=read(dest) if dest.exists() else {};raw=result.get('raw',{})
  entry=dict(run_id=rid,job=j,worker_status=result.get('worker_status','missing_result'),returncode=code,watchdog=watchdog,
   started_utc=started,ended_utc=utc(),pid=child.pid,command=cmd,wall_seconds=time.perf_counter()-t,result_path=str(dest),
   valid=result.get('independent_route_check',{}).get('valid',False),seconds=raw.get('seconds'),source=raw.get('source'))
  with ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
  done[rid]=entry;print(json.dumps({'mode':mode,'completed':len(done),'total':len(protocol['jobs']),'last':rid,'valid':entry['valid']}),flush=True)
  if code!=0 or watchdog or entry['worker_status']!='returned':raise RuntimeError('Stopped at first infrastructure exception; see immutable attempt evidence')
 verify_hashes(protocol)
 print('BATCH_COMPLETE',mode,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='worker':sys.exit(worker(read(sys.argv[2]),Path(sys.argv[3])))
 run_batch(sys.argv[1])
