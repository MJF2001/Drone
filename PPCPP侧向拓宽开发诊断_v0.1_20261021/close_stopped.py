"""Seal actual pre-entry stop and preserve root progress history."""
from common import *
import sys,datetime
if sys.argv[1]=='prepare':
    with (H/'停止前根进度快照.md').open('xb') as f:f.write((R/'当前进度与下一步.md').read_bytes())
    save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','stopped_verify.log','verification_receipt.json','completion_manifest.json')});print('Stopped-package manifest prepared; original first-sealed code unchanged.')
else:
    log=(H/'stopped_verify.log').read_text(encoding='utf8');assert log.rstrip().endswith('new planner/core/graph calls=0.') and 'ALL PASS STOPPED PACKAGE ONLY' in log
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    save(H/'verification_receipt.json',dict(status='ALL_PASS_STOPPED_PACKAGE_ONLY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verify_script='verify_stopped.py',verify_log_sha256=sha(H/'stopped_verify.log'),verified_manifest_sha256=sha(H/'manifest.json'),first_seal_sha256=sha(H/'seal1.json'),real_entries=0,real_core_calls=0,pure_statistic_stubs=8,hypothesis_result='NOT_TESTED',new_verify_graph_calls=0))
    entry='''# 最新停止：侧向拓宽固定批启动前统计模块语法错误，真实入口0（2026-10-21）

已建立PPCPP侧向拓宽开发诊断_v0.1_20261021，八项纯统计桩全部通过、一次冷导入无求解，第一阶段seal1封存10242来源/环境/代码及6份初始输入；冻结原件未改，字节参考保留。启动六次历史准备时，run.py导入analysis.py遇CSV导出字典语法错误，未进入main、未启动worker，actual_order不存在。只读AST扫描另定位verify.py的同型潜在语法错误；执行方漏做全源码解析检查，桩通过不能证明调度链有效。

按稿技术异常立即停，未修改封存程序、未重新封存接着跑、未重试或创建后继版。真实入口0/306、核心0，6准备/12门槛/288正式全部未运行；实际历史0、前缀0、位置候选表0、事件输入0、第二seal未创建，不能把固定48计划当已生成验证。侧向位置假设/有限继续信号均NOT_TESTED，不作无收益或算法结论。

原代码/首次seal/失败prep_execution.log、syntax_findings、306未运行槽位、调用账和准备停止报告保留。停止包专用verify_stopped实际通过来源hash/冻结字节/六初始几何/8桩/语法缺陷/未运行账，stopped_verify.log及verification_receipt保留；不等于完成实验核验。普通图搜索/覆盖精确/P2/LAST/四方向/干预/留出新增均0。根目录计划与旧证据不覆盖，封存待负责人决定后继修复，不自动继续运行，不提交推送Git。入口为本目录准备停止报告.md及review_packet.md。

---

'''
    p=R/'当前进度与下一步.md';old=p.read_text(encoding='utf8');assert not old.startswith('# 最新停止：侧向拓宽固定批启动前')
    with p.open('wb') as f:f.write((entry+old).encode('utf8'))
    with (H/'停止后根进度快照.md').open('xb') as f:f.write((entry+old).encode('utf8'))
    save(H/'completion_manifest.json',dict(files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='completion_manifest.json'},note='Main manifest excludes actual stopped verify log/receipt to avoid self reference; completion scope includes main manifest/log/receipt and root progress snapshots, excludes only itself.'))
    for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    print('SEALED PRE-ENTRY STOP; root progress prepended with history retained. Real entries0/306; hypothesis NOT_TESTED; awaiting review.')
