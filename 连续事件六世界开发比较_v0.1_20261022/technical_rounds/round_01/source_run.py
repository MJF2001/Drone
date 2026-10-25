"""The single fixed batch, serial isolated sessions, no retry/resume."""
from util import *
from real_audit import inspect_session
import sys,subprocess,time
def main():
    cfg=config();check_seal();assert not (H/'actual_sessions.jsonl').exists() and not (H/'actual_attempts.jsonl').exists();proofs=[];counter={'BFS':0}
    try:
        for sj in read(H/'session_order.json'):
            job=H/'jobs'/(sj['id']+'.session.json');save(job,sj)
            with (H/'actual_sessions.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(sj)+'\n')
            print('SESSION_START',sj['id'],flush=True)
            try:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'session.py'),str(job)],env=env(),capture_output=True,timeout=300);code=p.returncode;log=p.stdout+p.stderr
            except subprocess.TimeoutExpired as ex:code='session_watchdog';log=(ex.stdout or b'')+(ex.stderr or b'')
            put(H/'logs'/(sj['id']+'.session.log'),log)
            if code!=0:raise RuntimeError(('technical_session_stop',sj['id'],code,log.decode('utf8',errors='replace')[-2000:]))
            before=counter['BFS']
            try:proof=inspect_session(sj,counter)
            finally:
                with (H/'independent_audit_BFS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(session=sj['id'],BFS=counter['BFS']-before,cumulative=counter['BFS']))+'\n')
            save(H/'sessions'/(sj['id']+'.audit.json'),proof);proofs.append(proof);s=proof['summary'];print('SESSION_END',sj['id'],s['status'],'actual_M',s['M'],'responses',s['response_calls'],flush=True)
        save(H/'acceptance.json',dict(batch_complete=True,sessions=len(proofs),proofs=proofs,independent_audit_BFS=counter['BFS'],all_saved_sessions_independently_audited=True,performance_success_is_not_technical_gate=True))
        receipt('real',[H/'acceptance.json',*sorted((H/'sessions').glob('*.json')),*sorted((H/'outputs').glob('*.json')),*sorted((H/'logs').glob('*.receipt.json'))]);print('COMPLETE fixed development batch; stop all new calls',flush=True)
    except BaseException as ex:
        save(H/'STOP.json',dict(stage='technical_batch_stop',exception=repr(ex),finished_audits=len(proofs),independent_audit_BFS=counter['BFS'],no_retry=True,no_execution_chain_fix_after_real=True,utc=time.time()));raise
if __name__=='__main__':main()
