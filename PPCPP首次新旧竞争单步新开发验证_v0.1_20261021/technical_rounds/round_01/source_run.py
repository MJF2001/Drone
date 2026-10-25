"""Three finite phases, serial fresh processes, no retry or silent resume."""
from common import *
from evaluation import job_row,check_formal_pair
import sys,subprocess,os,time
def run(phase):
    assert phase in ('prep','gate','formal');require('technical');require('action_stubs');cfg=plan();check_seal('seal1' if phase=='prep' else 'seal2')
    if phase=='formal':require('gate')
    if phase=='gate':require('inputs_audited')
    actual=H/'actual_order.jsonl';past=[json.loads(x) for x in actual.read_text(encoding='utf8').splitlines()] if actual.exists() else []
    expected=0 if phase=='prep' else cfg['counts']['prep'] if phase=='gate' else cfg['counts']['prep']+cfg['counts']['gate'];assert len(past)==expected,('no_resume',phase,len(past))
    order=read(H/('order.json' if phase=='formal' else phase+'_order.json'));assert len(order)==cfg['counts'][phase]
    rows=[];consecutive=0;env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for i,j in enumerate(order):
        require('technical');require('action_stubs');check_seal(j['seal'][:-5]);assert len(past)<cfg['entry_cap']
        out=H/'outputs'/f'{j["id"]}.json';log=H/'logs'/f'{j["id"]}.txt';assert not out.exists() and not log.exists()
        item=dict(id=j['id'],phase=phase,mode=j['mode'],sequence=len(past)+1,process_start_utc=time.time())
        with actual.open('a',encoding='utf8') as f:f.write(json.dumps(item)+'\n')
        past.append(item)
        try:
            try:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,capture_output=True,timeout=90);code=p.returncode;data=p.stdout+p.stderr
            except subprocess.TimeoutExpired as ex:code='watchdog';data=(ex.stdout or b'')+(ex.stderr or b'')
            with log.open('xb') as f:f.write(data)
            markers=dict(entries=data.count(b'ENTRY_START '),cores=data.count(b'CORE_START '));assert markers['entries']<=1 and markers['cores']<=1
            if code!=0:
                consecutive+=1;save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,status='WATCHDOG' if code=='watchdog' else 'PROCESS_ABNORMAL',exit_code=code,markers=markers,no_retry=True))
                if phase!='formal' or b'Traceback' in data or consecutive>=2:raise RuntimeError(('technical_or_process_stop',j['id'],code))
                continue
            consecutive=0;row=job_row(j);assert markers==dict(entries=1,cores=1)
            if phase!='formal':assert row['valid'] and row['timely']
            proof=check_formal_pair(j)
            save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,status=row['status'],exit_code=0,valid=row['valid'],timely=row['timely'],markers=markers,output_sha256=sha(out),pair_proof=proof,no_retry=True));rows.append(row)
            print(phase,i+1,'/',len(order),j['id'],row['status'],f'{row["seconds"]:.6f}s',flush=True)
        except BaseException as ex:
            save(H/'STOP.json',dict(stage=phase,id=j['id'],reason=repr(ex),attempted_processes=len(past),no_retry=True));raise
    save(H/(phase+'_metrics.json'),rows)
    if phase=='gate':save(H/'OFF_equivalence.json',[dict(job=r['job'],equivalence=r['equivalence'],all_metrics_equal=True) for r in rows if r['job']['mode']=='OFF'])
    receipt(phase,[H/(phase+'_metrics.json'),*[H/'logs'/f'{j["id"]}.receipt.json' for j in order],*[H/'outputs'/f'{j["id"]}.json' for j in order if (H/'outputs'/f'{j["id"]}.json').exists()],*([H/'OFF_equivalence.json'] if phase=='gate' else [])])
    print('PASS',phase,'fixed phase complete',flush=True)
if __name__=='__main__':run(sys.argv[1])
