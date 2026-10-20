from pathlib import Path
import sys,json,hashlib,subprocess,tempfile
import verify as v
D=Path(__file__).resolve().parent
checks=[]
def rejects(name,func):
 try:func()
 except (AssertionError,KeyError):checks.append(name);return
 raise AssertionError('tamper not detected: '+name)
old=[[0,0],[1,0],[2,0],[1,0],[0,0]];patch=old[1:4]
v.check_core(old,1,3,[[2,0]],old,patch)
rejects('local_goal_omission',lambda:v.check_core(old,1,3,[[2,0]],old,[[1,0]]))
rejects('fixed_suffix_change',lambda:v.check_core(old,1,3,[[2,0]],old[:-1]+[[9,9]],patch))
rejects('duplicate_success_run_id',lambda:v.check_unique([{'run_id':'x'},{'run_id':'x'}]))
case=D/'worker_failure_fixture.json';case.write_text('{}',encoding='utf-8')
j={'run_id':'worker_failure_fixture','case':str(case),'case_sha256':hashlib.sha256(case.read_bytes()).hexdigest(),'method':'RANGE_SEED','budget':1,'seed':0}
x={'job':dict(j,case_sha256='0'*64),'worker_status':'returned'}
rejects('input_hash',lambda:v.check_result(x['job'],x))
with tempfile.TemporaryDirectory() as td:
 td=Path(td);f=td/'unknown_source.py';f.write_text('changed',encoding='utf-8');(td/'preflight_protocol.json').write_text(json.dumps({'protected_hashes':{str(f):'0'*64}}),encoding='utf-8')
 previous=v.D;v.D=td
 try:rejects('unknown_protected_source_change',lambda:v.main('preflight'))
 finally:v.D=previous
jobfile=D/'worker_failure_fixture.job.json';jobfile.write_text(json.dumps(j),encoding='utf-8');dest=D/'worker_failure_fixture.result.json'
r=subprocess.run([sys.executable,'-B','-X','utf8',str(D/'experiment.py'),'worker',str(jobfile),str(dest)],capture_output=True,text=True)
assert r.returncode==1 and json.loads(dest.read_text(encoding='utf-8'))['worker_status']=='exception'
checks.append('worker_exception_saved_before_solver')
(D/'checker_fixture_results.json').write_text(json.dumps({'status':'PASS','checks':checks,'optimizer_calls':0,'worker_pre_solver_failure_attempts':1},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','checks':checks}))
