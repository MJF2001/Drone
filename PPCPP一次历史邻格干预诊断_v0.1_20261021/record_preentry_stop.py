"""Record an observed preparation failure without retrying or entering a solver."""
from probe_common import *
import datetime,ast
original=P/'candidate.py';copy=H/'candidate.py';a=original.read_bytes();b=copy.read_bytes()
assert a!=b and a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n')
assert not (H/'actual_order.jsonl').exists() and not (H/'stub_results.json').exists() and not list((H/'outputs').glob('*'))
failure=dict(stage='pre-entry static preparation',code='CANDIDATE_BYTE_COPY_MISMATCH',original=str(original),copy=str(copy),original_sha256=sha(original),copy_sha256=sha(copy),original_bytes=len(a),copy_bytes=len(b),original_CRLF=a.count(b'\r\n'),copy_CRLF=b.count(b'\r\n'),LF_normalized_equal=True,AST_equal=ast.dump(ast.parse(a.decode('utf8')),include_attributes=False)==ast.dump(ast.parse(b.decode('utf8')),include_attributes=False),cause='prepare_copies.py read_text/open(text) on Windows converted 57 LF newlines to CRLF; original unchanged',observed_before_real_entries=True,preseal_was_created_after_false_flag=True,impact='Byte identity promised by protocol/verify fails. No behavioral change established; no experiment or efficacy conclusion. No automatic correction or retry.')
save(H/'preentry_static_failure.json',failure);save(H/'failures.json',[failure])
pending=[dict(**j,status='NOT_RUN',reason='stopped_pre_entry_on_static_byte_copy_mismatch') for j in read(H/'fixed_order.json')];save(H/'unrun_slots.json',pending);csvsave(H/'24未运行槽位.csv',pending)
save(H/'stub_not_run.json',dict(planned=8,executed=0,reason='static preparation failed before stub gate'))
save(H/'STOP.json',dict(status='STOPPED_PRE_ENTRY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=failure['code'],true_entries=0,real_core_calls=0,formal_pairs=0,stub_checks_executed=0,unrun_slots=24,corrected_version_created=False,automatic_retry=False,algorithm_hypothesis_verdict='NOT_TESTED',responsible_review_required=True))
save(H/'call_ledger.json',dict(real_entries=0,real_core_calls=0,gate_entries=0,formal_entries=0,planned_entry_cap=24,unrun_entries=24,stub_checks=0,cold_import_inventory_processes=2,cold_import_inventory_real_entries=0,upstream_readonly_verify_runs=1,upstream_ordinary_full_BFS=16,upstream_ordinary_full_Dijkstra=16,this_preparation_new_graph_distance_searches=0,P2_calls=0,LAST_calls=0,four_direction_calls=0,coverage_exact_searches=0,candidate_action_enumeration=0,holdout_uses=0,extra_maps=0,retries=0,technical_preparation_failures=1))
report='''# 一次历史邻格干预：准备阶段技术停止，未启动实验

本版在真实入口之前停止。不是“干预无效”，也没有产生原版/处理版比较结果。真实入口0/24、真实核心0、固定桩0/8；12关闭等价入口与12正式入口全部未运行。

## 已完成的准备

已读当前进度、必读研究定义/冻结说明及执行稿，接受负责人独立文字勘误，旧封存报告不覆盖。实际运行链确认是共同预算runtime→candidate.P0→独立版v0.2 native，早期core仅提供奖励工具。两份原始输入已按字节复制；两条动作固定(5,2)→(5,1)，原previous=(4,2)、原三seed，24顺序槽位已保存。

已准备独立诊断副本、一次pre-loop强制步helper、8项桩夹具、独立逐决策/双指标审核程序、执行器及只读核验代码，但尚未执行桩或任何真实规划入口。冷导入路径清单有两个进程，均未调用solve；不当真实入口。上游order_verify实际全部通过，日志为upstream_verify.log，新增规划0，普通全图BFS16/Dijkstra16另账。

## 静态失败与处理错误

prepare_copies.py用read_text和文本写入复制candidate.py，Windows把57个LF转换为CRLF。原4383字节，副本4440字节；SHA256不同。去掉CRLF差异后字节相同、AST相同，未发现逻辑差别；但本轮协议和verify要求包装副本逐字节一致，因此这一静态条件失败。

准备检查已经输出candidate byte equality False，执行方却把静态检查与preseal置于同一条顺序命令，仍生成了预封存。这是执行处理错误，不能说静态门槛已通过或封存代表有效性验收。观察到该问题后未运行桩、等价入口、正式入口或动作干预，未改封存代码来绕过失败。

原冻结文件没有被修改。具体hash、字节/换行数和AST比较在preentry_static_failure.json；初版副本、minimal.diff及含10511来源文件的preseal.json保留，不覆盖成首次即成功。与换行不同有关的candidate diff文本为空是因为diff基于规范化文本，不代表原始字节相同。

## 停止裁决与影响

执行稿第7节要求“技术异常立即停并保留所有已运行结果；未运行槽位明确标记。若需修正另立版本并交负责人裁决”，故本版停止，不自动修完再跑。24未运行槽位.csv及unrun_slots.json逐项保存；stub_not_run.json明确八项桩未执行。没有正式路线、双指标成绩、转弯/耗时比较或两状态正反图，均为未运行，不用0步补值。

只读verify.py是原计划的实验核验器，当前条件不满足，未执行；verify_stopped.py专用于本次停止包，检查原/副本来源hash、两输入/动作/固定槽位、无真实结果与调用账，不导入planner或生成路线。核验是否成功以verify.log和verification_receipt.json为准。停止包manifest和日志保留。

如需继续，应另立后继版，在不修改本版的前提下将要求字节相同的包装文件改为二进制复制，并在封存前用会真正中止流程的断言校验。该修正尚未实施，后继实验尚待负责人裁决；原24上限未使用不能视作自动获准重跑。

本次未检验单步是否有效，不支持或否定历史邻格假设，不构成算法收益或在线改进结论。根进度记录准备阶段停止，保留旧计划/历史；不追加动作、候选、地图、奖励或留出，不提交推送Git。
'''
with (H/'通俗报告_准备阶段停止.md').open('x',encoding='utf8') as f:f.write(report)
with (H/'review_packet.md').open('x',encoding='utf8') as f:f.write('# 停止包审核入口\n\n先读通俗报告_准备阶段停止.md、preentry_static_failure.json和STOP.json。0/24真实入口、0核心、0/8桩；不是干预无效。原件不变、诊断candidate仅LF→CRLF，但违反本版逐字节协议；False检查后仍封存的处理错误明确记录。\n\n本版不修正、不运行原实验verify.py、不自动启动后继。停止包只读核验：\n\n```powershell\n.\\运行环境\\python\\python.exe -B -X utf8 PPCPP一次历史邻格干预诊断_v0.1_20261021/verify_stopped.py\n```\n\n该命令只验hash/静态差异/未运行账，不调规划器。候选源若需二进制复制修正，另立版本交负责人裁决。\n')
print('STOP RECORDED: 0/24 entries, 0 cores, 0/8 stubs; 24 pending slots; no repair/retry')
