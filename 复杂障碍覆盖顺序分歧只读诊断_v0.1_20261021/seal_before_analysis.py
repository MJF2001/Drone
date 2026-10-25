"""Record immutable provenance before first new analysis; no analysis or planners."""
import sys,datetime
from order_common import *
assert not (H/'analysis.json').exists()
sources={}
for folder in (S,T):
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:sources[str(p)]=sha(p)
extra=[R/'复杂障碍覆盖顺序分歧只读诊断执行稿_给sol_20261021.md',MD/'metrics.py',MD/'crosscheck.py',R/'复杂障碍完成位置联合最优负责人审核_20261021/负责人审核结论.md',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py']
for p in extra:sources[str(p)]=sha(p)
save(H/'source_hashes.json',sources)
with (H/'运行前进度快照.md').open('x',encoding='utf8') as f:f.write((R/'当前进度与下一步.md').read_text(encoding='utf8'))
names=['order_common.py','order_analysis.py','seal_before_analysis.py','预登记操作化协议.md','source_hashes.json','运行前进度快照.md','upstream_verify.log']
save(H/'preseal.json',dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={n:sha(H/n) for n in names},executable=sys.executable,executable_sha256=sha(sys.executable),python=sys.version,first_analysis_not_started=True))
print('PRESEALED',len(sources),'source files; first new analysis not started',flush=True)
