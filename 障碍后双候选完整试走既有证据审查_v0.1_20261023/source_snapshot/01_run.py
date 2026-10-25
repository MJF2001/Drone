from common import *
import subprocess,traceback
from qualify import prepare_states
from analysis_metrics import pair
def freeze():
 excluded={'active_freeze.json','status.json','current_job.json'}
 return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and p.name not in excluded and (p.suffix=='.py' or p.is_relative_to(H/'protocol') or p.is_relative_to(H/'inputs') or p.name in ('plan.json','prechecks.json','source_guards.json','runtime_guards.json','environment.json','01_有效协议与四项修正.md','02_实际调用计划.md'))}
def launch(job,status):
 assert job['id'] not in status['attempted'];status['attempted'].append(job['id']);dump(H/'current_job.json',job);dump(H/'status.json',status)
 before=time.perf_counter();append(H/'attempts.jsonl',dict(event='started',id=job['id'],arm=job['arm'],input=job['input'],utc=time.time()))
 env=dict(os.environ,**read(H/'plan.json')['thread_env'],PYTHONDONTWRITEBYTECODE='1')
 try:
  proc=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'current_job.json')],env=env,capture_output=True,timeout=150)
  (H/'logs'/(job['id']+'.log')).write_bytes(proc.stdout+proc.stderr)
  x=read(H/'outputs'/(job['id']+'.json'))
  if proc.returncode and not x.get('semantic_error'):x.update(semantic_error=True,status='worker_exit_error')
 except subprocess.TimeoutExpired as ex:
  (H/'logs'/(job['id']+'.log')).write_bytes((ex.stdout or b'')+(ex.stderr or b''));x=read(H/'outputs'/(job['id']+'.json')) if (H/'outputs'/(job['id']+'.json')).exists() else dict(job=job)
  x.update(passed=False,eligible=False,status='parent_timeout',semantic_error=False);dump(H/'outputs'/(job['id']+'.json'),x)
 x['parent_wall_seconds']=time.perf_counter()-before;dump(H/'outputs'/(job['id']+'.json'),x)
 status['completed'].append(dict(id=job['id'],arm=job['arm'],status=x['status'],eligible=x['eligible']))
 append(H/'attempts.jsonl',dict(event='ended',id=job['id'],arm=job['arm'],status=x['status'],eligible=x['eligible'],parent_wall_seconds=x['parent_wall_seconds']))
 dump(H/'status.json',status);print('ENTRY',job['id'],x['status'],'eligible='+str(x['eligible']),flush=True)
 if x.get('semantic_error'):raise RuntimeError('substantive error; stop no repair/retry: '+job['id'])
 return x
def run():
 assert read(H/'prechecks.json')['passed'] and not (H/'entry_log.jsonl').exists() and not (H/'status.json').exists()
 dump(H/'active_freeze.json',freeze());status=dict(attempted=[],completed=[],failure=None,stage='history',responses=[],pairs=[])
 plan=read(H/'plan.json');dump(H/'status.json',status)
 try:
  for m in plan['maps']:
   launch(dict(id='history__'+m['id'],arm='history',input='inputs/history__'+m['id']+'.json',base_geometry=m['id'],family=m['family']),status)
  status['stage']='qualification';dump(H/'status.json',status);registry=prepare_states()
  # Freeze all E and all failed slots before the first response can run.
  dump(H/'qualification_freeze.json',{str(p.relative_to(H)):sha(p) for p in list((H/'qualification').glob('*.json'))+list((H/'history').glob('*.json'))+[H/'state_registry.json']+list((H/'inputs').glob('*.json'))})
  status['stage']='response';dump(H/'status.json',status);b=bindings()
  for row in registry:
   sr=dict(id=row['id'],qualification=row['status'],arms={});status['responses'].append(sr)
   if row['status']!='qualified':sr['reason']='not_qualified';continue
   common=dict(input=row['input'],base_geometry=row['base_geometry'],family=row['family'],old_order=row['old_order'])
   refid=row['id']+'__REF';ref=launch(dict(common,id=refid,arm='REF'),status);sr['arms']['REF']=ref['status']
   if not ref['eligible']:sr['reason']='REF_not_eligible';continue
   if ref['scanner']['status']!='applicable':sr['reason']=ref['scanner']['status'];continue
   off=launch(dict(common,id=row['id']+'__OFF',arm='OFF',reference_id=refid),status);sr['arms']['OFF']=off['status']
   if not off['eligible']:sr['reason']='OFF_not_eligible';continue
   alt=launch(dict(common,id=row['id']+'__ALT1',arm='ALT1'),status);sr['arms']['ALT1']=alt['status']
   if not alt['eligible']:sr['reason']='ALT1_not_eligible';continue
   result=pair(row,off,alt,b);status['pairs'].append(result);sr['reason']='valid_pair';dump(H/'pairs.json',status['pairs']);dump(H/'status.json',status)
  status['stage']='finite_batch_ended'
 except BaseException as ex:status.update(stage='stopped',failure=dict(reason=repr(ex),traceback=traceback.format_exc()))
 finally:
  dump(H/'status.json',status);dump(H/'pairs.json',status['pairs']);print('FIXED BATCH ENDED; NO RETRIES OR ADDITIONAL CANDIDATES',status['stage'],flush=True)
if __name__=='__main__':run()
