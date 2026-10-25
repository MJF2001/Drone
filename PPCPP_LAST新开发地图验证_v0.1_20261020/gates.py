from common import *
from call import call
from input_audit import audit_all
def main():
 protect();assert read(H/'preflight.json')['passed'];rows=audit_all();assert rows==read(H/'input_audit.json');assert (H/'novelty.json').exists();gates=[]
 for s in rows:
  if s['status']!='valid':continue
  cpath=H/'inputs'/f"{s['id']}.json";c=read(cpath);outs={}
  for method in ('PPCPP','ONE'):
   x=call(cpath,H/'gates'/f"{s['id']}__{method}.json",method,s['id'],'gate');assert not x.get('technical_failure') and x['eligible'],(s['id'],method)
   pa.audit(c,x['raw']['branches']['P0']);assert metric(c,x['raw']['route'])==cross(c,x['raw']['route']);outs[method]=x
   assert sha(cpath)==x['job']['input_sha256'];gates.append(x['job'])
  for k in ('route','trace'):assert outs['PPCPP']['raw'][k]==outs['ONE']['raw'][k],s['id']
  print('ONE equivalent',s['id'],flush=True)
 save(H/'gate_index.json',dict(passed=True,calls=len(gates),states=len(gates)//2,jobs=gates))
 save(H/'input_seal.json',{str(p.relative_to(H)):sha(p) for folder in ('inputs','witnesses','prep','gates') for p in (H/folder).rglob('*') if p.is_file()}|{n:sha(H/n) for n in ('protocol.json','preflight.json','input_audit.json','novelty.json','gate_index.json')})
 files={str(p.relative_to(H)):sha(p) for p in H.glob('*.py')};files.update({n:sha(H/n) for n in ('protocol.json','input_seal.json','预登记.md')})
 save(H/'source_seal.json',dict(files=files,phase='after all new-input gates; before formal calls'))
 print('all new-input gates passed; input/source sealed',len(gates),flush=True)
if __name__=='__main__':main()
