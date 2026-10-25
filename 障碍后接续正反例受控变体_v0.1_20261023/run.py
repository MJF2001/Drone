from common import *
import subprocess,traceback
from variant_qualify import construct
from analysis_metrics import pair
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
def freeze():
 return {str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and (p.suffix=='.py' or p.is_relative_to(H/'protocol') or p.name in ('plan.json','source_bindings.json','source_guards.json','runtime_guards.json','prechecks.json','01_有效协议与额度.md','setup_receipt.json'))}
def run():
 assert read(H/'prechecks.json')['passed'] and not (H/'entry_log.jsonl').exists() and not (H/'status.json').exists()
 dump(H/'active_freeze.json',freeze());status=dict(attempted=[],completed=[],failure=None,stage='qualification',responses=[],pairs=[]);dump(H/'status.json',status)
 try:
  registry=construct()
  dump(H/'qualification_freeze.json',{str(p.relative_to(H)):sha(p) for p in list((H/'qualification').glob('*.json'))+list((H/'history').glob('*.json'))+list((H/'inputs').glob('*.json'))+[H/'state_registry.json',H/'qualification_ledger.json']})
  jobs=[dict(id=r['id']+'__'+arm,arm=arm,input=r['input'],old_order=r['old_order'],base_geometry=r['base_geometry'],family=r['family']) for r in registry if r['status']=='qualified' for arm in ('REF','OFF','ALT1')]
  dump(H/'response_plan.json',dict(jobs=jobs,core_upper=len(jobs),post_upper=len(jobs),qualified_unique_states=len(jobs)//3,frozen_before_any_response=True,conditional_OFF_ALT=True));qfreeze=read(H/'qualification_freeze.json');qfreeze['response_plan.json']=sha(H/'response_plan.json');dump(H/'qualification_freeze.json',qfreeze);status['stage']='response';dump(H/'status.json',status);b=bindings()
  for row in registry:
   sr=dict(id=row['id'],qualification=row['status'],arms={});status['responses'].append(sr)
   if row['status']!='qualified':sr['reason']=row['status'];continue
   common=dict(input=row['input'],base_geometry=row['base_geometry'],family=row['family'],old_order=row['old_order']);refid=row['id']+'__REF'
   ref=launch(dict(common,id=refid,arm='REF'),status);sr['arms']['REF']=ref['status']
   if not ref['eligible']:sr['reason']='REF_not_eligible';continue
   if ref['scanner']['status']!='applicable':sr['reason']=ref['scanner']['status'];continue
   off=launch(dict(common,id=row['id']+'__OFF',arm='OFF',reference_id=refid),status);sr['arms']['OFF']=off['status']
   if not off['eligible']:sr['reason']='OFF_not_eligible';continue
   alt=launch(dict(common,id=row['id']+'__ALT1',arm='ALT1'),status);sr['arms']['ALT1']=alt['status']
   if not alt['eligible']:sr['reason']='ALT1_not_eligible';continue
   p=pair(row,off,alt,b);status['pairs'].append(p);sr['reason']='valid_pair';dump(H/'pairs.json',status['pairs']);dump(H/'status.json',status)
  status['stage']='finite_batch_ended'
 except BaseException as ex:status.update(stage='stopped',failure=dict(reason=repr(ex),traceback=traceback.format_exc()))
 finally:
  status['not_run']=[s['id']+'__'+a for s in read(H/'plan.json')['slots'] for a in ('REF','OFF','ALT1') if s['id']+'__'+a not in status['attempted']]
  dump(H/'status.json',status);dump(H/'pairs.json',status['pairs']);print('CONTROLLED VARIANT BATCH ENDED; NO ADDITIONS',status['stage'],flush=True)
if __name__=='__main__':run()
