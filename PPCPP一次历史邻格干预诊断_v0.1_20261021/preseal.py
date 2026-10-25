"""Inventory warm imports without entering any planner; then seal before stubs/entries."""
from probe_common import *
import sys,subprocess,os,datetime,ast
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');files=read(S/'formal_seal.json')
inventories=[]
for mode in ('FROZEN','OFF'):
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),'inventory',mode],env=env,capture_output=True,check=True);x=json.loads(p.stdout);inventories.append(dict(mode=mode,**x))
    for path in x['paths']:files[path]=sha(path)
save(H/'import_inventory.json',inventories)
for folder in (H,R/'复杂障碍覆盖顺序分歧只读诊断_v0.1_20261021',R/'复杂障碍覆盖顺序分歧负责人审核_20261021'):
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:files[str(p.resolve())]=sha(p)
for p in (R/'PPCPP一次历史邻格干预诊断执行稿_给sol_20261021.md',Path(sys.executable),M/'metrics.py',M/'crosscheck.py'):files[str(p.resolve())]=sha(p)
with (H/'运行前根进度快照.md').open('x',encoding='utf8') as f:f.write((R/'当前进度与下一步.md').read_text(encoding='utf8'))
files[str(H/'运行前根进度快照.md')]=sha(H/'运行前根进度快照.md')
assert not (H/'actual_order.jsonl').exists() and not (H/'stub_results.json').exists()
save(H/'preseal.json',dict(complete=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,python_executable_sha256=sha(sys.executable),environment_threads={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},true_entries_before_seal=0,real_core_calls_before_seal=0))
print('PRESEALED',len(files),'source/environment/input files; zero real entries/cores so far')
