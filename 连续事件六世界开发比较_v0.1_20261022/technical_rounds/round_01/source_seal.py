"""Fresh environment/source seal after new hash-bound technical PASS."""
from util import *
from reference_contract import references
import subprocess,sys,datetime
def main():
    config();require('technical');assert not (H/'actual_attempts.jsonl').exists() and not (H/'seal.json').exists()
    files=read(H/'source_lock.json').copy()
    for p,v in files.items():assert sha(p)==v,('inherited_source_drift',p)
    save(H/'reference_validation.json',references(P,H/'frozen_source_bytes',files))
    inventories=[]
    for method in ('PPCPP','P2_MULTI'):
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory',method],env=env(),capture_output=True,check=True);inv=json.loads(p.stdout);inventories.append(inv)
        for f in inv['paths']:
            if f in files:assert sha(f)==files[f],f
            files[f]=sha(f)
    save(H/'import_inventory.json',inventories)
    for p in H.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and not (p.parent==H and p.name.endswith('_execution.log')):files[str(p.resolve())]=sha(p)
    save(H/'seal.json',dict(complete=True,binding=binding(),files=files,critical={str(H/n):sha(H/n) for n in binding()},python_sha256=sha(sys.executable),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),config=config()))
    receipt('seal',[H/'seal.json']);print('PASS new real-interface source seal',len(files),'files; real calls0',flush=True)
if __name__=='__main__':main()
