import subprocess
from diag_common import *
def main():
 assert read(D/'positive_index.json')['passed'];records=[]
 for fam,item in read(D/'selection.json')['selected'].items():
  if not item:continue
  source=D/'exact_inputs'/(fam+'.json');results={}
  for method in ('exact_bfs','exact_dijkstra'):
   dest=D/'exact_outputs'/(fam+'_'+method+'.json');dest.parent.mkdir(exist_ok=True)
   with dest.with_suffix('.log').open('x',encoding='utf-8') as f:
    try:
     p=subprocess.run([sys.executable,'-B','-X','utf8',str(D/(method+'.py')),str(source),str(dest)],stdout=f,stderr=subprocess.STDOUT,timeout=60)
     if p.returncode:raise RuntimeError(p.returncode)
    except Exception as e:
     if not dest.exists():save(dest,dict(status='unresolved',reason=repr(e)))
   results[method]=read(dest)
  if all(r['status']=='optimal' for r in results.values()):assert results['exact_bfs']['length']==results['exact_dijkstra']['length']
  records.append(dict(family=fam,id=item['id'],results=results))
 save(D/'exact_index.json',dict(calls=2*len(records),records=records));print('Exact complete',len(records),'cases,',2*len(records),'bounded solves')
if __name__=='__main__':main()
