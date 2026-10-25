from common import H,ROOT
from isolation import install
from pathlib import Path
import json
allowed=H/'technical/probe_crop.json'
counts,paths=install(H,allowed)
assert json.loads(allowed.read_text(encoding='utf-8'))=={'saved_prefix_only':True}
blocked=[]
for p in (ROOT/'当前进度与下一步.md',ROOT/'障碍后正反例任务次序与收尾结构对照_v0.1_20261023/pair_index.json',H/'outputs/fake_truth.json',H/'source_guards.json'):
 try:p.read_bytes();raise AssertionError('leak permitted')
 except PermissionError:blocked.append(str(p))
assert counts['blocked_reads']==4
print(json.dumps(dict(passed=True,counts=counts,blocked=blocked),ensure_ascii=False))
