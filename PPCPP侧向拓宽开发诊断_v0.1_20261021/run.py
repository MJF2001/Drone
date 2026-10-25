"""Sequential fixed slots, explicit process outcomes, no retry or silent resume."""
from analysis import job_row
from common import *
import sys,os,subprocess,time
def run(phase):
    assert phase in ('prep','gate','formal');require('stat_stubs');sealname='seal1' if phase=='prep' else 'seal2';require(sealname);check_seal(sealname+'.json')
    if phase!='prep':require('generated');require('prep')
    if phase=='formal':require('gate')
    order=read(H/({'prep':'prep_order.json','gate':'gate_order.json','formal':'order.json'}[phase]));actual=H/'actual_order.jsonl';past=[json.loads(x) for x in actual.read_text(encoding='utf8').splitlines()] if actual.exists() else [];expected={'prep':0,'gate':6,'formal':18}[phase];assert len(past)==expected,('no_silent_resume',phase,len(past));env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');rows=[];consecutive=0
    for i,j in enumerate(order):
        assert len(past)<306;check_seal(sealname+'.json');require(sealname);out=H/'outputs'/f'{j["id"]}.json';log=H/'logs'/f'{j["id"]}.txt';assert not out.exists() and not log.exists()
        start=dict(id=j['id'],phase=phase,sequence=len(past)+1,process_start_utc=time.time())
        with actual.open('a',encoding='utf8') as f:f.write(json.dumps(start)+'\n')
        past.append(start);code=None;data=b''
        try:
            try:
                p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/f'{j["id"]}.json'),str(out)],env=env,capture_output=True,timeout=90);code=p.returncode;data=p.stdout+p.stderr
            except subprocess.TimeoutExpired as ex:code='watchdog';data=(ex.stdout or b'')+(ex.stderr or b'')
            with log.open('xb') as f:f.write(data)
            markers=dict(entry_starts=data.count(b'ENTRY_START '),core_starts=data.count(b'CORE_START '));assert markers['entry_starts']<=1 and markers['core_starts']<=1
            if code!=0:
                consecutive+=1;status='WATCHDOG' if code=='watchdog' else 'PROCESS_ABNORMAL';save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,exit_code=code,status=status,markers=markers,output_exists=out.exists(),no_retry=True))
                if phase!='formal' or b'Traceback' in data or consecutive>=2:raise RuntimeError(('process_or_technical_stop',j['id'],code))
                print(phase,i+1,'/',len(order),j['id'],status,flush=True);continue
            consecutive=0;row=job_row(j);assert markers==dict(entry_starts=1,core_starts=row['core_calls'])
            if phase!='formal':assert row['valid'] and row['timely'],('gate_or_prep_not_full_legal_timely',j['id'])
            save(H/'logs'/f'{j["id"]}.receipt.json',dict(job=j,exit_code=0,status=row['status'],valid=row['valid'],timely=row['timely'],markers=markers,output_sha256=sha(out),no_retry=True));rows.append(row)
            print(phase,i+1,'/',len(order),j['id'],row['status'],f'{row["seconds"]:.6f}s',flush=True)
        except BaseException as ex:
            save(H/'STOP.json',dict(stage=phase,id=j['id'],reason=repr(ex),attempted_processes=len(past),no_retry=True));raise
    if phase in ('prep','gate'):
        assert len(rows)==len(order);save(H/f'{phase}_metrics.json',rows);receipt(phase,[H/f'{phase}_metrics.json',*[H/'outputs'/f'{j["id"]}.json' for j in order]])
    else:receipt('formal',[H/'order.json',*[H/'logs'/f'{j["id"]}.receipt.json' for j in order]])
    print('PASS',phase,'fixed phase completed; no retry',flush=True)
if __name__=='__main__':run(sys.argv[1])
