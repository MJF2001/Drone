"""Resume only missing/failed calls after correcting LITERAL adapter dispatch."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,time,traceback
ROOT=Path(__file__).resolve().parent;ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009'/'算法小型验证_20261010';RUN=ALGO/'continuous_history_diagnostics'/'old_plan_warm_global_v0.1_20261017';REC=RUN/'recovery2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def worker(j,dest):
 try:
  sys.path.insert(0,str(ROOT));import portable_frozen,baseline_suite
  from prepare_road_range_diagnostic_20261015 import snapshot
  from verify_continuous_preparation_20261016 import read as rc,route_check
  if j['method']=='P2_WARM_GLOBAL':
   v=ALGO/'candidate_baselines'/'P2_WARM_GLOBAL'/'v0.1_20261017';sys.path.insert(0,str(v));import p2_search_audit_warm as warm
   baseline_suite.p2_solve=lambda s,b,var,sd:warm.solve(s,b,'warm_multi' if var=='multi' else var,sd)
  from outer_connector_candidate_20261016 import solve as literal_solve
  c=rc(Path(j['case']));s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']));t=time.perf_counter()
  if j['method']=='P2_WARM_GLOBAL':raw=baseline_suite.solve(s,initial,'P2_MULTI',j['budget'],j['seed'],portable_frozen.PROFILE);raw['method']='P2_WARM_GLOBAL'
  elif j['method']=='LITERAL':raw=literal_solve(s,initial,j['method'],j['budget'],j['seed'])
  else:raw=portable_frozen.solve(s,initial,j['method'],j['budget'],j['seed'],portable_frozen.PROFILE)
  write(dest,{'worker_status':'returned','case_sha256':sha(j['case']),'method':j['method'],'budget':j['budget'],'seed':j['seed'],'raw':raw,'independent_route_check':route_check(c,raw['route']),'wall_seconds':time.perf_counter()-t});return 0
 except BaseException:write(dest,{'worker_status':'exception','traceback':traceback.format_exc()});return 1
def main():
 p=read(RUN/'protocol.json');jobs=p['jobs'];old=[json.loads(x) for x in (RUN/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()];success={x['run_id'] for x in old if x['valid']};pending=[j for j in jobs if j['run_id'] not in success];(REC/'runs').mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1');start=time.perf_counter();rows=[]
 with (REC/'recovery_ledger.jsonl').open('x',encoding='utf-8') as ledger:
  for i,j in enumerate(pending,1):
   dest=REC/'runs'/(j['run_id']+'.json');log=REC/'runs'/(j['run_id']+'.log');t=time.perf_counter()
   try:
    with log.open('x',encoding='utf-8') as out:code=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',json.dumps(j,ensure_ascii=False),str(dest)],cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
    watchdog=False
   except subprocess.TimeoutExpired:code=None;watchdog=True
   q=read(dest) if dest.exists() else {};raw=q.get('raw',{});check=q.get('independent_route_check',{});row=dict(j,worker_status=q.get('worker_status','no_result'),returncode=code,watchdog_timeout=watchdog,valid=bool(check.get('valid')) and not watchdog,steps=check.get('steps'),seconds=raw.get('seconds'),source=raw.get('source'),overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01,process_wall_seconds=time.perf_counter()-t);rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
   if i%5==0:print(f'recovered {i}/{len(pending)} valid {sum(x["valid"] for x in rows)}',flush=True)
 write(REC/'completion.json',{'recovered_attempts':len(rows),'valid':sum(x['valid'] for x in rows),'exceptions':sum(x['worker_status']=='exception' for x in rows),'watchdog_timeouts':sum(x['watchdog_timeout'] for x in rows),'wall_seconds':time.perf_counter()-start,'reason':'recover failed or unattempted jobs after LITERAL adapter dispatch error; original attempts preserved'})
 write(REC/'sha256.json',{str(x.relative_to(REC)):sha(x) for x in REC.rglob('*') if x.is_file()})
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(json.loads(sys.argv[2]),Path(sys.argv[3])))
 main()

