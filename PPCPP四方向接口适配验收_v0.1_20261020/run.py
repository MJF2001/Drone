import os,subprocess
from common_orient import *
from environment import verify
from audit_orient import semantics,check
def main():
 verify();assert read(H/'pure_tests.json')['passed'];outputs={};records=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');inputs={i['id']:i for i in read(H/'protocol.json')['inputs']}
 for row in read(H/'order.json'):
  name=f"{row['sequence']:03d}__{row['stage']}__{row['id']}__{row['mode']}__{row['degree']}";dest=H/'execution'/(name+'.json');jobpath=H/'jobs'/(name+'.json');assert not dest.exists();j=dict(**row,input_sha256=sha(row['input']),seal_sha256=sha(H/'environment_seal.json'),budget=20,seed=20261020);save(jobpath,j);dest.parent.mkdir(exist_ok=True)
  try:
   with dest.with_suffix('.log').open('x',encoding='utf-8') as f:
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jobpath),str(dest)],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90)
    if p.returncode:raise RuntimeError(('worker failed',p.returncode))
   x=read(dest);assert x['status']==row['expected'],(name,x['status'],x['exception']);outputs[row['id'],row['mode'],row['degree']]=x
   if row['expected']=='core_complete':assert x['eligible'];check(read(row['input']),x)
   else:assert x['exception']['type']=='ValueError' and not x['raw']['route']
   if row['stage']=='B1' and row['mode']=='NEW' and row['degree']==0:
    assert semantics(x['raw']['candidates'][0]['raw'])==semantics(outputs[row['id'],'OLD',0]['raw']['candidates'][0]['raw'])
    golden=read(inputs[row['id']]['golden'])['raw']['branches']['P0'];assert semantics(x['raw']['candidates'][0]['raw'])==semantics(golden)
   if row['stage']=='B3':
    for cand in x['raw']['candidates']:assert semantics(cand['raw'])==semantics(outputs[row['id'],'NEW',cand['degree']]['raw']['candidates'][0]['raw'])
  except Exception as exc:
   save(H/'STOPPED.json',dict(job=j,reason=repr(exc),completed_entries=len(records),entry_may_have_run=True));raise
  records.append(dict(**row,status=x['status'],entry_seconds=x['entry_seconds'],core_calls=x['core_calls'],output=str(dest.relative_to(H))))
  with (H/'actual_order.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(records[-1],ensure_ascii=False)+'\n')
  if row['sequence']%15==0:print(row['sequence'],'/285',name,flush=True)
 verify();save(H/'completion.json',dict(completed=True,entries=len(records),real_core_calls=sum(r['core_calls'] for r in records),records=records));print('FIXED GATES COMPLETE; STOP NO FORMAL')
if __name__=='__main__':main()
