import os,subprocess,datetime
from support import *
from environment import verify
def main():
 verify();assert read(H/'gate_index.json')['passed'];items={i['id']:i for i in read(H/'protocol.json')['inputs']};order=read(H/'formal_order.json');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
 for row in order:
  name=f"{row['sequence']:03d}__{row['id']}__r{row['repetition']}__{row['method']}";dest=H/'execution'/(name+'.json');jobpath=H/'jobs'/(name+'.json')
  assert not dest.exists() and not jobpath.exists();item=items[row['id']];j=dict(**row,input=item['payload'],input_sha256=item['sha256'],environment_sha256=sha(H/'environment_seal.json'));save(jobpath,j);dest.parent.mkdir(exist_ok=True)
  with dest.with_suffix('.log').open('x',encoding='utf-8') as log:
   try:
    result=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jobpath),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if result.returncode:raise RuntimeError(('worker failure',result.returncode))
   except Exception as e:
    if not dest.exists():save(dest,dict(job=j,technical_failure=repr(e)))
    save(H/'STOPPED.json',dict(job=j,reason=repr(e)));raise
  x=read(dest)
  with (H/'actual_order.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(**row,entry_seconds=x['entry_seconds'],status=x['raw']['status']),ensure_ascii=False)+'\n')
  print(row['sequence'],'/324',row['id'],row['method'],x['raw']['status'],flush=True)
 verify();save(H/'completion.json',dict(completed=True,entries=324));print('FIXED324 COMPLETE; STOP')
if __name__=='__main__':main()
