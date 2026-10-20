"""Resume only missing results after user interruption; preserve partial logs."""
from run_outer_connector_diagnostic_20261016 import *
def main():
    protocol=read(OUT/'protocol.json');jobs=protocol['jobs']
    rows=[json.loads(v) for v in (OUT/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==115 and [r['run_id'] for r in rows]==[j['run_id'] for j in jobs[:115]]
    assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items());manifest(INPUT)
    pending=jobs[115:];assert all(not (OUT/'runs'/(j['run_id']+'.json')).exists() for j in pending)
    partial=OUT/'runs'/(pending[0]['run_id']+'.log');assert partial.exists()
    write(OUT/'interruption_record.json',dict(reason='User interrupted previous turn; no Python processes remained; 115 completed rows preserved.',
        completed_before_resume=115,ledger_sha256_before_resume=sha(OUT/'execution_ledger.jsonl'),
        excluded_incomplete_attempt=pending[0]['run_id'],partial_log_sha256=sha(partial),
        partial_attempt_not_in_comparison=True,resume_source_sha256=sha(Path(__file__)),new_completed_calls_planned=5))
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');start=time.perf_counter()
    with (OUT/'execution_ledger.jsonl').open('a',encoding='utf-8') as ledger:
        for j in pending:
            dest=OUT/'runs'/(j['run_id']+'.json');t=time.perf_counter();timeout=False
            with (OUT/'runs'/(j['run_id']+'.resumed.log')).open('x',encoding='utf-8') as log:
                try:code=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'run_outer_connector_diagnostic_20261016.py'),'--worker',j['case'],j['method'],str(j['budget']),str(dest)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=j['budget']+30).returncode
                except subprocess.TimeoutExpired:code=None;timeout=True
            payload=read(dest) if dest.exists() else {};raw=payload.get('raw',{});check=payload.get('independent_route_check',{})
            row=dict(j,returncode=code,watchdog_timeout=timeout,worker_status=payload.get('worker_status','no_result'),valid=bool(check.get('valid')) and not timeout,steps=check.get('steps'),seconds=raw.get('seconds'),source=raw.get('source'),process_wall_seconds=time.perf_counter()-t,overrun_gt_10ms=raw.get('seconds',0)>j['budget']+.01)
            rows.append(row);ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush();print(j['run_id'],row['valid'],flush=True)
    assert len(rows)==120 and all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    write(OUT/'completion.json',dict(calls=120,completed_comparisons=120,excluded_incomplete_attempts=1,total_process_attempts=121,
        valid=sum(r['valid'] for r in rows),exceptions=sum(r['worker_status']=='exception' for r in rows),watchdog_timeouts=sum(r['watchdog_timeout'] for r in rows),
        resumed_wall_seconds=time.perf_counter()-start,completed_process_wall_seconds=sum(r['process_wall_seconds'] for r in rows),protected_unchanged=True,holdout_used=False))
    write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
if __name__=='__main__':main()
