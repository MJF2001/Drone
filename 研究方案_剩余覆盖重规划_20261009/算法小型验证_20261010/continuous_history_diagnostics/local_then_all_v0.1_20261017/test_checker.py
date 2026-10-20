from pathlib import Path
import json,copy,subprocess,sys
from verify import read,check_result,check_unique
D=Path(__file__).resolve().parent;pr=read(D/'preflight_protocol.json');j=next(j for j in pr['jobs'] if j['method']=='LOCAL_THEN_ALL' and j['budget']==1);x=read(D/'preflight'/(j['run_id']+'.json'));checks=[]
def reject(name,fn):
 try:fn()
 except (AssertionError,ValueError,StopIteration):checks.append(name);return
 raise AssertionError('tamper missed '+name)
for kind in ('illegal_route','omitted_goal','wrong_stage_scope','forged_acceptance','first_late_acceptance','module_hash'):
 y=copy.deepcopy(x)
 if kind=='illegal_route':y['raw']['route'][0]=[99999,99999]
 if kind=='omitted_goal':y['raw']['route']=y['raw']['route'][:1]
 if kind=='wrong_stage_scope':y['raw']['candidate_events'][0]['stage_scope']='R_ALL'
 if kind=='forged_acceptance':next(e for e in y['raw']['candidate_events'] if e['accepted'])['accepted_public_elapsed']=-1
 if kind=='first_late_acceptance':
  e=next(e for e in y['raw']['candidate_events'] if e['accepted'] and e['stage']=='local');e['accepted_public_elapsed']=.6;e['decision_public_elapsed']=.6
 if kind=='module_hash':next(iter(y['loaded_modules'].values()))['sha256']='UNKNOWN'
 reject(kind,lambda:check_result(j,y,pr['protected_hashes']))
reject('duplicate_run_id',lambda:check_unique([j,j]))
bad=dict(j,case_sha256='BAD');job=D/'worker_failure.job.json';dest=D/'worker_failure.result.json';job.write_text(json.dumps(bad),encoding='utf-8');run=subprocess.run([sys.executable,'-B','-X','utf8',str(D/'experiment.py'),'worker',str(job),str(dest)],capture_output=True,text=True);assert run.returncode==1 and read(dest)['worker_status']=='exception'
(D/'checker_and_worker_fixtures.json').write_text(json.dumps(dict(status='PASS',detected=checks,real_cli_failure_saved=True,before_solver=True,planner_calls=0),indent=2),encoding='utf-8');print('PASS negative audit and worker fixtures; solver calls 0')
