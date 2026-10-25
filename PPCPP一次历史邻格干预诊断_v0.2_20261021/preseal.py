"""Only after static+two preparation gates; cold inventory, fixed pre-run seal."""
from stage_control import *
import sys,subprocess,os,datetime
require('static');require('prepare_fixtures');assert not (H/'preseal.json').exists() and not (H/'actual_order.jsonl').exists() and not (H/'stub_results.json').exists()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');files=read(S/'formal_seal.json');inventories=[]
for mode in ('FROZEN','OFF'):
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory',mode],env=env,capture_output=True,check=True);x=json.loads(p.stdout);inventories.append(dict(mode=mode,**x))
    for path in x['paths']:
        h=sha(path)
        if path in files:assert h==files[path],('inherited_hash_drift',path)
        files[path]=h
save(H/'import_inventory.json',inventories)
for folder in (H,R/'PPCPP一次历史邻格干预诊断_v0.1_20261021',R/'PPCPP一次历史邻格干预准备停止负责人审核_20261021'):
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            path=str(p.resolve());h=sha(p)
            if path in files:assert h==files[path],path
            files[path]=h
for p in (R/'PPCPP一次历史邻格干预诊断执行稿_给sol_20261021.md',R/'PPCPP一次历史邻格干预v0.2修复接续执行稿_给sol_20261021.md',Path(sys.executable),M/'metrics.py',M/'crosscheck.py'):
    path=str(p.resolve());h=sha(p)
    if path in files:assert h==files[path],path
    files[path]=h
with (H/'运行前根进度快照.md').open('xb') as f:f.write((R/'当前进度与下一步.md').read_bytes())
files[str(H/'运行前根进度快照.md')]=sha(H/'运行前根进度快照.md')
save(H/'preseal.json',dict(complete=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,binding=binding(),critical_source_hashes=read(H/'source_contract.json'),python_executable_sha256=sha(sys.executable),environment_threads={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},true_entries_before_seal=0,real_core_calls_before_seal=0))
receipt('preseal',[H/'preseal.json',H/'import_inventory.json']);print('PASS PRESEALED',len(files),'source/environment/input files after static+2 fixture PASS; real entries/cores=0')
