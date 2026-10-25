"""Single fresh immutable preseal; reuse v0.4 byte-reference contract."""
from common import *
from reference_contract import references
import subprocess,sys,os,datetime
def main():
    require('technical');require('action_stubs');assert not (H/'actual_order.jsonl').exists();assert not (H/'preseal.json').exists();plan()
    files=read(B/'seal2.json')['files'];save(H/'reference_validation.json',references(P,H/'frozen_source_bytes',files))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory'],env=env,capture_output=True,check=True);inventory=json.loads(p.stdout);save(H/'import_inventory.json',inventory)
    for n in inventory['paths']:
        if n in files:assert sha(n)==files[n],('inherited_drift',n)
        files[n]=sha(n)
    for p in H.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name!='actual_order.jsonl' and not (p.parent==H and p.name.endswith('_execution.log')):files[str(p.resolve())]=sha(p)
    critical={str((H/n).resolve()):sha(H/n) for n in ('runtime.py','candidate.py','native_diag.py','intervention.py','common.py','decision_audit.py','worker.py','run.py')}
    runtime_native_source=inventory['reward_tools'];critical[str(Path(runtime_native_source))]=sha(runtime_native_source)
    save(H/'preseal.json',dict(complete=True,binding=binding(),files=files,critical=critical,entry_identifier=LABEL,python_sha256=sha(sys.executable),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),entry_cap=288,entry_budget=20,watchdog=90,threads=1))
    receipt('preseal',[H/'preseal.json']);print('PASS fresh preseal',len(files),'files; no real entries yet',flush=True)
if __name__=='__main__':main()
