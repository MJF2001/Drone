import subprocess,sys,os
from common import *
def main():
 protect();assert read(H/'gate_index.json')['passed'] and (H/'source_seal.json').exists();protocol=read(H/'protocol.json');jobs=[]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 for rep in protocol['formal']['repetitions']:
  for i,c in enumerate(protocol['cases']):
   for method in (['PPCPP','LAST'] if (i+rep)%2==0 else ['LAST','PPCPP']):
    name=f"{c['id']}__r{rep}__{method}";out=H/'execution'/f'{name}.json';job=H/'jobs'/f'{name}.json'
    j=dict(id=name,case_id=c['id'],batch=c['batch'],method=method,repetition=rep,seed=20261020+rep,budget=20,input=str(R/c['input']),input_sha256=c['sha256'])
    if not out.exists():
     save(job,j);out.parent.mkdir(exist_ok=True)
     with out.with_suffix('.log').open('x',encoding='utf-8') as log:
      try:
       p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(job),str(out)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
       if p.returncode:save(out,dict(job=j,technical_failure=True,returncode=p.returncode))
      except subprocess.TimeoutExpired:save(out,dict(job=j,technical_failure=True,reason='watchdog_90s'))
    jobs.append(j);print(len(jobs),name,flush=True)
 protect();save(H/'completion.json',dict(completed=True,calls=len(jobs),jobs=jobs));print('360 fixed formal calls complete; STOP',flush=True)
if __name__=='__main__':main()
