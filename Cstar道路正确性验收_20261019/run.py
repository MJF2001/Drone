"""Defaults to read-only readiness. --run is the separate bounded execution."""
import sys,json,hashlib,subprocess,time,os,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,z):
    with Path(p).open('xb') as f:f.write(json.dumps(z,ensure_ascii=False,indent=2).encode())
def verify():
    m=read(HERE/'freeze_manifest.json')
    for name,digest in m['local_files'].items():assert sha(HERE/name)==digest,name
    for key in ('external_runtime','prior_sources'):
        for name,digest in m[key].items():assert sha(ROOT/name)==digest,name
    p=read(HERE/'protocol.json');assert len(p['jobs'])==40
    return p
def worker(job_path,dest):
    # Witnesses and metadata are intentionally unavailable to the solver API.
    job=read(job_path);protocol=read(HERE/'protocol.json');c=read(HERE/job['input'])
    request={k:c[k] for k in protocol['core_input_whitelist']}
    begin=time.perf_counter()
    sys.path.insert(0,str(ROOT/protocol['algorithm_source']))
    try:
        from history_adapter import solve
        bootstrap=time.perf_counter()-begin
        r=solve(request,job['budget_seconds'],job['seed'],max_iterations=job['max_iterations'])
        write(dest,dict(worker_status='returned',job=job,input_sha256=sha(HERE/job['input']),bootstrap_seconds=bootstrap,result=r))
        return 0
    except BaseException:
        write(dest,dict(worker_status='exception',job=job,traceback=traceback.format_exc()));return 1
def run():
    p=verify();out=HERE/'execution';out.mkdir(exist_ok=False)
    from audit_outputs import audit
    consecutive=0;records=[];aborted=False
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for job in p['jobs']:
        verify();stem=job['run_id'];jobpath=out/(stem+'.job.json');dest=out/(stem+'.result.json');write(jobpath,job)
        started=time.perf_counter();watchdog=False
        with (out/(stem+'.log')).open('x',encoding='utf8') as log:
            try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',str(jobpath),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=p['watchdog_seconds']).returncode
            except subprocess.TimeoutExpired:code=None;watchdog=True
        row=dict(run_id=stem,watchdog=watchdog,returncode=code,wall_seconds=time.perf_counter()-started,accepted=False)
        if not watchdog and code==0:
            r=read(dest);assert r['job']==job and r['input_sha256']==job['input_sha256']
            try:row.update(audit(read(HERE/job['input']),r['result'],job['budget_seconds']));row['independent_audit']='passed'
            except Exception:row.update(independent_audit='failed',audit_error=traceback.format_exc())
        technical_failure=watchdog or code!=0
        consecutive=consecutive+1 if technical_failure else 0;records.append(row)
        with (out/'ledger.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
        if consecutive>=2:aborted=True;break
    verify();write(out/'completion.json',dict(started=len(records),unstarted=40-len(records),accepted=sum(z['accepted'] for z in records),aborted=aborted,gate='PASS' if len(records)==40 and all(z['accepted'] for z in records) else 'NOT_PASSED',ranking=False,holdout_used=False))
def main():
    if len(sys.argv)>1 and sys.argv[1]=='--worker':return worker(Path(sys.argv[2]),Path(sys.argv[3]))
    if len(sys.argv)>1 and sys.argv[1]=='--run':run();return 0
    p=verify();print(json.dumps(dict(status='SEALED_NOT_RUN' if not (HERE/'execution').exists() else 'EXECUTION_PRESENT',jobs=len(p['jobs']),new_solver_calls=0,read_only=True),ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
