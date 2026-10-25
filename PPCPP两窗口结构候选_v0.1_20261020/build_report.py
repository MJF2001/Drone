import json
from pathlib import Path
H=Path(__file__).resolve().parent
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def main():
    a=json.loads((H/'analysis.json').read_text(encoding='utf-8'));g=json.loads((H/'gate_PASS.json').read_text(encoding='utf-8'));s=a['summary'];ms=('PPCPP','FIRST','STRUCT')
    lines=['# PPCPP两窗口结构候选：实现验收与共同预算开发比较','','2026-10-20。STRUCT独立版本v0.1。没有覆盖旧算法或历史结果，留出未使用。此轮数据已被反复用于分析和设计，不是泛化检验，不宣称主算法或创新已经确定。','',
    '## 1. 实现了什么，没实现什么','',
    'STRUCT仅在本次求解内前两个原生恢复机会生成原最近/基地最近/基地最远候选，并对预测尚未采集U四邻接分块。候选跨至少两个U块则E真，在首个E真处至多完整试走一次；假则按原最近继续。第二次之后无新结构判断。触发后完整仿真各入口余程及返航，真实合法总步数择优，同值保原；即便选原分支也已用掉唯一机会，后续不嵌套试走。','',
    '候选距离与结构检查在完整分支前计算并计入共同预算，算法不读旧结果来选择时机。原局部奖励、权重、捕食者、历史朝向、四邻接、目标/暂缓和资源约定不变；H与initial_targets不修改。U连通块不是F飞行连通块。此策略不覆盖单块有价值入口等全部机会，不声称E是收益必要或充分条件。','',
    'PPCPP为冻结独立适配版，FIRST为原首次恢复实现逐字节副本。ONE保留同样结构检查，但只求原入口，专用于等价验收，不参加正式性能排名。所有分支路径/trace/pending私有，仅共享静态F几何。','',
    '## 2. 先验收再开跑','',
    f"门槛共{g['calls']}次：64微型子集×4=256，47开发输入×4=188，3边界×4=12，固定分组456；首次/第二次触发各1次检查点发现，分见证逐点截止注入{sum(g['deadline_stage_calls'].values())}次，另3次不直接抛异常的时钟推进测试。预期失败与完整结果均保存于gates.jsonl，不能把它们全称作成功路线。",
    '验收包括ONE与原版完整route/trace等价、STRUCT原分支等价、真实输入不变、独立并查集/BFS审核触发条件与所有窗口、只首个E真触发、第二窗口后无新增结构检查，以及逐候选的原奖励/恢复/采集/返航。原分支已完整后在替代开始截止仍整体拒收；在分块访问、结果输出等推进时钟也诚实拒收。','',
    '通过后原20道路状态与受控27输入，三方法×两固定种子=282次全新调用；旧结果只作逐路线/trace预测核对，不拼入本批计时或排名。独立进程串行、方法次序轮换、线程数1、20秒共同暖入口。两个种子不算独立地图。','',
    table(['批次/方法','完整合法及时/调用','完整及时状态数','有完整试走的状态数','非原分支获选状态数'],[[b+'/'+m,f"{v['eligible']}/{v['calls']}",v['complete_timed_states'],v['triggered'] if m!='PPCPP' else '—',v['selected_alternative'] if m!='PPCPP' else '—'] for b,z in s.items() for m,v in z['methods'].items()]),'',
    '## 3. 同批路程比较','',
    table(['批次/前者_vs_后者','共同完整及时状态','短/平/长','前者/后者总步数','净差','逐状态相对差均值'],[[b+'/'+name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}" if v['mean_relative'] is not None else '—'] for b,z in s.items() for name,v in z['pairs'].items()]),'',
    '负差为前者更短，两个批次分开，逐状态平均与总量比例不混称。全程超时/失败保留，不能以缺失路线计0；如有非及时结果，比较表只用共同完整及时交集并明确样本数。各方法的其他指标总计仅对其完整及时状态，若样本不同不能横向直接比总量。','',
    '## 4. 所有方法完整指标','']
    fields=[('length','含返航总步数'),('fresh_target_steps','新采集移动'),('historical_target_steps','历史重复'),('repeated_new_target_steps','本轮重复'),('non_target_steps','非目标移动'),('turns90','90度转弯'),('turns180','180度折返'),('direction_changes','总方向变化'),('completion_step','覆盖完成前步数'),('return_tail_steps','返航尾段（已含）'),('initial_credit','起点即时新采集'),('remaining_before','扣H后待检（含起点）'),('newly_completed','本轮完成待检'),('active_targets','当前可检格次'),('active_covered','可检已完成格次'),('missing_active','可检遗漏'),('published_targets','已公开目标格次'),('published_covered','已公开已完成格次'),('deferred','暂缓格次'),('uncompleted_published','已公开未完成格次'),('target_arrivals','目标到达步数'),('duplicate_target_arrivals','重复目标到达步数')]
    for b,z in s.items():
        lines += ['### '+b,'',table(['指标（每状态一次）']+list(ms),[[label]+[z['methods'][m]['totals'][k] for m in ms] for k,label in fields]),'',table(['比率（计数加权）']+list(ms),[[label]+[f"{z['methods'][m]['totals'][k]:.4%}" if z['methods'][m]['totals'][k] is not None else '—' for m in ms] for k,label in [('remaining_completion_pooled','剩余任务完成率'),('active_coverage_pooled','当前可检覆盖率'),('published_coverage_pooled','全部已公开覆盖率'),('overlap_pooled','目标到达重复比例')]]),'']
    lines += ['四分类移动之和等于总步数；返航只是其中一部分，不再相加。暂缓不计完成。格次跨快照重复，不代表唯一物理面积。转弯按输出路线连续边统计，未额外加入历史朝向与输出首边间的角度；历史朝向仍实际影响决策。','',
    '## 5. 全程时间与真实结构开销','',
    table(['批次/方法','均值秒','中位秒','P95秒','最大秒'],[[b+'/'+m]+[f"{v[k]:.6f}" for k in ('time_mean','time_median','time_p95','time_max')] for b,z in s.items() for m,v in z['methods'].items()]),'',
    table(['批次','STRUCT结构检查状态窗口数','第一/第二窗口实际触发状态数','STRUCT/FIRST完整试走状态数'],[[b,z['methods']['STRUCT']['structural_checks'],f"{z['methods']['STRUCT']['trigger_at_first']}/{z['methods']['STRUCT']['trigger_at_second']}",f"{z['methods']['STRUCT']['triggered']}/{z['methods']['FIRST']['triggered']}"] for b,z in s.items()]),'',
    '共同暖入口计入JSON解析/验证、Snapshot构造、结构与前置候选距离、原策略执行、所有分支仿真/审核及完整原始结果编码，另审调用者墙钟<20秒；输入文件读写、进程启动/导入和外部独立复核不计，三方法相同。90秒看门狗不扩大预算。超时整体拒收，完成分支仅留诊断，不用保底掩盖迟到。','',
    '分块遍历线性，但本实现为确定性分块编号排序U，含O(|U|log|U|)排序与O(|U|)存储；另需F上的候选最短距离。实际都计时，不能把少触发几个状态当作节省同等比例计算。只报告本批本机测量，两个重复不足以证明稳定速度差，更不保证任意预算及时率。','',
    '## 6. 逐道路状态','',
    table(['状态','PPCPP','FIRST','STRUCT','STRUCT−FIRST','STRUCT触发窗口','结构检查数/完整分支数'],[[x['case_id']]+[x['methods'][m]['metrics']['length'] if x['methods'][m]['metrics'] else '无完整路线' for m in ms]+[x['methods']['STRUCT']['metrics']['length']-x['methods']['FIRST']['metrics']['length'] if all(x['methods'][m]['metrics'] for m in ms) else '—',x['methods']['STRUCT'].get('trigger_recovery'),str(len(x['methods']['STRUCT'].get('windows',[])))+'/'+str(x['methods']['STRUCT']['candidates'])] for x in a['states'] if x['batch']=='original20']),'',
    '## 7. 当前结论的边界','',
    '这一轮实现的是固定两个恢复窗口、至多一次结构触发完整试走，不是任意窗口智能触发器，也不是FIRST与SECOND的免费逐状态最优。已知case01单块仍可省2步而本规则会放过；case11两窗口E都真，规则先触发，不一定达到SECOND更短路线。反例不因本轮净收益而消失。','',
    '开发收益若小，不能自动认为算法复杂度值得；结构条件可能在新地图增加前置计算又不能触发，也可能错过同块有价值入口。当前原分支保留解释部分“不更长”，不能把它当强泛化或创新证据。本批全部输入已见，重复使用并不提供独立泛化验证。','',
    '按本轮协议停止，不调结构阈值、不继续第三第四窗口、不叠加候选或多次试走。下一步应依据本轮质量—开销是否值得，选择独立开发验证或停止这个候选，而不是继续同批上无限诊断；留出仍未使用。','',
    '## 8. 重放与证据','',
    '预登记.md与protocol.json固定开跑前规则/输入/来源/源码；gates.jsonl含全部门槛原始输出；execution含282新调用及完整route/trace/窗口；analysis.json含全部指标、候选成本和两批统计。verify.py只读重审源哈希、独立结构/逐决策、双指标、原分支等价与既有两窗口重放预测、跨种子完整trace以及全部统计；manifest.json封存本目录。','',
    '```powershell',"& './运行环境/python/python.exe' -B -X utf8 'PPCPP两窗口结构候选_v0.1_20261020/verify.py'",'```','',
    '旧冻结基线和实验不改，未推送GitHub。验收完成不等于论文算法复现或创新已经完成。','']
    (H/'两窗口结构候选开发结果与判断_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()
