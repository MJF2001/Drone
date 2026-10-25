import subprocess,os,datetime
from support import *
from environment import verify
def main():
 verify();assert read(H/'gate_index.json')['passed'];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');inputs={i['id']:i for i in read(H/'protocol.json')['inputs']};order=read(H/'formal_order.json');finished=[]
 for row in order:
  name=f"{row['sequence']:04d}__{row['case_id']}__b{row['budget']}__r{row['repetition']}__{row['method']}";dest=H/'execution'/(name+'.json');jobpath=H/'jobs'/(name+'.json')
  if dest.exists():finished.append(read(dest)['job']);continue
  assert not jobpath.exists(),('started job missing output; assessment required',jobpath)
  item=inputs[row['case_id']];assert sha(item['path'])==item['sha256'];job=dict(**row,id=name,input=item['path'],input_sha256=item['sha256'],environment_seal_sha256=sha(H/'environment_seal.json'))
  save(jobpath,job);dest.parent.mkdir(exist_ok=True)
  with dest.with_suffix('.log').open('x',encoding='utf-8') as log:
   try:
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jobpath),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if p.returncode:raise RuntimeError(('worker failure',p.returncode))
   except Exception as exc:
    if not dest.exists():save(dest,dict(job=job,technical_failure=repr(exc)))
    save(H/'STOPPED.json',dict(job=job,reason=repr(exc)));raise
  x=read(dest);finished.append(job)
  with (H/'actual_order.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(**row,id=name,status=x['raw']['status'],entry_seconds=x['entry_seconds'],finished=datetime.datetime.now().astimezone().isoformat()),ensure_ascii=False)+'\n')
  print(row['sequence'],'/972',row['case_id'],row['budget'],row['method'],x['raw']['status'],round(x['entry_seconds'],6),flush=True)
 verify();save(H/'completion.json',dict(completed=True,calls=len(finished)));print('FIXED972 COMPLETE; STOP',flush=True)
if __name__=='__main__':main()
