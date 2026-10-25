"""Summarize existing failed/unused slots. Never run or audit an algorithm."""
from pathlib import Path
import json,hashlib

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    assert not (HERE/'调用账与阶段状态.json').exists(),'no delivery overwrite'
    slots=read(HERE/'124槽实际账.json');status=read(HERE/'status.json');plan=read(HERE/'计划_124槽.json')
    outputs=[read(p) for p in (HERE/'outputs').glob('*.json')]
    gates=[read(p) for p in sorted((HERE/'tech').glob('attempt_*_result.json'))]
    accounts={}
    for x in outputs:
        for key,value in x['accounts'].items():accounts[key]=accounts.get(key,0)+value
    by_phase={phase:{key:sum(x['phase']==phase and x['status']==key for x in slots) for key in ('passed','failed','not_run')} for phase in ('legacy','diagonal')}
    attempted=sum(x['status']!='not_run' for x in slots)
    finding=read(HERE/'失败只读归因与保存路线审计.json')
    calls=dict(real_entry_attempts=attempted,warm_entries=sum(x['entry'] is not None for x in outputs),
        original_entries=sum(x['job']['method']=='ORIGINAL' for x in outputs),h1_entries=sum(x['job']['method']=='H1' for x in outputs),
        formal_passed_slots=sum(x['status']=='passed' for x in slots),formal_failed_slots=sum(x['status']=='failed' for x in slots),
        not_run=sum(x['status']=='not_run' for x in slots),legacy_pairs=len(read(HERE/'54等价证据.json')),
        diagonal_entries=len(read(HERE/'16斜向技术证据.json')),accounts=accounts,
        graph_searches_started=accounts.get('context_BFS_started',0)+accounts.get('distance_row_BFS_started',0)+accounts.get('Astar_started',0),
        graph_searches_completed=accounts.get('context_BFS_completed',0)+accounts.get('distance_row_BFS_completed',0)+accounts.get('Astar_completed',0),
        LOS_queries=0,postprocess_calls=0,closed_loop_sessions=0,performance_comparisons=0,
        independent_worker_audit_attempts=len(outputs),independent_worker_audit_completed=sum(x['audit'] is not None for x in outputs),
        independent_saved_diagnostic_audit_attempts=1,independent_saved_diagnostic_audit_completed=int(finding['saved_route_audit_completed']),
        read_only_verify_added_graph_or_core=0,
        pure_gate_attempts=len(gates),pure_gate_cases=sum(len(x['cases']) for x in gates),pure_gate_calls=gates[-1]['pure_function_calls'],
        original_inputs_copied=54,new_geometry_or_event_inputs=0,synthetic_direction_slots_planned=16,synthetic_direction_slots_executed=0,
        complete_new_native_routes=sum(bool(x['entry'] and x['entry']['raw']['branches']['P0']['route']) for x in outputs),
        new_h1_routes=0,unlimited_retries=0,technical_repair_rounds=0,holdout_uses=0)
    dump(HERE/'调用账与阶段状态.json',dict(calls=calls,phase_counts=by_phase,failure=status['failure'],formal_acceptance='NOT_PASSED',no_rerun=True))
    lines=['# 124槽计划与实际状态','','失败尝试占用槽1；其余123未运行。保存路线事后只读审核不改变此状态。','', '|槽|阶段|ID|方法|状态|原因|','|---|---|---|---|---|---|']
    for x in slots:lines.append(f"|{x['slot']}|{x['phase']}|{x['id']}|{x['method']}|{x['status']}|{x['reason'] or ''}|")
    (HERE/'124槽完整表.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    x=outputs[0];native=x['entry']['raw']['branches']['P0'];steps=len(native['route'])-1
    report=f'''# PPCPP真实来向H1第一块：实现已保存，真实验收中止

本轮**未通过真实验收**。8类纯函数/手工边更新门槛共26个案例，第一轮全部通过；随后真实批在槽1的原版独立审核失败，按执行稿停止，不修补、不补跑。计划124槽实际尝试1，失败槽1，其余123未运行；54旧输入没有形成任何完整成对等价证据，16合成斜向入口均未运行。

## 失败在哪里

原版入口正常完成，核心开始/返回/完成各1，两个内部路线审核均合法，未触20秒截止。失败是本包独立审核器的容器比较错误：`independent_audit.py:80`把运行时的`event.previous`元组与输入JSON的列表直接比较。原runtime把previous转换为tuple，而worker保留JSON的list，两者坐标相同，Python容器类型不同使断言失败。这是我编写的验收器技术错误，不能据此判断原算法或H1路线失败。

原生返回、完整trace、入口日志、失败栈和源码冻结均保留。之后只对保存JSON做了一次独立路线/信用/方向复核：该保存路线{steps}步合法，JSON已把tuple序列化为数组，所以不再触发运行时容器差异。此只读检查没有新增入口/核心/图搜索，不构成槽1补跑或正式通过；槽1仍failed，新版真实入口仍0。具体见失败只读归因与保存路线审计.json。

## 实现了什么及证据强度

已按原字节保存原源并另建派生核心/入口，diff见最小改动.diff。H1保留原轴向/无方向评分算术与原权重、其他奖励/排序；非轴向原始有理来向规范化为同向整数对，用精确有理数＋单根式总分比较，禁止epsilon平局；每条预测格点边更新来向，零长保留。日志不伪造previous，legacy_previous只在保存旧输入/对照元数据中。

26纯案例覆盖四轴向、四斜向、正倍数与有理数、相反方向、精确/近似外观平局、无运动与UNKNOWN/非法来源、零长继承及恢复后方向更新。纯门槛不调用真实规划器，不能代替集成验收。新核心模块在worker冷导入时已加载，但没有一次H1真实入口/核心运行，不能宣称54输入退化一致、斜向真实接收已验收或完整格心适配已通过。

## 实际调用与停止边界

真实入口尝试1（原版1、新版0），原核心开始/返回/完成各1；内部图搜索{calls['graph_searches_started']}次：可达性BFS1、距离行BFS1、A*2，均完成。几何距离请求48、路径请求2、预检查1；内部路线审核2，原worker外部审核1次中止，额外保存路线审核1次完成。纯函数调用另见调用账与阶段状态.json；不能报零求解。

新增原生完整路线1（原版），H1新路线0。LOS/后处理/闭环/性能比较均0；54原几何仅按字节复制，合成方向16槽只预登记、未执行。计数观察开销计入暖入口，冷导入和外部审核另列，本轮不提出性能结论。

第一阶段108槽：通过0、失败1、未运行107；第二阶段16槽：全部未运行。全部失败/未运行保留在124槽完整表.md及原JSON账内，不混入正式汇总。技术门槛仅1轮，无技术修复；真实开始后冻结代码原字节保留。

执行稿要求真实问题立即停止、失败消耗槽不补跑，因此本轮不修审核器后接着跑。后续若另获授权，先在新版本用纯桩覆盖运行时tuple/list与保存JSON的坐标比较，再审接续预算及受影响结果；本轮不创建新的执行批或自行复用未运行额度。

S→q、非格心坐标/资源、探测器、未知地图、原地采集及闭环都未实施。此块是模型接口基础；不确认原论文完整复现、性能改善或创新，不重启缓存/LAST/信用筛选，冻结原件、旧包、留出不变，无推送。

文件核验通过仅表示来源/冻结文件/保存证据完整，**不表示真实验收通过**。新verify核对保存的历史进度快照，不要求实时根进度永远相等。更新根进度后封存停止，交负责人审核。
'''
    (HERE/'00_通俗报告与中止结论.md').write_text(report,encoding='utf8')
    print(json.dumps(dict(delivered_failure_evidence=True,attempted=attempted,failed=1,not_run=123,H1_entries=0,graph_searches=calls['graph_searches_started']),ensure_ascii=False))

if __name__=='__main__':main()
