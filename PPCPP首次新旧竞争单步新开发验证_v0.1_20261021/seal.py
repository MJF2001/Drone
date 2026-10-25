"""Fresh implementation/environment seal, then actual-input/order seal."""
from common import *
from reference_contract import references
import subprocess,sys,os,datetime
def main(name):
    assert name in ('seal1','seal2');require('technical');require('action_stubs');plan();assert not (H/(name+'.json')).exists()
    if name=='seal1':
        assert not (H/'actual_order.jsonl').exists();files=read(D/'preseal.json')['files'].copy()
        for p,h in files.items():assert sha(p)==h,('inherited_source_drift',p)
        save(H/'reference_validation.json',references(P,H/'frozen_source_bytes',files))
        inventories=[]
        for mode in ('FROZEN','OFF'):
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory',mode],capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'),check=True)
            inv=json.loads(p.stdout);inventories.append(inv)
            for n in inv['paths']:
                if n in files:assert sha(n)==files[n],('inherited_import_drift',n)
                files[n]=sha(n)
        save(H/'import_inventory.json',inventories)
    else:
        require('prep');require('generated');require('inputs_audited');files=check_seal('seal1')['files'].copy()
        for p,h in files.items():assert sha(p)==h,p
    for p in H.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name!='actual_order.jsonl' and not (p.parent==H and p.name.endswith('_execution.log')):files[str(p.resolve())]=sha(p)
    critical={str((H/n).resolve()):sha(H/n) for n in binding()}
    save(H/(name+'.json'),dict(complete=True,binding=binding(),files=files,critical=critical,python_sha256=sha(sys.executable),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan=plan()))
    receipt(name,[H/(name+'.json')]);print('PASS',name,len(files),'fixed files; runtime append logs explicitly separate',flush=True)
if __name__=='__main__':main(sys.argv[1])
