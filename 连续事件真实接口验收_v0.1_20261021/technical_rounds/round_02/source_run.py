"""Six ordered isolated sessions; no retry/resume and no performance ranking."""
from util import *
from real_audit import inspect_session
import sys,subprocess
def main():
    config();check_seal();assert not (H/'actual_sessions.jsonl').exists() and not (H/'actual_attempts.jsonl').exists();proofs=[];counter={'BFS':0}
    for sj in read(H/'session_order.json'):
        job=H/'jobs'/(sj['id']+'.session.json');save(job,sj)
        with (H/'actual_sessions.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(sj)+'\n')
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'session.py'),str(job)],env=env(),capture_output=True,timeout=300);put(H/'logs'/(sj['id']+'.session.log'),p.stdout+p.stderr)
        if p.returncode!=0:
            save(H/'STOP.json',dict(stage='real_session',session=sj,exit_code=p.returncode,no_retry=True));raise RuntimeError(('session_technical_stop',sj['id'],p.stderr.decode('utf8',errors='replace')[-2000:]))
        proof=inspect_session(sj,counter);save(H/'sessions'/(sj['id']+'.audit.json'),proof);proofs.append(proof)
        print(sj['id'],'INTERFACE_PASS' if proof['passed'] else 'ACCEPTANCE_NOT_PASSED',flush=True)
    save(H/'acceptance.json',dict(interface_pass=all(p['passed'] for p in proofs),six_sessions=len(proofs),proofs=proofs,independent_audit_BFS=counter['BFS'],W3_zero_credit_paths_all_covered=all(p['W3_base_zero_credit_triggered'] for p in proofs if p['session']['world']=='W3'),no_ranking=True))
    receipt('real',[H/'acceptance.json',*sorted((H/'sessions').glob('*.json')),*sorted((H/'outputs').glob('*.json')),*sorted((H/'logs').glob('*.receipt.json'))]);print('COMPLETE fixed interface batch; no further experiments',flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as ex:
        if not (H/'STOP.json').exists():save(H/'STOP.json',dict(stage='unhandled_chain_failure',exception=repr(ex),no_retry=True))
        raise
