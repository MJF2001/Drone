from common import *
import sys,os,time,subprocess,traceback,importlib.util
CONTROL=ROOT/'中心区计时插桩影响核查_v0.1_20261022/run_check.py'
def worker(j):
 spec=importlib.util.spec_from_file_location('_recovery_diag_accepted_worker_bindings',CONTROL);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 import recovery_diag_worker as W
 for key in ('read','dump','sha','ps','B','evaluate','engine','invoke_once','detail'):setattr(W,key,getattr(C,key))
 W.H=H;W.worker(j)
def freeze():
 return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and not p.is_relative_to(H/'outputs') and not p.is_relative_to(H/'logs') and p.name not in ('active_freeze.json','current_job.json','status.json','attempts.jsonl')}
def run():
 assert read(H/'prechecks.json')['passed'] and not (H/'attempts.jsonl').exists()
 plan=read(H/'plan.json');jobs=plan['jobs'];assert len(jobs)==12
 dump(H/'active_freeze.json',freeze());env=dict(os.environ,**plan['thread_env'],PYTHONDONTWRITEBYTECODE='1')
 status={'completed':[],'attempted':[],'failure':None,'not_run':[],'two_OFF_gate_passed':False}
 for i,j in enumerate(jobs):
  if i==2:assert status['two_OFF_gate_passed'],'two OFF gates required before any ON'
  start=time.perf_counter();status['attempted'].append(j['id']);dump(H/'current_job.json',j)
  with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'event':'started','id':j['id'],'arm':j['arm'],'core':1,'utc':time.time()})+'\n')
  try:
   p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(H/'current_job.json')],capture_output=True,env=env,timeout=150)
   (H/'logs'/(j['id']+'.log')).write_bytes(p.stdout+p.stderr)
   if p.returncode:raise RuntimeError('substantive formal failure; stop with no fix/retry')
   x=read(H/'outputs'/(j['id']+'.json'));assert x['passed'] and x['independent']['passed'] and x['decision_audit']['passed']
   assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0}
   if not j['target_intervention_enabled']:assert x['off_equivalence']['passed']
   status['completed'].append(j['id'])
   if i==1:status['two_OFF_gate_passed']=True
  except BaseException as ex:status['failure']={'id':j['id'],'reason':repr(ex),'traceback':traceback.format_exc()};status['not_run']=[q['id'] for q in jobs[i+1:]]
  with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'event':'ended','id':j['id'],'success':status['failure'] is None,'parent_wall_seconds':time.perf_counter()-start})+'\n')
  dump(H/'status.json',status);print('COMPLETE' if not status['failure'] else 'STOP',i+1,'/12',j['id'],flush=True)
  if status['failure']:break
 print('FINITE BATCH ENDED; NO ADDITIONAL EXPERIMENTS',flush=True)
if __name__=='__main__':worker(read(sys.argv[2])) if sys.argv[1]=='worker' else run()
