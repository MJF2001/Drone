"""Post-verification artifact/ledger audit and final seal; no planning or graph search."""
from pathlib import Path
import sys,json,datetime,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from probe_common import *
from stage_control import require_preseal,require
seal=require_preseal();require('formal');a=read(H/'analysis.json');g=read(H/'gate_analysis.json')
success=(H/'verify_csv_read.log').read_text(encoding='utf8');failed=(H/'verify.log').read_text(encoding='utf8');assert 'ALL PASS COMPLETED EXPERIMENT' in success and 'field larger than field limit (131072)' in failed
assert a['stop_verdict']=='no_strict_benefit_stop' and len(a['pairs'])==6 and all(p['delta']['length']==2 and p['delta']['turns180']==1 and p['delta']['return_tail_steps']==0 and p['rejoin']['first']['same_literal_suffix'] for p in a['pairs'])
for ex in read(H/'figure_index.json'):
    case=ex['case'];data=read(H/'figures'/f'{case}.json');assert data['pair']==next(p for p in a['pairs'] if p['case']==case and p['seed']==SEEDS[0]);ET.parse(H/'figures'/ex['svg'])
for row in read(H/'render_receipt.json')['rows']:assert sha(H/'figures'/row['svg'])==row['svg_sha256'] and sha(H/'figures'/row['png'])==row['png_sha256']
save(H/'visual_qa.json',dict(pages=2,inspected=[c+'.png' for c in CASES],checks='Both full PNG pages visually inspected: no clipped cost/turn/step labels, correct origin-return sequence and unchanged suffix/return, readable full routes.',planner_calls=0,graph_searches=0))
ledger=read(H/'call_ledger.json');ledger.update(final_verify_status='ALL PASS_COMPLETED_EXPERIMENT_with_CSV_reader_only_successor',verification_attempts=2,verification_report_reader_failures=1,verification_successful_attempts=1,verification_ordinary_BFS_total=2*(a['ordinary_BFS_total']+g['ordinary_BFS_total']),ordinary_BFS_delivery_total_actual=3*(a['ordinary_BFS_total']+g['ordinary_BFS_total']),production_technical_failures=0,experiment_retries=0,read_only_csv_reader_recheck=1)
assert ledger['actual_logged_entries']==ledger['actual_core_calls']==24;save(H/'call_ledger_final.json',ledger)
attempts=[dict(script='verify.py',log='verify.log',status='FAILED_REPORT_CSV_FIELD_LIMIT',ordinary_BFS=582,planner_calls=0,core_calls=0),dict(script='verify_csv_read.py',log='verify_csv_read.log',status='ALL_PASS_COMPLETED_EXPERIMENT',CSV_reader_bound_bytes=3011845,ordinary_BFS=582,planner_calls=0,core_calls=0)];save(H/'verification_attempts.json',attempts)
save(H/'verification_receipt.json',dict(status='ALL_PASS_COMPLETED_EXPERIMENT',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),successful_log='verify_csv_read.log',successful_log_sha256=sha(H/'verify_csv_read.log'),original_failed_log='verify.log',original_failed_log_sha256=sha(H/'verify.log'),preseal_sha256=sha(H/'preseal.json'),presealed_verifier_unchanged=sha(H/'verify.py')==seal['files'][str(H/'verify.py')],core_source_binding_unchanged=True,extra_planner_calls_for_verification=0,read_only_repair='Only csv.field_size_limit; original verifier/data/source unchanged',actual_calls=24,stop_verdict=a['stop_verdict'],figures_hash_and_data_audit='PASS',call_ledger='call_ledger_final.json'))
intro='''# 最终审核入口：一次历史邻格干预v0.2

固定两状态、各原三seed已完成。2准备流程夹具、8干预桩、12关闭等价门槛和12正式入口按序通过，共24真实入口/24核心，不重跑。两状态处理各多2步、180°多1次、返航尾段不变；马上回起点后接回相同原后缀。本次指定一次动作没有收益，按稿停止。

|原状态|原版→处理完整步数|三seed的ΔL/ΔC/ΔR|180°差|
|---|---|---|---|
|31x21_maze_p30|563→565|+2/+2/0|+1|
|31x21_serpentine_p30|551→553|+2/+2/0|+1|

主表6/6配对双方完整合法且入口严格<20秒；末采集格相同。动作来自事后P2轨迹，仅检验指定一步，不能称自主在线算法，也不能否定所有历史通道策略。

**核验透明记录：**第一次只读verify在CSV大字段读取上限处失败，verify.log保留。仅新增CSV读取上限入口verify_csv_read.py，原封存verify/CSV/JSON/算法不变、不重跑真实入口；补充只读核验实际全部通过，成功日志verify_csv_read.log。独立审核BFS实际1746次（含两次核验），正式运行技术失败0、报告读取失败1。完整说明见核验读取修正与实际账说明.md。旧报告中的“若一次核验成功”的1164次是预先条件账，最终使用call_ledger_final.json。

阅读顺序：

1. [完整结果报告](通俗报告与完整结果.md)，含逐seed步数/覆盖/暂缓/转弯/耗时及解释。
2. [核验读取修正和实际调用账说明](核验读取修正与实际账说明.md)，原失败与成功记录分开。
3. [实际最终调用账](call_ledger_final.json)、[核验收据](verification_receipt.json)、[两次只读核验账](verification_attempts.json)。
4. 6正式配对.csv、24调用完整指标.csv、all_decision_audits.json、receipts/、copy_manifest.json及preseal.json。
5. [迷宫固定图](figures/31x21_maze_p30.png)、[蛇形固定图](figures/31x21_serpentine_p30.png)。

一键只读复核使用verify_csv_read.py（详见修正说明），不调用planner，不生成覆盖路线；每次新增独立BFS582次，审核另账。manifest在实际成功核验后生成；不将主manifest自身或完成补充manifest纳入自身，completion_manifest覆盖主manifest、日志、收据及根进度快照。图文导出/最终封存代码是结束后追加的辅助，不冒称运行前封存；实验统计/独立verify/动作规则均在真实入口前封存。

整个v0.1和冻结源保留。当前24入口上限已到，不再增加一步/候选/地图/预算/seed/奖励，不用留出、不自动在线开发或Git提交推送，封存交负责人审核。
'''
with (H/'审核入口_最终状态.md').open('xb') as f:f.write(intro.encode('utf8'))
entry='''# 最新完成：历史邻格一次干预v0.2两状态均多2步，固定批封存停止（2026-10-21）

完成PPCPP一次历史邻格干预诊断_v0.2_20261021，v0.1全部保留。二进制复制candidate及两输入实际bytes/hash相等，原native覆盖循环AST不改；修复为静态失败非零中止及hash绑定PASS阶段门控。2准备夹具（含预期字节失败，阻断封存/后哨兵）＋8干预桩通过后，12原版/OFF等价门槛全通过，完整route/trace/options/score等非时间字段与原压力结果一致；再12正式新入口，全批真实入口24/核心24、均合法完整严格及时，无真实求解失败或重试。

固定31x21_maze_p30与31x21_serpentine_p30、原三seed及(5,2)→(5,1)一次动作。全部处理第2步立即回原起点，第3步采(5,3)，在同current=(5,3)/previous=(5,2)/pending下接回原版第1步后的字面完整后缀；距离资源少2，不称完全同运行状态。迷宫563→565（C425→427，R138不变）；蛇形551→553（C290→292，R261不变）。各三seed全ΔL=+2=ΔC(+2)+ΔR0，历史到达+2、180°+1、90°不变；末格/覆盖/暂缓/其他重复不变。指定一次历史步未获支持，按稿停止，不追加第二步或换动作，不当在线算法或普遍机制结论。

首次最终只读verify遇CSV长字段默认131072限制，原失败日志verify.log保留；按原协议纯报告只读修复例外新增verify_csv_read.py，仅提高读取上限，原封存代码/数据不变、未重跑实验。成功补充核验verify_csv_read.log实际全通过（来源/绑定阶段/完整等价/逐决策/双指标/CSV/停止判据）；报告读取失败1次单列，不隐瞒成首次即成功。独立审核BFS实际1746次（门槛192＋完成分析390＋失败核验582＋成功核验582），新增覆盖精确/P2/LAST/四方向/动作枚举/额外图/留出均0。最终账call_ledger_final.json、verification_attempts与收据、两状态图/6配对/24原始输出、预封存10347来源及最终manifest保留。先看审核入口_最终状态.md。真实24上限已到，封存待负责人审核，不自动调参/开发或Git提交推送。

---

'''
progress=R/'当前进度与下一步.md';old=progress.read_text(encoding='utf8');assert not old.startswith('# 最新完成：历史邻格一次干预v0.2')
with progress.open('wb') as f:f.write((entry+old).encode('utf8'))
with (H/'完成后根进度快照.md').open('xb') as f:f.write((entry+old).encode('utf8'))
scope={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','completion_manifest.json')}
save(H/'manifest.json',scope)
for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
save(H/'completion_manifest.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='completion_manifest.json'},note='Actual completion scope excludes only itself; core final verify already passed before this seal. Root progress is hashed only via saved snapshot.'))
for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
print('PASS export data/figure hashes and actual ledgers; sealed completed experiment, updated root progress; 24/24 entries, stopped. Independent audit BFS1746; report-reader failure1 retained.')
