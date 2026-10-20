"""Saved evidence report and repeatable read-only integrity check."""
from verify_continuous_comparison_20261016 import *
def check():
    for p in (PREP,CHECK,RUN,RESULT):manifest(p)
    if (RESULT/'supplement_sha256.json').exists():assert all(sha(RESULT/n)==h for n,h in read(RESULT/'supplement_sha256.json').items())
    protocol=read(RUN/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    valid=core=0
    for j in protocol['jobs']:
        p=RUN/'runs'/(j['run_id']+'.json')
        if not p.exists() or read(p)['worker_status']!='returned':continue
        payload=read(p);c=read(Path(j['case']));raw=payload['raw'];assert payload['case_sha256']==sha(Path(j['case']))
        if raw['route']:assert route_check(c,raw['route'])['valid'];valid+=1
        if raw.get('core_route'):assert route_check(c,raw['core_route'])['valid'];core+=1
    result=dict(valid_final=valid,valid_core=core,protected_hashes=len(protocol['protected_hashes']),all_hashes_match=True,read_only=True,holdout_used=False)
    print(json.dumps(result,ensure_ascii=False));return result
def main():
    integrity=check();s=read(RESULT/'summary.json');pairs=read(RESULT/'paired_summary.json');stats=read(RESULT/'method_summary.json');prep=read(CHECK/'summary.json')
    d=DOC.parent;dest=d/'69_连续执行历史共同预算比较结果_20261016.md'
    text=f'''# 连续执行历史共同预算比较结果

日期：2026-10-16。第67/68份之后的有界开发验证，非正式留出主实验。

## 1. 问题与方法

检查第65/66份局部收益是否在自洽执行历史中保留。10图各自在事件前公开地图生成20秒P2完整初始路线，逐格执行到首次50%覆盖，再公开固定事件；共同当前位置、覆盖历史、真实未执行尾段与扣除已走步数的资源上限给两方法。没有在旧扫描检查点人工替换尾段，没有移动障碍/触发点，也没有重做初始准备寻找好结果。

LITERAL仍为固定R_PLUS1局部重排，P2_MULTI为冻结整体方法；双方都可选共同合法保底。比较1/20秒、两个预定种子，共80项独立进程串行响应调用。仅10张既有开发地图，两个种子不算20张独立地图，不作显著性或稳定性保证。事件相对当前位置可能与65份不同，不把跨轮变化归因于单一旧计划质量。

## 2. 验收与预算

- 80次完整响应，合法{s['valid']}；{s['final_audits']}条最终路线、{s['core_audits']}条核心路线、{s['structural_checks']}个计时内范围通过独立复核。
- 25项既有不同回归测试通过；不是新增25项算法贡献或实验地图。
- 响应超软预算>10ms为{s['overruns']}次，最大{max(0,s['max_overrun_seconds'])*1000:.3f}ms；异常与看门狗数见run/completion。时间不能宣传为严格硬实时保证。
- 复用已完成10次初始准备，累计实际{prep['preparation_seconds']:.3f}秒，名义额度200秒，另有4次准备软超时。整个连续历史支线为10准备＋80响应=90完整调用，不是本轮又准备10次。
- {integrity['protected_hashes']}项保护哈希不变，留出未生成/使用，三冻结基线及PPCPP不变。准备、响应与事后独立audit分别记账。

## 3. 同状态、同预算结果

差值=LITERAL−P2，负数更短。每预算20配对；全部有效时，均值等价于先对每图两个种子平均、再对10地图等权平均。

|预算|短/平/长|总步差|地图等权平均相对差|
|---|---|---:|---:|
'''
    for p in pairs:text+=f"|{p['budget']}秒|{p['shorter']}/{p['equal']}/{p['longer']}|{p['sum_difference']:+d}|{p['mean_relative']*100:+.2f}%|\n"
    text+='''
本轮两个预算平均差均为负，说明第65份的局部收益并非只能在人为替换检查点尾段时出现。但20秒优势缩小到0.74%，不能据此称稳定或普遍领先；还未独立留出验证。

按同一地图两个种子看：1秒8图均严格更短、1图一短一平、1图均更长；20秒5图均更短、1图一短一平、3图均相同、1图均更长。small_g4两个预算两个种子均多4步；large_g1的1秒每次少252步，20秒仅少2步。完整反例均纳入，无选择性删图。两个种子仍不能证明随机稳定性。

短平长只说明本批开发数据，不据总量或单个大图确立主算法。若短预算有收益而长预算消失，属于预算依赖，不包装成普遍优胜。方法都是限时启发式，失败与保底来源另列，合法最终路线不等于局部核心必然完成。

## 4. 逐图与种子，不省略反例

|地图|种子序号|1秒局部/P2|1秒差|20秒局部/P2|20秒差|
|---|---:|---|---:|---|---:|
'''
    one={(v['map_id'],v['repeat']):v for v in pairs[0]['per_pair']};twenty={(v['map_id'],v['repeat']):v for v in pairs[1]['per_pair']}
    for key,a in one.items():
        b=twenty[key];text+=f"|{key[0]}|{key[1]}|{a['local_steps']}/{a['P2_steps']}|{a['difference']}|{b['local_steps']}/{b['P2_steps']}|{b['difference']}|\n"
    text+='''
## 5. 时间与最终来源

|预算|方法|有效数|总步数|平均求解秒|软超时数|最终来源|
|---|---|---:|---:|---:|---:|---|
'''
    for p in stats:text+=f"|{p['budget']}秒|{p['method']}|{p['valid']}|{p['sum_steps']}|{p['mean_seconds']:.4f}|{p['overruns']}|{json.dumps(p['sources'],ensure_ascii=False)}|\n"
    text+='''
来源scope_core:common_fallback是窗口内部修复初始化，不是共同全局保底；其他scope_core标签也不能一律归功于2-opt。完整detail存阶段累计时刻、严格改善接受序列及core_patch。独立审核重建范围/责任，核对固定前后缀拼接、局部任务、全局覆盖及返航/额度；不靠求解器自报成功。

## 6. 停止与结论边界

本轮到80响应即停，不追着正例加圈层、预算或种子，不启动留出。当前仅验证已有固定局部策略在连续执行历史下的开发表现，未实现自适应范围选择、未比较全部冻结基线，未确认论文主算法/创新。

下一步先依据本批短平长、反例与预算趋势决定是否值得提出新的明确机制；不能仅凭“利用旧计划”宣称创新（整体P2本身也保留共同旧参考/保底）。若后续继续，先明确新机制相对现有固定局部和整体P2改变了什么，再写有界协议，不立即扩大完整测试矩阵。

## 7. 证据与只读重核

continuous_history_diagnostics/comparison_v0.1_20261016保存80任务预清单、保护哈希、源码快照、原始结果/日志、执行台账和完成状态；comparison_verification_v0.1_20261016保存summary、逐配对结果、方法统计、最终/core审计及保底来源；初始准备与真实状态证据仍在68份目录。

在工作区根目录可执行（不求解、不写实验结果）：
```powershell
& './运行环境/python/python.exe' -X utf8 report_continuous_comparison_20261016.py --check
```
性能重跑需新版本和新目录，不向本轮台账追加；默认输出独占创建，不覆盖历史。
'''
    with dest.open('x',encoding='utf-8') as f:f.write(text)
    lead='最新完成（第69份）：真实连续执行历史下80次响应比较已完成，'+str(s['valid'])+'条合法，'+str(s['core_audits'])+'核心/'+str(s['structural_checks'])+'范围独立复核通过。'
    lead+='；'.join(f"{p['budget']}秒局部对P2为{p['shorter']}/{p['equal']}/{p['longer']}短平长、平均相对差{p['mean_relative']*100:+.2f}%" for p in pairs)
    lead+=f"。{s['overruns']}次响应软超时，271保护哈希不变。10准备复用、80响应完成即停，无主算法确认，留出未用。"
    p=ROOT/'当前进度与下一步.md';v=p.read_text(encoding='utf-8-sig');p.write_text(v.replace('更新：2026-10-16。','更新：2026-10-16。\n\n'+lead,1),encoding='utf-8')
    p=d/'00_阅读入口.md';v=p.read_text(encoding='utf-8-sig');p.write_text(v.replace('## 当前进度先看这里','## 当前进度先看这里\n\n最新完成：[69 连续执行历史共同预算比较结果](69_连续执行历史共同预算比较结果_20261016.md)。80响应完成并独立复核，初始10次准备复用；本轮按协议停止，留出未用。',1),encoding='utf-8')
    write(RESULT/'report_record.json',dict(report_sha256=sha(dest),source_sha256=sha(Path(__file__)),integrity=integrity));write(RESULT/'supplement_sha256.json',{'report_record.json':sha(RESULT/'report_record.json')});print(dest)
if __name__=='__main__':
    if '--check' in sys.argv:check()
    else:main()
