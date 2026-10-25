"""Only the registered 16 previously unexecuted entries, no retry."""
from region_common import *
import subprocess,traceback
def launch(j):
 start=time.perf_counter();dest=H/'outputs/worker'/(j['id']+'.json');assert not dest.exists();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
 try:
  cp=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/(j['id']+'.json'))],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=150)
  row=dict(id=j['id'],parent_seconds=time.perf_counter()-start,returncode=cp.returncode,stdout=cp.stdout,stderr=cp.stderr,parent_late=time.perf_counter()-start>150);dump(H/'outputs/parent'/(j['id']+'.json'),row);print(cp.stdout.strip(),flush=True)
  assert dest.exists(),'missing worker evidence';r=read(dest)
  if cp.returncode or r.get('semantic_error') or not r['passed']:raise RuntimeError('technical/completeness stop '+j['id']+' '+str(r.get('failure',r['status'])))
  return r
 except subprocess.TimeoutExpired as e:
  dump(H/'outputs/parent'/(j['id']+'.json'),dict(id=j['id'],status='parent_timeout',seconds=time.perf_counter()-start,stdout=str(e.stdout),stderr=str(e.stderr)));raise RuntimeError('parent timeout; no retry')
def run():
 assert not (H/'run_status.json').exists();assert read(H/'regression_receipt.json')['passed'] and read(H/'old_review_receipt.json')['passed'];guard();plan=read(H/'plan.json');out=dict(status='running',completed_jobs=[],attempted_jobs=[],automatic_retry=False,new_engineering_repairs_after_first_core=0)
 try:
  for n,j in enumerate(plan['jobs']):
   out['attempted_jobs'].append(j['id']);r=launch(j);out['completed_jobs'].append(j['id']);dump(H/'control'/('progress_'+str(n+1).zfill(2)+'.json'),out)
  out.update(status='fixed_remaining_batch_complete')
 except BaseException as e:out.update(status='stopped_technical_error',failure=repr(e),traceback=traceback.format_exc())
 finally:dump(H/'run_status.json',out);print('STOP',out['status'],flush=True)
if __name__=='__main__':run()
