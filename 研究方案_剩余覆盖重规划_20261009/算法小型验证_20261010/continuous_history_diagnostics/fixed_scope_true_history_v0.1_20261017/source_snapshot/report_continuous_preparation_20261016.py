from verify_continuous_preparation_20261016 import *
def main():
    manifest(PREP);manifest(CHECK);s=read(CHECK/'summary.json');checks=read(CHECK/'checks.json')
    d=DOC.parent;path=d/'68_连续执行初始计划准备与事件状态核验_20261016.md'
    text=f'''# 连续执行初始计划准备与事件状态核验

日期：2026-10-16。第67份实际初始准备阶段，不是事件后比较结果。

## 1. 已实际完成

10张固定事件开发地图，各自在事件前公开地图上调用冻结P2_MULTI一次，预算20秒。完成{s['preparation_calls']}次准备，合法{s['valid_preparation']}次。初始输入只含已知完整飞行域、当时目标、空历史、基地和原H见证；初始种子仅由map_id固定派生。未来目标/障碍及旧事件检查点未交给规划器。

随后逐格执行保存的完整初始路线至首次覆盖一半初始目标，生成真实当前位置、覆盖历史、未执行尾段和剩余额度，再发布原固定事件。另一套账本代码核对首次触发、尾段连续性、覆盖及资源扣减；事件自由/活动/暂缓集合守恒、连通性及合法见证检查，再以独立结构实现核对R_PLUS1范围。

事件状态分类：{json.dumps(s['event_status_counts'],ensure_ascii=False)}。不挪动障碍、触发点或当前位置，不挑图。

## 2. 时间及边界

准备实际求解时间合计{s['preparation_seconds']:.3f}秒（名义上限10×20=200秒），软超时>10ms为{s['overruns']}次，最大超时{max(0,s['max_overrun_seconds'])*1000:.3f}ms。该费用双方共享并单列，不称免费参考。独立audit在求解计时外；进程墙钟另存台账。

10项账本单元测试再次通过，不计为新增10种测试。初始路线合法不等于全局最优；本轮只用既有10开发图，不代表泛化或新独立地图。范围参考与离线见证均只用于验证，不能免费交给后续在线搜索。

## 3. 逐图准备与触发状态

|地图|原H完整路线步数|P2完整路线步数|执行步数|实际覆盖比例|当前位置|事件状态|
|---|---:|---:|---:|---:|---|---|
'''
    records=read(PREF/'records.json')
    for e,c in zip(records,checks):
        raw=read(Path(e['initial_case']));h=c.get('history',{})
        text+=f"|{e['map_id']}|{len(raw['old_route'])-1}|{c.get('initial_steps','—')}|{h.get('executed_steps','—')}|{h.get('actual_progress',0)*100:.2f}%|{h.get('current','—')}|{c['status']}|\n"
    text+='''
## 4. 下一步与停止条件

事件后性能比较尚未启动（0次），不能提前说局部仍领先。下一步补齐比较运行器、两个固定种子/顺序预清单及保存结果独立验收后冻结，按67份只比较LITERAL与P2_MULTI，1/20秒、两个种子；全10图通过时最多80项。若模型不支持或输入门槛未过，先保留原因，不能换图凑数。

完成该有界比较即停，不根据正反结果调进度、初始预算、窗口或接口。无确认主算法或创新点；三冻结基线及PPCPP不变，留出不生成/使用。

## 5. 证据

continuous_history_diagnostics/preparation_v0.1_20261016保存准备协议、10任务/输入哈希、保护源码快照、逐次原始结果及日志、执行台账、完成状态和哈希。

preparation_verification_v0.1_20261016保存独立历史/范围检查、事件分类、10图状态汇总及适用case；原preflight保持不变。根目录prepare_continuous_history_runs_20261016.py与verify_continuous_preparation_20261016.py对应运行与复核。输出目录独占创建，不能原地重跑覆盖。
'''
    with path.open('x',encoding='utf-8') as f:f.write(text)
    p=ROOT/'当前进度与下一步.md';v=p.read_text(encoding='utf-8-sig');line=f'最新完成（第68份）：事件前20秒P2准备10次，{s["valid_preparation"]}条完整路线合法；真实执行至50%后事件状态分类{s["event_status_counts"]}，独立账本/范围与见证核验完成。准备实际累计{s["preparation_seconds"]:.3f}秒，{s["overruns"]}次软超时，费用另计。事件后比较0次，下一步补齐两个种子运行器与验收后冻结最多80项，不预告收益。留出未用。'
    p.write_text(v.replace('更新：2026-10-16。','更新：2026-10-16。\n\n'+line,1),encoding='utf-8')
    p=d/'00_阅读入口.md';v=p.read_text(encoding='utf-8-sig');p.write_text(v.replace('## 当前进度先看这里','## 当前进度先看这里\n\n最新完成：[68 连续执行初始计划准备与事件状态核验](68_连续执行初始计划准备与事件状态核验_20261016.md)。10次初始准备已实际执行，真实历史与事件门槛已复核；事件后性能比较未启动。',1),encoding='utf-8')
    write(CHECK/'report_record.json',dict(report_sha256=sha(path),report_source_sha256=sha(Path(__file__)),protected_unchanged=all(sha(Path(p))==h for p,h in read(PREP/'protocol.json')['protected_hashes'].items()),comparison_calls=0,holdout_used=False));print(path)
if __name__=='__main__':main()
