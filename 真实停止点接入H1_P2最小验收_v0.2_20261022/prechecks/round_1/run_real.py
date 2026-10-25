"""Only remaining original 11 jobs, serial and no retries."""
from pathlib import Path
import subprocess,sys,os,json,time,traceback
from v02_utils import HERE,read,dump,sha,now

def main():
    assert not (HERE/'attempts.jsonl').exists(),'batch already attempted; no automatic resume'
    reg=read(HERE/'registration.json')
    assert len(reg['resume_jobs'])==11 and all(j['id']!='01_H1' for j in reg['resume_jobs'])
    freeze=read(HERE/'real_freeze.json')
    for name,digest in freeze['files'].items():
        assert sha(HERE/name)==digest
    assert read(HERE/'reuse_ready.json')['status']=='reused_saved_reaudited'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    attempted,completed,failure=[],[],None
    for job in reg['resume_jobs']:
        attempted.append(job['id'])
        with (HERE/'attempts.jsonl').open('a',encoding='utf-8') as file:
            file.write(json.dumps({'utc':now(),'id':job['id'],'event':'attempted_once'},ensure_ascii=False)+'\n')
        start=time.perf_counter()
        try:
            proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),job['id']],env=env,capture_output=True,timeout=45)
            (HERE/'logs'/(job['id']+'.log')).write_bytes(proc.stdout+proc.stderr)
            if proc.returncode:
                raise RuntimeError('worker_exit:'+str(proc.returncode))
            data=read(HERE/'outputs'/(job['id']+'.json'))
            assert data['passed'] is True
            completed.append(job['id'])
        except Exception as error:
            failure={'job':job,'reason':repr(error),'traceback':traceback.format_exc(),
                     'external_worker_wall_seconds':time.perf_counter()-start}
        dump(HERE/'batch_status.json',{'utc':now(),'planned_new':11,'attempted':attempted,'completed':completed,
             'failed':int(bool(failure)),'not_run':11-len(attempted),'failure':failure,
             'old_01_H1_reused_only':True,'stopped':bool(failure) or len(completed)==11})
        print(job['id'],'STOP_FAILED' if failure else 'passed',f'{len(completed)}/11',flush=True)
        if failure:
            raise SystemExit(1)

if __name__=='__main__':
    main()
