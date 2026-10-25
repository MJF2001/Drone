"""Serial registered jobs, no retry, fixed stopping conditions."""
from region_common import *
import subprocess,traceback
def launch(job):
 assert read(H/'prechecks.json')['passed'];start=time.perf_counter();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');p=H/'outputs'/(job['id']+'.json');assert not p.exists()
 try:
  cp=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(H/'jobs'/(job['id']+'.json'))],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=150)
  result=read(p) if p.exists() else {'passed':False,'status':'worker_missing_output','semantic_error':True}
  row={'id':job['id'],'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'parent_seconds':time.perf_counter()-start,'parent_late':time.perf_counter()-start>150,'status':result['status']};dump(H/'logs'/(job['id']+'.json'),row);print(cp.stdout.strip(),flush=True)
  if cp.returncode or result.get('semantic_error'):raise RuntimeError('technical stop '+job['id']+' '+str(result.get('failure',result['status'])))
  return result
 except subprocess.TimeoutExpired as e:
  dump(H/'logs'/(job['id']+'.json'),dict(id=job['id'],status='parent_timeout',parent_seconds=time.perf_counter()-start,stdout=str(e.stdout),stderr=str(e.stderr)));raise RuntimeError('parent timeout; no retry')
def run():
 assert not (H/'run_status.json').exists();plan=read(H/'plan.json');out={'status':'running','completed_jobs':[],'unused_budget_reassigned':False}
 try:
  for j in plan['jobs']:
   if j['phase']=='history':launch(j);out['completed_jobs'].append(j['id']);dump(H/'run_status.json',out)
  from qualify import qualify_all
  rows=qualify_all();bad=[s for s in plan['gate_slots'] if next(r for r in rows if r['id']==s)['status']!='qualified']
  if bad:out.update(status='stopped_fixed_gate_slot_ineligible',failed_gate_slots=bad);return
  for j in plan['jobs']:
   if j['phase']=='equivalence':
    r=launch(j);out['completed_jobs'].append(j['id']);dump(H/'run_status.json',out)
    if not r['eligible']:out.update(status='stopped_equivalence_incomplete_or_late',job=j['id']);return
  qualified={r['id'] for r in rows if r['status']=='qualified'}
  for j in plan['jobs']:
   if j['phase']=='formal' and j['slot'] in qualified:launch(j);out['completed_jobs'].append(j['id']);dump(H/'run_status.json',out)
  out.update(status='fixed_formal_batch_complete',formal_ineligible_slots=sorted(set(s['id'] for s in plan['slots'])-qualified))
 except BaseException as e:out.update(status='stopped_technical_error',failure=repr(e),traceback=traceback.format_exc())
 finally:dump(H/'run_status.json',out);print('STOP',out['status'],flush=True)
if __name__=='__main__':run()
