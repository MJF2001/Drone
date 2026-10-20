"""Run the sealed 120-call P2_WARM_GLOBAL development comparison."""
from pathlib import Path
import sys, json, hashlib, subprocess, os, time, traceback
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009'/'算法小型验证_20261010'
RUN=ALGO/'continuous_history_diagnostics'/'old_plan_warm_global_v0.1_20261017'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def worker(case,method,budget,seed,dest):
 try:
  sys.path.insert(0,str(ROOT))
  import portable_frozen
  import baseline_suite
  from prepare_road_range_diagnostic_20261015 import snapshot
  from verify_continuous_preparation_20261016 import read as read_case,route_check
  if method=='P2_WARM_GLOBAL':
   v=ALGO/'candidate_baselines'/'P2_WARM_GLOBAL'/'v0.1_20261017'
   sys.path.insert(0,str(v)); import p2_search_audit_warm as warm
   baseline_suite.p2_solve=lambda s,b,var,sd:warm.solve(s,b,'warm_multi' if var=='multi' else var,sd)
  c=read_case(case);s=snapshot(c);initial=set(map(tuple,c['metadata']['initial_targets']))
  t=time.perf_counter()
  if method=='P2_WARM_GLOBAL': raw=baseline_suite.solve(s,initial,'P2_MULTI',budget,seed,portable_frozen.PROFILE);raw['method']='P2_WARM_GLOBAL'
  else: raw=portable_frozen.solve(s,initial,method,budget,seed,portable_frozen.PROFILE)
  result={'worker_status':'returned','case_sha256':sha(case),'method':method,'budget':budget,'seed':seed,'raw':raw,'independent_route_check':route_check(c,raw['route']),'wall_seconds':time.perf_counter()-t}
  write(dest,result);return 0
 except BaseException:
  write(dest,{'worker_status':'exception','traceback':traceback.format_exc()});return 1
def main():
 protocol=read(RUN/'protocol.json'); jobs=protocol['jobs'];assert len(jobs)==120
 assert Path(sys.executable).resolve()==ROOT/'运行环境'/'python'/'python.exe'
 assert all(sha(p)==h for p,h in protocol['protected_hashes'].items())
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 rows=[];start=time.perf_counter()
 with (RUN/'execution_ledger.jsonl').open('x',encoding='utf-8') as ledger:
  for idx,j in enumerate(jobs,1):
   dest=RUN/'runs'/(j['run_id']+'.json');log=RUN/'runs'/(j['run_id']+'.log');t=time.perf_counter()
   try:
    with log.open('x',encoding='utf-8') as out:
     code=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',j['case'],j['method'],str(j['budget']),str(j['seed']),str(dest)],cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
    watchdog=False
   except subprocess.TimeoutExpired: code=None;watchdog=True
   p=read(dest) if dest.exists() else {};raw=p.get('raw',{});check=p.get('independent_route_check',{})
   row=dict(j,worker_status=p.get('worker_status','no_result'),returncode=code,watchdog_timeout=watchdog,valid=bool(check.get('valid')) and not watchdog,steps=check.get('steps'),seconds=raw.get('seconds'),source=raw.get('source'),overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01,process_wall_seconds=time.perf_counter()-t)
   rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush()
   if idx%5==0: print(f'completed {idx}/120 valid {sum(x["valid"] for x in rows)}',flush=True)
   if Path(dest).exists():
    with dest.open('r+',encoding='utf-8') as f: pass
  assert all(sha(p)==h for p,h in protocol['protected_hashes'].items())
  write(RUN/'completion.json',{'calls':len(rows),'valid':sum(x['valid'] for x in rows),'exceptions':sum(x['worker_status']=='exception' for x in rows),'watchdog_timeouts':sum(x['watchdog_timeout'] for x in rows),'wall_seconds':time.perf_counter()-start,'protected_unchanged':True,'holdout_used':False})
  write(RUN/'sha256.json',{str(p.relative_to(RUN)):sha(p) for p in RUN.rglob('*') if p.is_file()})
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':sys.exit(worker(Path(sys.argv[2]),sys.argv[3],float(sys.argv[4]),int(sys.argv[5]),Path(sys.argv[6])))
 main()

