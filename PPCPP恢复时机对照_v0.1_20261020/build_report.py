import json
from pathlib import Path
H=Path(__file__).resolve().parent
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def main():
    a=json.loads((H/'analysis.json').read_text(encoding='utf-8'));g=json.loads((H/'gate_PASS.json').read_text(encoding='utf-8'));s=a['summary'];ms=('PPCPP','FIRST','SECOND')
    lines=['# PPCPP第一次与第二次恢复试走：固定时机对照开发结果','','2026-10-20。独立命名候选v0.1，不改冻结原版。此为重复使用已见开发输入的有限实验，不是留出泛化检验，不宣称确立论文主算法或创新。','',
    '## 1. 唯一改变了什么','',
    'PPCPP为冻结独立适配版；FIRST为上轮首次恢复THREE逐字节副本；SECOND在原生第二次恢复时才分支，之前完全按原策略执行。两种候选都只试走一次，至多原最近/基地最近/基地最远三个确定入口去重，完整模拟至返航，用真实合法总步数择优、同值保原分支。后续不嵌套试走。没有第二次恢复则SECOND等于原路线。','',
    '原局部奖励、权重、固定捕食者、历史朝向、任务和暂缓口径及几何规则不变。真实H/initial_targets不改；候选路径、trace和预测pending各自私有，仅静态物理F几何共享。第二次是本次求解内部第二次没有相邻待检目标时的恢复，不是第二次环境事件。','',
    '## 2. 验收与正式样本','',
    f"门槛合计{g['calls']}调用：64微型目标子集×4方法={g['micro_calls']}、3边界夹具×4={g['boundary_calls']}、现有开发输入补足{g['supplement_calls']}、检查点发现{g['discovery_calls']}、逐检查点截止注入{g['deadline_stages']}。ONE2仅原入口用于等价验收。包含无任务、基地不可达、资源不足，以及原分支已完成而替代分支开始时截止仍整体拒收。子集含等价输入，不当独立地图。",
    '门槛通过后原20道路状态与受控27输入，各3方法×2种子，共282次全新正式调用；旧结果不拼入本批性能比较。94状态—种子组核对每种候选原分支与同批PPCPP完整route/trace相同；FIRST另与上轮THREE完整route/trace核对。逐路线和逐候选独立BFS/奖励/历史账本审核、两套指标交叉补算。','',
    table(['批次/方法','完整合法及时/调用','触发状态数','选非原分支状态数'],[[b+'/'+m,f"{v['eligible']}/{v['calls']}",v['triggered'] if m!='PPCPP' else '—',v['selected_alternative'] if m!='PPCPP' else '—'] for b,z in s.items() for m,v in z['methods'].items()]),'',
    '两种子指标一致，路程总量按每状态一次；耗时用全部实际调用，不把重复种子视为独立地图。失败或迟到不删；如有不完整及时状态，下表仅完整及时交集并明确样本数，不把缺失路线计0。','',
    '## 3. 主问题：第二次是否优于第一次','',
    table(['批次/比较（前者减后者）','共同状态','短/平/长','前者/后者总步数','净差','逐状态相对差均值'],[[b+'/'+name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}" if v['mean_relative'] is not None else '—'] for b,z in s.items() for name,v in z['pairs'].items()]),'',
    '负差为前者更短。不能只展示SECOND相对原版，而隐去它相对FIRST的退化。原20和受控27分开，不合成总体泛化分数。“相对原版不变长”有原分支保留的结构原因，不等于新优势得到独立验证。','',
    '## 4. 完整指标','']
    fields=[('length','含返航总步数'),('fresh_target_steps','新采集移动'),('historical_target_steps','历史重复'),('repeated_new_target_steps','本轮重复'),('non_target_steps','非目标移动'),('turns90','90度转弯'),('turns180','180度折返'),('direction_changes','方向变化总次数'),('completion_step','完成当前可检任务前步数'),('return_tail_steps','最终返航尾段（已含于总步数）'),('initial_credit','起点即时新采集'),('remaining_before','扣H后待检格次（含起点）'),('newly_completed','本轮完成待检格次'),('active_targets','当前可检目标格次'),('active_covered','已完成可检目标格次'),('missing_active','可检遗漏'),('published_targets','已公开目标格次'),('published_covered','已公开中完成格次'),('deferred','暂缓格次'),('uncompleted_published','已公开未完成格次'),('target_arrivals','目标到达步数'),('duplicate_target_arrivals','重复目标到达步数')]
    for batch,z in s.items():
        lines += ['### '+batch,'',table(['指标（每状态一次）']+list(ms),[[label]+[z['methods'][m]['totals'][key] for m in ms] for key,label in fields]),'',table(['比率（计数加权）']+list(ms),[[label]+[f"{z['methods'][m]['totals'][key]:.4%}" for m in ms] for key,label in [('remaining_completion_pooled','剩余任务完成率'),('active_coverage_pooled','当前可检覆盖率'),('published_coverage_pooled','全部已公开覆盖率'),('overlap_pooled','目标到达重复比例')]]),'']
    lines+=['四分类移动之和严格等于总步数。返航尾段是其中一部分，不能重复相加。暂缓不计已完成；汇总格次跨快照会重复同一物理格，不表示唯一物理面积。转弯按输出路线连续边方向统计，不另加入历史朝向的起点转弯；历史朝向仍用于规划决策。','',
    '## 5. 全程计算时间','',
    table(['批次/方法','均值秒','中位秒','P95秒','最大秒'],[[b+'/'+m]+[f"{v[k]:.6f}" for k in ('time_mean','time_median','time_p95','time_max')] for b,z in s.items() for m,v in z['methods'].items()]),'',
    '共同20秒暖入口含JSON解析/验证、Snapshot构造、所有分支求解与内部审核、完整原结果JSON编码；另要求调用者墙钟<20秒。进程启动/导入、文件读取落盘、外部独立复核不计，方法一致。90秒看门狗不扩充算法预算。全程计时不等于纯核心CPU时间；不同候选次数及trace编码开销保留，不删慢调用。超时整体拒收，完成原分支仅作诊断证据。','',
    '## 6. 原道路逐状态比较','',
    table(['状态','原版','FIRST','SECOND','SECOND−FIRST','FIRST/SECOND触发','FIRST/SECOND候选数'],[[x['case_id']]+[x['methods'][m]['metrics']['length'] if x['methods'][m]['metrics'] else '失败' for m in ms]+[x['methods']['SECOND']['metrics']['length']-x['methods']['FIRST']['metrics']['length'] if all(x['methods'][m]['metrics'] for m in ms) else '—',f"{x['methods']['FIRST']['triggered']}/{x['methods']['SECOND']['triggered']}",f"{x['methods']['FIRST']['candidates']}/{x['methods']['SECOND']['candidates']}"] for x in a['states'] if x['batch']=='original20']),'',
    '## 7. 第二次与第一次不同时的成本分解','',
    '各段取选中分支trace：触发前缀／强制入口衔接／此后到最后待检格的移动／返航。两种方法触发时间不同，前缀长度不相同，不能只比较中间段；必须看四段总账。输入、入口和各候选全路线成本见analysis.json。','',
    table(['批次/状态','FIRST 前缀/入口/后续/返航','SECOND 前缀/入口/后续/返航','总步数差'],[[x['batch']+'/'+x['case_id'],'/'.join(str(v) for v in x['methods']['FIRST']['cost'].values()),'/'.join(str(v) for v in x['methods']['SECOND']['cost'].values()),x['methods']['SECOND']['metrics']['length']-x['methods']['FIRST']['metrics']['length']] for x in a['states'] if all(x['methods'][m]['eligible'] for m in ms) and x['methods']['SECOND']['metrics']['length']!=x['methods']['FIRST']['metrics']['length']]),'',
    '## 8. 结论边界和复核','',
    '本轮只检验这个固定触发位置变化。不能从有限结果推断所有后期恢复无效，也不能继续扫描第三/第四次恢复直到挑出最好。若要改变入口集合、试走次数或触发选择器，须提出独立问题、另立版本和预登记。本轮未使用留出，未修改旧结果或冻结基线，未推送GitHub。','',
    'protocol.json固定开跑前规则/输入/源码；gates.json为全部门槛原输出；execution为282新调用完整结果；analysis.json含47状态完整指标、候选与分段、两批汇总；verify.py只读重审来源哈希、门槛、逐决策、双指标、原分支等价、上轮FIRST一致性及统计；manifest.json封存本目录。','',
    '```powershell',"& './运行环境/python/python.exe' -B -X utf8 'PPCPP恢复时机对照_v0.1_20261020/verify.py'",'```','']
    (H/'恢复时机对照结果_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()
