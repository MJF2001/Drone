"""Fixed OFF144 then ON144; no retries/resume; failures retained."""
from common import *
from decision_audit import job_row
import sys,subprocess,os,time
def run(mode):
    assert mode in ('OFF','ON');require('technical');require('action_stubs');preseal();cfg=plan()
    if mode=='ON':require('OFF')
    actual=H/'actual_order.jsonl';past=[json.loads(x) for x in actual.read_text(encoding='utf8').splitlines()] if actual.exists() else [];assert len(past)==(0 if mode=='OFF' else cfg['counts']['OFF']),('no_silent_resume',mode,len(past))
    order=[j for j in read(H/'order.json') if j['mode']==mode];assert len(order)==cfg['counts'][mode];rows=[];consecutive=0;env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for i,j in enumerate(order):
        require('technical');require('action_stubs');preseal();assert len(past)<cfg['entry_cap'];out=H/'outputs'/f'{j["id"]}.json';log=H/'logs'/f'{j["id"]}.txt';assert not out.exists() and not log.exists()
        item=dict(id=j['id'],mode=mode,sequence=len(past)+1,process_start_utc=time.time())
        with actual.open('a',encoding='utf8') as f:f.write(json.dumps(item)+'\n')
        past.append(item)
        try:
            try:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,capture_output=True,timeout=90);code=p.returncode;data=p.stdout+p.stderr
            except subprocess.TimeoutExpired as ex:code='watchdog';data=(ex.stdout or b'')+(ex.stderr or b'')
            with log.open('xb') as f:f.write(data)
            markers=dict(entries=data.count(b'ENTRY_START '),cores=data.count(b'CORE_START '));assert markers['entries']<=1 and markers['cores']<=1
            if code!=0:
                consecutive+=1;save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,status='WATCHDOG' if code=='watchdog' else 'PROCESS_ABNORMAL',exit_code=code,markers=markers,no_retry=True))
                if mode=='OFF' or b'Traceback' in data or consecutive>=2:raise RuntimeError(('technical_or_process_stop',j['id'],code))
                print(mode,i+1,'/',len(order),j['id'],'process failure retained',flush=True);continue
            consecutive=0;row=job_row(j);assert markers==dict(entries=1,cores=1)
            if mode=='OFF':assert row['valid'] and row['timely'] and row['equivalence']['passed']
            save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,status=row['status'],exit_code=0,valid=row['valid'],timely=row['timely'],markers=markers,output_sha256=sha(out),no_retry=True));rows.append(row)
            print(mode,i+1,'/',len(order),j['id'],row['status'],f'{row["seconds"]:.6f}s',flush=True)
        except BaseException as ex:
            save(H/'STOP.json',dict(stage=mode,id=j['id'],reason=repr(ex),attempted_processes=len(past),no_retry=True));raise
    save(H/f'{mode}_metrics.json',rows)
    if mode=='OFF':assert len(rows)==cfg['counts']['OFF'];save(H/'OFF_equivalence.json',[dict(job=r['job'],equivalence=r['equivalence'],all_metrics_equal=True) for r in rows])
    receipt(mode,[H/f'{mode}_metrics.json',*[H/'logs'/f'{j["id"]}.receipt.json' for j in order],*[H/'outputs'/f'{j["id"]}.json' for j in order if (H/'outputs'/f'{j["id"]}.json').exists()],*([H/'OFF_equivalence.json'] if mode=='OFF' else [])])
    print('PASS',mode,'fixed phase complete',flush=True)
if __name__=='__main__':run(sys.argv[1])
