"""Seal stopped preparation, then record actual stop-package verification."""
from probe_common import *
import sys,datetime
if sys.argv[1]=='prepare':
    save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','verify.log','verification_receipt.json','completion_manifest.json')});print('Stopped-package manifest prepared; no solver calls')
else:
    log=(H/'verify.log').read_text(encoding='utf8');assert log.rstrip().endswith('planner=0, graph-distance searches=0.') and 'ALL PASS FOR PRE-ENTRY STOP PACKAGE ONLY' in log
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    save(H/'verification_receipt.json',dict(status='PASS_STOPPED_PACKAGE_ONLY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verify_script='verify_stopped.py',log_sha256=sha(H/'verify.log'),manifest_sha256=sha(H/'manifest.json'),real_entries=0,real_core_calls=0,stub_checks=0,experiment_gate_status='NOT_RUN',hypothesis_verdict='NOT_TESTED',verify_planner_calls=0,verify_graph_searches=0))
    entry='''# 最新停止：一次历史邻格干预诊断在真实入口前因静态复制条件失败停止（2026-10-21）

已建立PPCPP一次历史邻格干预诊断_v0.1_20261021并完成准备，未启动实验：真实入口0/24、核心0、固定桩0/8，12等价/12正式入口全部未运行。冻结原件不改，两份原输入与固定动作/三seed/24槽保留。上游只读order_verify实际全通过（普通全图BFS16/Dijkstra16、新规划0）。

静态发现candidate.py复制由文本读写将57个LF转换为CRLF，原4383字节、副本4440字节；规范化文本和AST相同，但不满足本版承诺的包装文件逐字节一致。执行方已看到False却仍生成preseal，属于准备处理错误；全部原件、最小diff、10511来源预封存、失败与24未运行槽位保留，不覆盖成成功。该问题不是动作假设无效，也没有干预收益、步数、转弯或耗时比较结果。

按执行稿“技术异常立即停…若需修正另立版本并交负责人裁决”停止，未修正或重试，未执行任何桩/真实入口。停止包专用verify_stopped.py实际通过hash/差异/输入动作/未运行账核验，不等于原实验门槛通过；verify.log和verification_receipt.json保留。本轮除上游外新增图距离搜索0，P2/LAST/四方向/覆盖精确/候选枚举/留出/额外动作均0。原实验verify.py未运行，后继版尚未建立或自动启动，待负责人裁决。入口见本目录通俗报告_准备阶段停止.md和review_packet.md。

---

'''
    progress=R/'当前进度与下一步.md';old=progress.read_text(encoding='utf8');assert not old.startswith('# 最新停止：一次历史邻格干预诊断')
    with progress.open('w',encoding='utf8',newline='') as f:f.write(entry+old)
    with (H/'完成后根进度快照.md').open('x',encoding='utf8') as f:f.write(entry+old)
    save(H/'completion_manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='completion_manifest.json'})
    for p,h in read(H/'completion_manifest.json').items():assert sha(H/p)==h,p
    print('SEALED PRE-ENTRY STOP; progress updated with all history retained; 0/24 true entries; awaiting responsible review')
