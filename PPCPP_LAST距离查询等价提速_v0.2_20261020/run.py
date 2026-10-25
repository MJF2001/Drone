"""Only the 810 preregistered formal calls. Abort on semantic discrepancy."""
import sys,os,subprocess,datetime
from common import *
from semantics import compare,p0_semantic,fingerprint
def stable_fingerprint(raw):
 # Seeds deliberately differ by repetition; seed is an annotation, seed_used=False.
 r=json.loads(json.dumps(raw));b=r.get('branches',{}).get('P0')
 if b:assert b['seed_used'] is False;b['seed']=0
 return fingerprint(r)
def main():
 protect();assert read(H/'gate_index.json')['passed'];assert not (H/'execution').exists()
 order=read(H/'formal_order.json');protocol=read(H/'protocol.json');inputs={i['id']:i for i in protocol['inputs'][:54]};seal=read(H/'source_seal.json');ledger=[];triplets={};stable={};paired=0;p0_pairs=0
 (H/'execution').mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
 for row in order:
  ident=row['case_id'];m=row['method'];rep=row['repetition'];name=f'{ident}__r{rep}__{m}';item=inputs[ident];inp=(H/item['input']).resolve()
  job=dict(**row,id=name,phase='formal',budget=20,input=str(inp),input_sha256=sha(inp),source_seal_sha256=sha(H/'source_seal.json'),production_hashes=seal['actual_sources'][m])
  jpath=H/'jobs'/(name+'.json');dest=H/'execution'/(name+'.json');save(jpath,job)
  started=datetime.datetime.now().astimezone().isoformat();error=None
  with dest.with_suffix('.log').open('x',encoding='utf-8') as log:
   try:
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jpath),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if p.returncode:error=dict(technical_failure=True,returncode=p.returncode)
   except subprocess.TimeoutExpired:error=dict(technical_failure=True,reason='watchdog_90s')
  if error:
   if not dest.exists():save(dest,dict(job=job,**error))
   save(H/'STOPPED.json',dict(reason='technical failure; fixed matrix interrupted',job=job,error=error));raise RuntimeError(error)
  x=read(dest);ledger.append(dict(**row,id=name,output=str(dest.relative_to(H)),started=started,finished=datetime.datetime.now().astimezone().isoformat(),status=x['raw']['status'],eligible=x['eligible']))
  with (H/'actual_order.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(ledger[-1],ensure_ascii=False)+'\n')
  try:
   assert x['runtime_reads']==[str(inp)] and x['production_sources']==job['production_hashes']
   assert x['method']==('PPCPP' if m=='PPCPP' else 'LAST') and x['budget']==20
   group=triplets.setdefault((ident,rep),{});group[m]=x
   if m in ('LAST_V1','LAST_V2') and 'LAST_V1' in group and 'LAST_V2' in group:
    paired+=compare(group['LAST_V1'],group['LAST_V2'])=='equal_complete'
   if x['eligible']:
    token=stable_fingerprint(x['raw']);key=ident,m
    if key in stable:assert stable[key]==token,('repeat instability',key,rep)
    else:stable[key]=token
   if len(group)==3:
    for method in ('LAST_V1','LAST_V2'):
     a=group['PPCPP']['raw']['branches'].get('P0');b=group[method]['raw']['branches'].get('P0')
     if a and b and a['status']==b['status']=='core_complete':assert p0_semantic(a)==p0_semantic(b);p0_pairs+=1
  except Exception as exc:
   save(H/'STOPPED.json',dict(reason='semantic/provenance discrepancy; no remaining calls executed',error=repr(exc),job=job,completed=len(ledger),counterexample_outputs=[f'execution/{ident}__r{rep}__{z}.json' for z in group]));raise
  if len(ledger)%27==0:print('FORMAL',len(ledger),'/810',name,x['raw']['status'],flush=True)
 protect();assert len(ledger)==810
 save(H/'completion.json',dict(completed=True,calls=810,V1_V2_complete_pairs=paired,P0_pairs=p0_pairs,stable_groups=len(stable),actual_order=ledger))
 print('COMPLETE 810; STOP. V1/V2 pairs',paired,'P0 pairs',p0_pairs,'stable groups',len(stable),flush=True)
if __name__=='__main__':main()
