from common import *
from call import call
def main():
 protect();assert read(H/'gate_index.json')['passed'];valid={r['id'] for r in read(H/'input_audit.json') if r['status']=='valid'};jobs=[]
 for rep in read(H/'protocol.json')['repetitions']:
  for i,s in enumerate(read(H/'protocol.json')['slots']):
   if s['id'] not in valid:continue
   for method in (('PPCPP','LAST') if (i+rep)%2==0 else ('LAST','PPCPP')):
    name=f"{s['id']}__r{rep}__{method}";x=call(H/'inputs'/f"{s['id']}.json",H/'execution'/f'{name}.json',method,s['id'],'formal',rep);jobs.append(x['job'])
    if x.get('technical_failure'):save(H/'STOPPED.json',dict(reason='technical_failure_stop',job=x['job']));raise RuntimeError(x)
    print(len(jobs),name,x['raw']['status'],flush=True)
 protect();save(H/'completion.json',dict(completed=True,calls=len(jobs),jobs=jobs));print('fixed matrix finished; STOP',flush=True)
if __name__=='__main__':main()
