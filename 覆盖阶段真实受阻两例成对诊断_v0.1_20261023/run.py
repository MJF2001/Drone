from common import *
import importlib.util,sys,os,time,subprocess,traceback
CONTROL=ROOT/'中心区计时插桩影响核查_v0.1_20261022/run_check.py'
spec=importlib.util.spec_from_file_location('_accepted_OFF_control',CONTROL);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);C.H=H
def active():
 return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.suffix=='.py' or p.is_relative_to(H/'inputs') or p.is_relative_to(H/'history') or p.name in ('selection.json','input_freeze.json','source_guards.json','plan.json','bindings.json','prechecks.json','prechecks_preparation_v01_failed.json','preparation_repairs.json','01_固定协议与实现边界.md','environment.json','input_contract.json','prechecks_preparation_v02_failed.json'))}
def worker(j):
 if j['branch']!='R':C.worker(j)
 else:
  import worker_r as W
  for name in ('read','dump','sha','ps','B','evaluate','engine','invoke_once','detail'):setattr(W,name,getattr(C,name))
  W.H=H;W.worker(j)
def run():
 assert read(H/'prechecks.json')['passed'] and not (H/'attempts.jsonl').exists()
 plan=read(H/'plan.json');jobs=plan['jobs'];assert len(jobs)==36
 dump(H/'active_freeze.json',active());env=dict(os.environ,**plan['thread_env'],PYTHONDONTWRITEBYTECODE='1')
 status={'completed':[],'failure':None,'not_run':[],'attempted':[]}
 for i,j in enumerate(jobs):
  status['attempted'].append(j['id']);start=time.perf_counter()
  with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'event':'started','id':j['id'],'branch':j['branch'],'core_slot':int(j['branch']!='R'),'R_slot':int(j['branch']=='R'),'utc_epoch':time.time()})+'\n')
  dump(H/'current_job.json',j)
  try:
   p=subprocess.run([sys.executable,'-B','-X','utf8',str(__file__),'worker',str(H/'current_job.json')],capture_output=True,env=env,timeout=150)
   (H/'logs'/(j['id']+'.log')).write_bytes(p.stdout+p.stderr)
   if p.returncode:raise RuntimeError('worker failed; stop, saved output retained')
   x=read(H/'outputs'/(j['id']+'.json'));assert x['passed'] and x['independent']['passed']
   assert x['entry_ledger']=={'started':1,'returned':1,'exceptions':0};assert x['native_counts_actual'] is None and x['native_observation']['counts'] is None
   if j['branch']=='R':assert x['independent']['repair_structure']['passed']
   status['completed'].append(j['id'])
  except BaseException as e:
   status['failure']={'id':j['id'],'reason':repr(e),'traceback':traceback.format_exc()};status['not_run']=[x['id'] for x in jobs[i+1:]]
  with (H/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'event':'ended','id':j['id'],'success':status['failure'] is None,'parent_wall_seconds':time.perf_counter()-start})+'\n')
  dump(H/'status.json',status);print('COMPLETE' if status['failure'] is None else 'STOP',i+1,'/'+str(len(jobs)),j['id'],flush=True)
  if status['failure']:return
 print('36 FINITE PROCESSING SLOTS COMPLETE; STOP FOR REVIEW',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='worker':worker(read(sys.argv[2]))
 else:run()
