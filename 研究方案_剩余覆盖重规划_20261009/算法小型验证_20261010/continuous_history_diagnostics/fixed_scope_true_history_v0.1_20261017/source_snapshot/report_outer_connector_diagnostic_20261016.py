"""Render report only from verified saved evidence."""
from run_outer_connector_diagnostic_20261016 import *
from verify_outer_connector_diagnostic_20261016 import VERIFY
def main():
    manifest(OUT);manifest(VERIFY);s=read(VERIFY/'summary.json');pairs=read(VERIFY/'paired_summary.json');stats=read(VERIFY/'method_summary.json')
    d=DOC.parent;dest=d/'65_窗口外连接轨迹诊断结果与停止判断_20261016.md'
    text=f'''# 窗口外连接轨迹诊断结果与停止判断

日期：2026-10-16。第64份预声明B1开发诊断；不是正式留出测试。

## 1. 目的、实施与结论

区分“保留窗口外字面路线过强”与其他限制：同一输入固定R_PLUS1窗口、局部required、接回端点和窗口外指定责任点顺序，只比较字面保留LITERAL与最短连接RECONNECT；另跑冻结P2_MULTI控制。20输入来自10个既有事件地图的RAW/P2_REF两参考，不是20张独立地图。

**核心发现：20输入的窗口外段不仅长度节省全为0，而且重连结果与字面段全部逐点相同。** 因此本轮没有产生有效的轨迹约束差异，不能通过限时结果的短平长宣称重连机制有效或无效；小幅在线差异只能视为有限预算执行波动，不能归因于几何改善。

前一轮A表明无事件损失对旧扫描质量敏感；本轮B1进一步说明这些事件输入在固定端点及任务责任点顺序下，没有直接压缩外部连接的空间。尚不能区分接回接口、任务次序、范围规则各自的影响，也不能解释所有事件损失。

## 2. 执行与验收

- 15项不同单元测试通过（重复运行不计为新增测试）；20输入由独立范围/责任集合代码及另一套BFS核验。
- 120项完整比较全部合法：最终路线复核{s['final_audits']}，核心路线复核{s['core_audits']}，计时内范围复核{s['structural_checks']}。
- {s['offline_replays']}条LITERAL核心patch离线拼入重连外部段，全部合法且路长不变。这是保存路线验证，不是额外在线求解或在线成绩。
- 软超时>10ms共{s['overruns']}次，最大{s['max_overrun_seconds']*1000:.3f}ms；完成比较无异常/看门狗终止。完整候选须在总截止前验收，最终独立audit在计时外。
- 202项保护哈希不变；三冻结基线及PPCPP未改。20输入在空目录从原事件快照和保存参考重放，哈希全部一致，无新增参考求解。留出未生成/使用。

中断说明：前115项完整结果保留。用户中断时下一项P2进程留下日志但无结果，作为1次不完整尝试单列排除；检查无存活Python进程后仅补跑剩余5项。因此是**120项完整比较＋1次中断尝试（121次进程尝试）**，不说总共只有120次实际启动。不完整尝试不参与质量、时间和合法率分母；原日志保留。interruption_record记录中断前台账哈希、残留日志哈希与续跑代码哈希。

## 3. 在线配对结果

差值=前一方法减后一方法；负数更短。相对差为10地图等权平均，每组一个种子，无显著性/稳定性推断。

|旧参考|预算|比较|短/平/长|总步差|平均相对差|
|---|---:|---|---|---:|---:|
'''
    for p in pairs:text+=f"|{p['reference']}|{p['budget']}s|{p['x']} / {p['y']}|{p['shorter']}/{p['equal']}/{p['longer']}|{p['sum_difference']:+d}|{p['mean_relative']*100:+.2f}%|\n"
    text+='''
两参考间不作同总预算排名：P2_REF承接第63份额外20秒参考准备，原准备费用另计；本轮没有重新准备。RAW/P2_REF的范围可不同，只在同参考内比较约束。LITERAL新包装器含责任拆分和日志开销，不冒充第58份旧程序的同一次性能结果。

## 4. 时间与来源

|参考|预算|方法|总步数|平均秒|最大秒|软超时次数|最终来源计数|
|---|---:|---|---:|---:|---:|---:|---|
'''
    for x in stats:text+=f"|{x['reference']}|{x['budget']}s|{x['method']}|{x['sum_steps']}|{x['mean_seconds']:.4f}|{x['max_seconds']:.4f}|{x['overruns']}|{json.dumps(x['sources'],ensure_ascii=False)}|\n"
    text+='''
共同保底不一定满足局部约束，核心与最终分别审计；阶段累计时间、每次接受时间及核心来源均保存在原始detail与verification/stages.json。指定服务点顺序不等于实际首次采集次序，附带覆盖按实际经过计账。

![全部20输入逐项结果](../../算法小型验证_20261010/outer_connector_diagnostics/verification_v0.1_20261016/all_case_steps.png)

## 5. 停止与下一步

按协议停止，不追加层数、种子或换图寻找正例，不进入留出主实验。当前没有确认主算法或创新点。

下一步先讨论是否仍保留局部机制方向，而不是继续扩大窗口：真正可变化的对象可能是任务访问骨架或接回接口，而不只是连接轨迹。任何新候选应先说明相比已有P2的具体差异、可改善的反例与有界验证门槛；若无法提出可区分机制，应停止该支线，回到强基线短板与正式实验冻结准备。以上是研究建议，不是已实现的算法或确认贡献。

## 6. 原始证据与只读复核

算法目录outer_connector_diagnostics：inputs_v0.1_20261016保存20输入及来源/结构参考；run_v0.1_20261016保存协议、源码快照、原始结果/日志、120行台账、中断记录、完成状态与哈希；verification_v0.1_20261016保存逐图配对、路线/core审计、阶段、离线回放、全例图及补充哈希；inputs_saved_reference_replay_v0.1_20261016保存输入哈希重放。

在工作区根目录执行只读复核（不会启动规划器）：
```powershell
& './运行环境/python/python.exe' -X utf8 finalize_outer_connector_diagnostic_20261016.py --check
& './运行环境/python/python.exe' -X utf8 -m unittest test_outer_connector_20261016 -v
```
性能重跑必须另建输出版本，不能再次向本轮台账追加。prepare/run/verify默认独占创建输出目录，不覆盖历史。
'''
    image=VERIFY/'all_case_steps.png';text=text.replace('../../算法小型验证_20261010/outer_connector_diagnostics/verification_v0.1_20261016/all_case_steps.png',image.as_posix())
    with dest.open('x',encoding='utf-8') as f:f.write(text)
    progress=ROOT/'当前进度与下一步.md';old=progress.read_text(encoding='utf-8-sig');lead=f'最新完成（第64/65份）：B1诊断120项完整比较全部合法，另1次中断尝试排除并保留日志；{s["core_audits"]}核心、{s["structural_checks"]}范围、20输入独立复核，20输入重放哈希一致。20输入重连外部段全部与字面段逐点相同、节省0；本轮无有效轨迹处理差异，不能从限时波动宣称机制收益。{s["overruns"]}次软超时，最大{s["max_overrun_seconds"]*1000:.3f}ms，202保护哈希不变，留出未用。按协议停止；下一步先讨论任务骨架/接口方向是否值得保留，不继续追正例扩大圈层。\n\n'
    progress.write_text(old.replace('更新：2026-10-16。','更新：2026-10-16。\n\n'+lead,1),encoding='utf-8')
    index=d/'00_阅读入口.md';v=index.read_text(encoding='utf-8-sig');v=v.replace('## 当前进度先看这里','## 当前进度先看这里\n\n最新完成：[65 窗口外连接轨迹诊断结果与停止判断](65_窗口外连接轨迹诊断结果与停止判断_20261016.md)。120完整比较＋1中断尝试单列；20输入外部段逐点相同、理论节省0，不能解释为重连收益。独立复核与输入重放通过，留出未用。下方“进行中”为历史状态，已结束。',1);index.write_text(v,encoding='utf-8');print(dest)
if __name__=='__main__':main()
