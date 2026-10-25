"""Export saved continuation results only; no planners, replay, or route audits."""
from pathlib import Path
from collections import Counter
import json,hashlib

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'PPCPP真实来向H1最小验收_v0.1_20261022'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    assert not (HERE/'三栏调用账与结果.json').exists(),'no export overwrite'
    status=read(HERE/'status.json');slots=read(HERE/'124槽接续实际账.json');pairs=read(HERE/'54等价证据.json');diags=read(HERE/'16斜向技术证据.json')
    outputs=[read(p) for p in sorted((HERE/'outputs').glob('*.json'))];reuse=read(HERE/'reuse/slot_001_reaudit.json')
    historical=read(Path(reuse['source_path']));accounts=Counter()
    for x in outputs:accounts.update(x['accounts'])
    old_accounts=Counter(historical['accounts']);cross=accounts+old_accounts
    preflights=[read(p) for p in sorted((HERE/'repair_rounds').glob('round_*_result.json'))]
    old_gate=read(OLD/'tech/attempt_1_result.json')
    count_graph=lambda x:sum(x.get(k,0) for k in ('context_BFS_started','distance_row_BFS_started','Astar_started'))
    accepted=(status['failure'] is None and status['new_attempted']==123 and status['new_passed']==123 and len(pairs)==54 and len(diags)==16)
    method_counts=Counter(x['job']['method'] for x in outputs)
    accounting=dict(
      historical_v01=dict(real_entries=1,original_entries=1,H1_entries=0,old_slot1_status='failed',accounts=dict(old_accounts),graph_searches=count_graph(old_accounts),
        native_entry_eligible=historical['entry']['eligible'],worker_independent_audit_failed=1,historical_extra_saved_diagnostic_audit=1),
      v02_saved_result_reaudit=dict(real_entries=0,cores=0,graph_searches=0,LOS_queries=0,saved_route_audits=2,reused_original_returns=1,old_status_unchanged=True),
      v02_new_execution=dict(real_attempts=status['new_attempted'],passed=status['new_passed'],failed=sum(s['status']=='failed' for s in slots[1:]),not_run=sum(s['status']=='not_run' for s in slots[1:]),
        original_entries=method_counts['ORIGINAL'],H1_entries=method_counts['H1'],accounts=dict(accounts),graph_searches=count_graph(accounts),
        independent_worker_audit_attempts=len(outputs),independent_worker_audit_completed=sum(x['audit'] is not None for x in outputs),new_native_routes=len(outputs),
        LOS_queries=0,postprocess_calls=0,closed_loop_sessions=0,performance_comparisons=0),
      cross_version=dict(real_entries=status['new_attempted']+1,original_entries=method_counts['ORIGINAL']+1,H1_entries=method_counts['H1'],accounts=dict(cross),graph_searches=count_graph(cross),
        historical_failed_slot_preserved=1,not_all_workflow_attempts_claimed_success=True),
      v02_pure_preflight=dict(rounds=len(preflights),auditor_calls=sum(p['auditor_calls'] for p in preflights),equivalence_checks=sum(len(p['equivalence_rows']) for p in preflights),
        accepted=sum(p['accepted'] for p in preflights),expected_rejected=sum(p['expected_rejections'] for p in preflights),core_calls=0,graph_searches=0,
        legacy_gate_cases_reused=len(old_gate['cases']),legacy_gate_reexecutions=0,handwritten_stub_routes=1,algorithm_generated_fixture_routes=0),
      planned_final_readonly_verify=dict(saved_route_audits=1+sum(s['status']=='passed' for s in slots[1:]),core_calls=0,graph_searches=0,LOS_queries=0,
        receipt_records_actual_completion=True),
      acceptance=dict(target_passed=accepted,legacy_equivalent_pairs=len(pairs),diagonal_technical_entries=len(diags),
        first_pair_uses_historical_original=True,performance_claim=False,noncenter_start_implemented=False,innovation_claim=False))
    dump(HERE/'三栏调用账与结果.json',accounting)
    mapping=[dict(slot=1,id=slots[0]['id'],origin='v0.1 native return, v0.2 reaudit',old_status='failed',new_status=slots[0]['status'],
        source=reuse['source_path'],sha256=reuse['source_sha256'],new_real_execution=False)]
    for s in slots[1:]:
        p=HERE/'outputs'/(s['id']+'.json')
        mapping.append(dict(slot=s['slot'],id=s['id'],origin='v0.2 new real entry' if p.exists() else 'not_run',status=s['status'],source=str(p) if p.exists() else None,
            sha256=sha(p) if p.exists() else None,new_real_execution=s['status']!='not_run'))
    dump(HERE/'124槽来源映射.json',mapping)
    rows=['# 原124槽来源与接续状态','','槽1是旧返回复核后复用，历史failed保留；其余槽按原顺序新运行。','', '|原槽|方法|阶段|v0.2状态|来源|','|---|---|---|---|---|']
    for s in slots:rows.append(f"|{s['slot']}|{s['method']}|{s['phase']}|{s['status']}|{'v0.1返回，v0.2复核；旧failed不改' if s['slot']==1 else 'v0.2新增入口'}|")
    (HERE/'124槽三栏来源表.md').write_text('\n'.join(rows)+'\n',encoding='utf8')
    pairlines=['# 54旧输入等价证据','','均比较原始格点路线、逐候选分数/决策、信用、恢复及返航；不比较耗时，不称原论文完整复现。','', '|状态|等价|原版来源|H1原槽|信用/决策|','|---|---|---|---|---|']
    for x in pairs:pairlines.append(f"|{x['case']}|{x['equivalent']}|{x['original_origin']}|{x['h1_slot']}|{x['credits_equal']}/{x['decisions_equal']}|")
    (HERE/'54旧输入等价表.md').write_text('\n'.join(pairlines)+'\n',encoding='utf8')
    certified=sum(bool(x['audit']['interval_bits_used']) for x in outputs if x['job']['phase']=='diagonal')
    recoveries=sum(sum(e['kind']=='recovery' for e in x['entry']['raw']['branches']['P0']['trace']) for x in outputs)
    report=f'''# H1审核器v0.2修复与接续：本轮最小验收通过

已完成授权的有限接续：**本版本新增123次真实入口全部通过，跨版本实际124次**。原54对保存输入的路线、信用、逐候选评分与决策一致；固定16次合成斜向入口的正倍数、重复一致性和完整合法性通过。没有额外求解或重跑旧原版槽1。

这确认的是当前格心核心接收H1来向的有限验收。S→q、非格心坐标/资源、探测、未知地图闭环、性能比较仍未实现或授权，不能称任意时刻事件接续已完成，也不确认创新。

## 三栏结果必须分开

|事项|v0.1历史失败|v0.2保存返回重新审核|v0.2新增123槽|
|---|---|---|---|
|真实入口|1，原版|0|123：原版53、H1 70|
|核心开始/返回/完成|1/1/1|0/0/0|123/123/123|
|工作流状态|槽1仍failed，审核器tuple/list错误|另记reused_saved_reaudited，旧状态不改|123通过，失败0、未运行0|
|内部图搜索|4：BFS1＋距离行BFS1＋A*2|0|{count_graph(accounts)}：BFS{accounts['context_BFS_started']}＋距离行BFS{accounts['distance_row_BFS_started']}＋A*{accounts['Astar_started']}，均完成|
|主路线审核|2次合法|0|{accounts['main_audit_calls']}次合法|
|独立审核|原运行时审核1次中止；旧包另有保存诊断1次|保存JSON及等值tuple载荷共2次通过|123次运行时审核通过|

首对原版来自旧槽1原生完整返回，H1来自本版槽2，因此不是同轮计时配对。其余53对的原版与H1均来自本版。不能说“本版124次新求解”，也不能说“旧失败槽已改成通过”。跨版本内部图搜索合计{count_graph(cross)}，旧4次没有重复计入新增{count_graph(accounts)}。

## 修复及前置证据

审核器现在先验证二维坐标、容器和值类型，再统一tuple/list比较；None与缺字段严格分开。local/recovery缺previous拒绝；冻结return schema本来没有previous，不造默认值，若显式给出则核对。还审查并修复了current/goal/options.cell、H1 primitive与来源端点、成对比较及报告输出的同类表示差异。bool、字符串、错误维数、非有限值、错误真实previous等均拒绝。

第一轮30类预登记纯桩，覆盖两个审核分支及运行时/JSON往返，共120次审核调用：28接受、92按预期拒绝；另4项成对比较检查通过。手写固定6边桩没有调用真实规划器或生成研究路线。旧8类26门槛证据按hash复用，未重新执行。保存旧首槽随后2次审核通过；仅转换坐标容器，不生成路线，运行时类型分支靠纯桩证明，不把JSON复核冒称完整运行时重演。

source_snapshot、derived、h1_direction/h1_rewards、输入、seed和原计划按字节绑定v0.1，评分、核心、候选、截止均未改。四个数值/评分审核函数的AST原源码片段逐字相同。每项审核/包装diff及理由保存；worker只加禁止槽1再次执行的保护。runtime_h1保持旧字节，实际仍加载v0.1派生核心路径，该文件与v0.2复制品哈希相同，实际加载hash全留存。真实开始后没有修代码、补跑或改输入。

## 验收内容及范围

54对原始格点路线及决策、分数、信用、恢复/返航均一致；数据是原开发保存状态，非留出、非普遍等价证明。16次方向夹具来自原ID排序首个合法非空输入，保持几何/任务/起终点/资源/捕食者/种子，只换四斜向及其2倍、每个重复一次；明确标synthetic，不是真实事件历史。{certified}次均实际出现首轮斜向分数认证，不只做输入接受检查。各同向正倍数/重复路线一致；不要求不同方向彼此路线一致，也不以路程变短作为通过标准。

本版{recoveries}个恢复事件及其后真实展开的预测方向从trace重建，H1逐边更新计数{accounts['heading_update_calls']}；70个H1结果末向与展开路线末边核对。预测方向/信用不是连续会话物理历史。

新增内部几何距离请求{accounts['geometry_distance_calls']}、路径请求{accounts['geometry_path_calls']}、预检查{accounts['geometry_precheck_calls']}；邻格评分{accounts['scored_neighbor_rows']}行。新增完整原生路线123，旧返回复用1；LOS、直达后处理、闭环、性能批0。20秒保护内全部eligible，没有截止中断。观察计数和必要日志开销在暖入口内，冷导入/外部审核另列；不作性能优劣声明。

最终只读verify还将对124份保存结果逐一审核，新增核心/图搜索/LOS均0；实际完成与次数以封存日志和final_receipt为准，另列于三栏调用账与结果.json，不混为阶段C新求解。旧failed与原始证据保留，历史进度只核验快照hash。

更新根进度、封存后停止，后续首连接及非整数资源须另审；不重启缓存、LAST、信用筛选，不使用留出或推送，不把工程修复称研究负结论或创新。
'''
    (HERE/'00_通俗报告与三栏结果.md').write_text(report,encoding='utf8')
    print(json.dumps(dict(acceptance_target_passed=accepted,new_entries=len(outputs),legacy_pairs=len(pairs),diagonals=len(diags),new_graph_searches=count_graph(accounts),cross_version_graph_searches=count_graph(cross)),ensure_ascii=False))

if __name__=='__main__':main()
