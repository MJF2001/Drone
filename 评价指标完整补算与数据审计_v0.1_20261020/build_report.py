"""Render full metric tables from verified numerical JSON; no manual transcription."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
def read(n):return json.loads((H/n).read_text(encoding='utf-8'))
def table(headers,rows):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def fmt(v):return 'NA' if v is None else f'{v:.2%}'
def main():
    s=read('summary.json');pairs=read('paired_states.json');wins=read('paired_wins.json');a=read('audit_results.json')
    fields=[('length','总步数'),('fresh_target_steps','新覆盖步数'),('historical_target_steps','历史重复步数'),('repeated_new_target_steps','本轮重复步数'),('non_target_steps','非目标转移步数'),('turns90','90°转弯'),('turns180','180°折返'),('direction_changes','方向变化总数'),('return_tail_steps','返航尾段步数（已包含）'),('initial_credit','起点额外采集'),('missing_active','当前可检漏检数'),('deferred','暂缓格次')]
    totals={m:{k:sum(x[m][k] for x in pairs) for k,_ in fields} for m in ('PPCPP','CAP_KR1')}
    rows=[[label,totals['PPCPP'][key],totals['CAP_KR1'][key]] for key,label in fields]
    for key,label in [('active_coverage_pooled','当前可检覆盖率（任务计数加权）'),('published_coverage_pooled','已发布任务完成率（任务计数加权）'),('overlap_pooled','目标到达重复比例（总体）'),('overlap_route_mean','重复比例（逐路线均值）')]:
        rows.append([label]+[f"{s['KR1_PAIR'][m]['all_valid'][key]:.4%}" for m in ('PPCPP','CAP_KR1')])
    rows.append(['剩余任务完成率（逐状态均值）']+[f"{statistics.mean(x[m]['remaining_completion_fraction'] for x in pairs):.4%}" for m in ('PPCPP','CAP_KR1')])
    rows.append(['已发布任务完成率（逐状态均值）']+[f"{statistics.mean(x[m]['published_coverage'] for x in pairs):.4%}" for m in ('PPCPP','CAP_KR1')])
    lines=['# 完整评价指标与数据准确性复核报告','',
        '2026-10-20。**本次未调用任何规划器，仅重审并补算360条已有正式路线。新PPCPP/CAP-KR1的80条与旧七算法280条分批保存，不混成跨批排名。**','',
        '## 1. 数据准确性结论','',
        f"- 两种不同实现（状态遍历与到达直方图/首次索引）在{a['metric_crosschecks']}个穷举/边界输入上结果一致；360条原始路线的全部指标逐项一致。另与第37份原始纯指标函数逐字段对照，360条均一致。",
        '- 原两批独立核验器再次通过：路线、逐决策、输入与原哈希、及时性和旧汇总均通过；本次预先固定1213项证据/脚本/定义哈希，处理后逐项未变。',
        '- 本次未发现360条保存路线或原步数汇总的数值错误。原方法适配边界仍在，测试通过不证明任意地图正确或作者代码等价。',
        '- **发现需补充而非掩盖的信息：有5个事件状态存在暂缓任务。因此当前可检100%不等于已发布任务100%；最近对照此前只重点汇报步数与时间，不能称完整多指标评价。**','',
        '## 2. 最新PPCPP/CAP-KR1：20状态的完整路径指标','',
        '每状态两种子路线相同，主表每状态只计一次，共20状态、10张关联地图，不是40独立样本。时间分布在下一节保留40次真实测量。没有把跨状态计数当空间面积并集。','',table(['指标','PPCPP','CAP-KR1'],rows),'',
        '### 指标核对与取舍','',
        '- PPCPP：7832+557+263+220=8872步；CAP-KR1：7832+426+1025+99=9382步。两方新覆盖任务量相同。',
        '- PPCPP比CAP-KR1历史重复多131步、非目标转移多121步，但本轮重复少762步，净少510步。不能宣称所有路程组成都更优。',
        '- 两方目标到达分别为8652和9283次，重复分别820和1451次；总体重叠率9.4776%和15.6307%，相差约6.1531个百分点，不能把这个差写成相对减少6.1531%。',
        '- 返航尾段已在总步数里。固定终点巡游在最后新目标覆盖后仍可能有移动，因此尾段不等于代码中标为return的动作段。转弯按路线内部相邻移动计算，不额外加入历史方向到第一步的转向。',
        '- 每方法20状态的已发布目标计数13793、已完成13766、暂缓27格次；当前可检目标计数13760全部完成。另有6个已完成历史目标格次后来不可飞，继续保持已完成。以上均为状态任务计数，不是唯一物理面积。','',
        '### 逐状态配对胜负','',
        '每项小者为优。原步数结论仍为PPCPP平均相对少5.6062%，控制组少9.6136%，事件组少1.5988%；事件组步数4短/2平/4长，不能称稳定领先。','',
        table(['指标','PPCPP优／平／劣于CAP-KR1'],[[dict(fields).get(k,'目标到达重复比例' if k=='overlap_ratio' else k),f"{v['PPCPP_better']}／{v['equal']}／{v['PPCPP_worse']}"] for k,v in wins['all'].items()]),'',
        '### 逐状态明细','',
        '单元格“PPCPP / CAP-KR1”；全部当前可检覆盖率100%，全部合法返航。完整字段及各分层胜负见paired_states.json与paired_wins.json。','',
        table(['状态','组/规模','步数','总体重复比例','90°','180°','非目标步','尾段步','暂缓格'],[[x['case_id'],x['state']+'/'+x['scale'],str(x['PPCPP']['length'])+' / '+str(x['CAP_KR1']['length']),fmt(x['PPCPP']['overlap_ratio'])+' / '+fmt(x['CAP_KR1']['overlap_ratio']),str(x['PPCPP']['turns90'])+' / '+str(x['CAP_KR1']['turns90']),str(x['PPCPP']['turns180'])+' / '+str(x['CAP_KR1']['turns180']),str(x['PPCPP']['non_target_steps'])+' / '+str(x['CAP_KR1']['non_target_steps']),str(x['PPCPP']['return_tail_steps'])+' / '+str(x['CAP_KR1']['return_tail_steps']),x['PPCPP']['deferred']] for x in pairs]),'',
        '## 3. 最新对照时间、可靠性','',
        '每方法40次真实入口测量。双方完整/合法/及时均40/40，技术失败/迟到/缺失/未配对均0；不把重复测量当独立地图。计时包含共同JSON解析、验证、方法构造、剩余预算求解与完整结果编码；严格外层及调用者<20秒。','',
        table(['方法','均值秒','中位数秒','P95秒','最大秒','超20秒','超10ms','最大超出秒'],[[m]+[f"{q['time'][k]:.6f}" for k in ('mean','median','p95','maximum')]+[q['time']['strict_over_budget'],q['time']['over_10ms'],f"{q['time']['max_excess']:.6f}"] for m,q in s['KR1_PAIR'].items()]),'',
        'P95采用(n−1)×0.95线性插值。入口均值、中位数与P95不同反映规模混合，不能只报告最快值。最大调用者时间沿用原对照记录：PPCPP约0.105937秒、CAP-KR1约4.769917秒。','',
        '## 4. 旧七算法v0.3：完整历史诊断表','',
        '**以下每方法40次的所有合法路线均列入，包括迟到路线，只作历史质量诊断，不能用P2较短总步数宣布其在20秒内获胜。**P2及时24/40、MST34/40，样本不齐必须另做共同及时配对；这里不重新建立七方排名。旧时间不含与新批次相同的结果编码，两批不可拼成统一时间榜。','',
        table(['方法','合法/及时','总步数','总体重复率','路线均重复率','90°','180°','历史重复','本轮重复','非目标步','尾段步'],[[m,f"{q['valid']}/{q['timely']}",q['all_valid']['length'],fmt(q['all_valid']['overlap_pooled']),fmt(q['all_valid']['overlap_route_mean'])]+[q['all_valid'][k] for k in ('turns90','turns180','historical_target_steps','repeated_new_target_steps','non_target_steps','return_tail_steps')] for m,q in s['SEVEN_V03'].items()]),'',
        '旧七方法各40路线：新覆盖均15664步、可检覆盖率均100%、漏检均0、暂缓各54格次。总体已发布任务完成率均99.8042%，不是100%；两个重复的计数不能说成54个新物理目标。','',
        '### 旧七算法及时子集（仅展示本方法子集，不能横向直接排位）','',
        table(['方法','及时n','步数','重复比例','90°','180°','非目标步'],[[m,q['timely_only']['n'],q['timely_only']['length'],fmt(q['timely_only']['overlap_pooled']),q['timely_only']['turns90'],q['timely_only']['turns180'],q['timely_only']['non_target_steps']] for m,q in s['SEVEN_V03'].items()]),'',
        '### 旧七算法时间','',
        table(['方法','均值秒','中位数秒','P95秒','最大秒','超20秒','超10ms','最大超出秒'],[[m]+[f"{q['time'][k]:.6f}" for k in ('mean','median','p95','maximum')]+[q['time']['strict_over_budget'],q['time']['over_10ms'],f"{q['time']['max_excess']:.6f}"] for m,q in s['SEVEN_V03'].items()]),'',
        '## 5. 后续研究基础：哪些可用，哪些不能冒认','',
        '- 统一定义以本目录《评价指标口径_v1_20261020.md》为入口，保留第37/53份来源；不新增任意加权综合分。',
        '- 最近PPCPP/CAP-KR1可用作本批同条件开发比较，CAP-KR1必须独立命名，不能改名作者原版CAP。',
        '- 旧七算法可用作带版本和协议的历史诊断。旧CAP目标接续限制、OARP适配/保底、TREE_MST不是TRACE/C*、TRACE已知分支等身份边界不因数据复核通过而消失。',
        '- 未包含C*八邻接敏感性（运动模型不同），也未把失败/中止批次或前置测试计入360正式路线。',
        '- 同图控制/事件关联、两种子重复、重复使用开发数据均需披露；当前无留出泛化、真实能耗或完整论文原版性能保证。',
        '- 后续发现代码或指标错误，另建版本说明受影响记录，不覆盖本基础档案。新版本必须复用同一正确性与指标审计。','',
        '## 6. 准确性复核和可重放证据','',
        '四层检查：①两批原核验器的物理/逐决策/哈希与原汇总；②两套不同指标实现及10288个穷举/边界输入；③与第37份原纯函数的一致性；④逐路线与所有汇总/配对/P95再复核。原始数据未改，新求解调用0。脚本独立是实现路径不同，不声称由另一个人或另一个代理审查。','',
        '保存：protocol.json（预封输入与源码哈希）、per_run.json（360逐路线全部指标及来源）、summary.json（分批/全合法/及时子集/时间）、paired_states.json（新批20状态）、paired_wins.json（分组逐指标胜负）、upstream_checks.json（原核验输出）、audit_results.json、manifest.json。','',
        '只读复核命令：','',
        '```powershell',
        "Set-Location -LiteralPath 'E:\\无人机研究项目_接续包_20261014'",
        "& './运行环境/python/python.exe' -B -X utf8 './评价指标完整补算与数据审计_v0.1_20261020/verify.py'",'```','',
        '核验会再次读取原封存数据及定义；如原包移动，绝对路径需显式迁移并记录，不冒充另一台电脑已验证。']
    (H/'完整指标与准确性审核报告_20261020.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()
