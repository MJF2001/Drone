import subprocess,sys,os
from common import *
def call(cpath,dest,method,case_id,phase,rep=0):
 dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():return read(dest)
 source=read(H/'protocol.json')['reused'];j=dict(id=dest.stem,case_id=case_id,phase=phase,method=method,repetition=rep,seed=20261020+rep,budget=20,input=str(Path(cpath).resolve()),input_sha256=sha(cpath),production_hashes={k:v['sha256'] for k,v in source.items() if k in ('candidate.py','runtime.py','worker.py')})
 job=H/'jobs'/phase/(dest.stem+'.json');save(job,j)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
 with dest.with_suffix('.log').open('x',encoding='utf-8') as log:
  try:
   p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(job),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   if p.returncode:save(dest,dict(job=j,technical_failure=True,returncode=p.returncode))
  except subprocess.TimeoutExpired:save(dest,dict(job=j,technical_failure=True,reason='watchdog_90s'))
 return read(dest)
