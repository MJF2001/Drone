from pathlib import Path
import json,subprocess,sys,copy
D=Path(__file__).resolve().parent
from verify import check_result,read,check_unique,check_acceptances,check_selected
pr=read(D/'preflight_protocol.json');j=pr['jobs'][0];x=read(D/'preflight'/(j['run_id']+'.json'));checks=[]
def reject(label,fn):
 try:fn()
 except (AssertionError,ValueError,StopIteration):checks.append(label);return
 raise AssertionError('tamper missed: '+label)
y=copy.deepcopy(x);next(iter(y['loaded_modules'].values()))['sha256']='UNKNOWN';reject('unknown_actual_module_hash',lambda:check_result(j,y,pr['protected_hashes']))
y=copy.deepcopy(x);y['raw']['route']=[y['raw']['route'][0]];reject('omitted_goal',lambda:check_result(j,y,pr['protected_hashes']))
y=copy.deepcopy(x);e=next(e for e in y['raw']['detail']['candidate_events'] if e['accepted']);e['accepted_public_elapsed']=j['budget']+1;reject('late_public_acceptance',lambda:check_result(j,y,pr['protected_hashes']))
reject('duplicate_run_id',lambda:check_unique([j,j]))
reject('wrong_selected_source',lambda:check_selected(dict(selected_candidate_id=0,source='bad',route=[]),[dict(candidate_id=0,accepted=True,source='right',route=[])]))
bad=copy.deepcopy(j);bad['case_sha256']='BAD';job=D/'worker_failure_fixture.job.json';job.write_text(json.dumps(bad),encoding='utf-8');dest=D/'worker_failure_fixture.result.json';cmd=[sys.executable,'-B','-X','utf8',str(D/'experiment.py'),'worker',str(job),str(dest)];run=subprocess.run(cmd,capture_output=True,text=True);assert run.returncode==1 and read(dest)['worker_status']=='exception' and 'AssertionError' in read(dest)['traceback']
(D/'infrastructure_and_checker_fixtures.json').write_text(json.dumps(dict(status='PASS',detected=checks,worker_exception_saved=True,exception_before_solver=True,planning_calls=0,command=cmd,returncode=run.returncode),ensure_ascii=False,indent=2),encoding='utf-8');print('PASS checker and real CLI exception fixtures; solver calls 0')
