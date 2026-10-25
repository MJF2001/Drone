"""Two real seals; preserve inherited expected hashes, never rebase drift."""
from common import *
import sys,subprocess,os,datetime
def run(stage):
    require('technical')
    assert stage in (1,2)
    require('stat_stubs')
    if stage==1:
        assert not (H/'actual_order.jsonl').exists();files=read(S/'formal_seal.json');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory'],env=env,capture_output=True,check=True);x=json.loads(p.stdout);save(H/'import_inventory.json',x)
        for path in x['paths']:
            now=sha(path)
            if path in files:assert now==files[path],('frozen_hash_drift',path)
            files[path]=now
        for name in ('runtime.py','candidate.py','p2_adapter.py'):
            source=P/name;target=H/'frozen_source_bytes'/name;target.parent.mkdir(exist_ok=True)
            with target.open('xb') as f:f.write(source.read_bytes())
            assert source.read_bytes()==target.read_bytes()
    else:
        require('generated');require('prep');require('seal1');files=read(H/'seal1.json')['files']
        for p,h in files.items():assert sha(p)==h,p
    for p in H.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ('actual_order.jsonl','seal1_execution.log','seal2_execution.log'):
            path=str(p.resolve());now=sha(p)
            if path in files:assert now==files[path],path
            files[path]=now
    extra=[R/'PPCPP侧向拓宽固定批诊断执行稿_给sol_20261021.md',M/'metrics.py',M/'crosscheck.py',Path(sys.executable),R/'PPCPP场景证据只读整理_20261021/整理结论.md',R/'PPCPP场景证据只读整理_20261021/54状态读取核对.json']
    for p in extra:
        path=str(p.resolve());now=sha(p)
        if path in files:assert now==files[path],path
        files[path]=now
    critical={str(p):sha(p) for p in (P/'runtime.py',P/'candidate.py',P/'p2_adapter.py',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')}
    save(H/f'seal{stage}.json',dict(complete=True,stage=stage,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),binding=binding(),critical=critical,files=files,python_sha256=sha(sys.executable),entry_budget=20,watchdog=90,threads=1,policy='original PPCPP mode and frozen P2 only; no new algorithm'))
    receipt(f'seal{stage}',[H/f'seal{stage}.json']);print('PASS SEAL',stage,len(files),'files',flush=True)
if __name__=='__main__':run(int(sys.argv[1]))
