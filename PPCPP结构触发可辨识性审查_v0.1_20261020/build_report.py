import json
from pathlib import Path
H=Path(__file__).resolve().parent
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def main():
    a=json.loads((H/'analysis.json').read_text(encoding='utf-8'));ss=a['summary'];misses=[(batch,m,q) for batch,s in ss.items() for m,v in s['features'].items() for q in v['missed_improved']]
    lines=['# 候选跨剩余任务块，能否作为试走触发门槛？','','2026-10-20。只读结构设计审查v0.1，不是新算法性能实验。**新求解0，规划器修改0，读取47状态、94份FIRST/SECOND保存结果，实际69个触发检查点；另读47份共同原版作参照。**','',
    '## 1. 问题、规则与事先约束','',
    '不再逐次试第三、第四个恢复编号，先检验一个没有数值阈值的结构解释：当三个候选覆盖至少两个不同的剩余任务连通块时，才值得进行一次完整后续试走。它只是候选规则，不是已证明的必要条件。','',
    'U为预测尚未采集的目标格，按U自身四邻接分块；原最近/基地最近/基地最远三种入口规则保持不变。定义E为“去重后的候选入口至少分属两个U连通块”。F是允许飞行空间，U分块不等于F不连通；不改任务格、不改已检历史、不加入规整度奖励。','',
    '在提取该新结构特征前，审查前规则.md及源码/输入/上游文件哈希已固定。只检验这个谓词，不根据反例再筛面积、边界、孔洞、距离或比例阈值。先问它能否作为保守过滤门槛而不丢掉本批任何已有严格收益；即使未丢收益，还要至少过滤一例无改善尝试才有跳过试走的结构证据。这不是普遍算法验收标准。','',
    '## 2. 观察到的门槛漏判','',
    table(['批次/时机','已有触发','E真','已有严格改善','改善中E真','漏掉改善','过滤无改善'],[[b+'/'+m,v['triggered'],v['eligible'],v['known_improved'],v['retained_improved'],len(v['missed_improved']),len(v['skipped_no_improvement'])] for b,s in ss.items() for m,v in s['features'].items()]),'',
    ('**存在已确认的严格改善被E过滤，因此不能把E当作“改善的必要条件”或无损过滤门槛。本轮不据此实现正式新规划器。**' if misses else '**本批没有发现E过滤已有严格改善，但这只通过了保存路线上的保守筛查，不证明必要性、泛化有效或真实运行更快；还须检查是否实际跳过无改善及计算代价。**'),'',
    '“漏判”指相应FIRST或SECOND保存路线确实比同批原版更短、但E为假；这不是统计分类器的独立测试准确率。当前输入已用于设计其他版本，不是独立测试数据。','',
    table(['被过滤的已有改善','U块数','候选覆盖块数','原版→该时机','全部候选入口'],[[b+'/'+q+'/'+m,next(x for x in a['states'] if x['batch']==b and x['case_id']==q)['features'][m]['component_count'],next(x for x in a['states'] if x['batch']==b and x['case_id']==q)['features'][m]['candidate_component_count'],str(next(x for x in a['states'] if x['batch']==b and x['case_id']==q)['metrics']['PPCPP']['length'])+'→'+str(next(x for x in a['states'] if x['batch']==b and x['case_id']==q)['metrics'][m]['length']),next(x for x in a['states'] if x['batch']==b and x['case_id']==q)['features'][m]['candidate_goals']] for b,m,q in misses]),'',
    '## 3. 两种固定规则的保存路线回顾性记账','',
    'FIRST_FILTER：第一次恢复E真才使用已有FIRST选中完整路线，否则用原版。TWO_WINDOW_REPLAY：在已有第一/第二恢复检查点中用首个E真的时机，触发后唯一试走机会即消耗，无论是否选到非原分支；两窗口都不满足则用原版。不触发第一次时原策略前缀与已有SECOND一致，因而在这两个窗口内可重放。没有计算第三个窗口，没有实现任意恢复上的在线结构触发器。','',
    '选择函数只读结构特征，不读哪条路线更短来挑时机。读取两版已有结果作审查和记账，不代表实际运行时可以免费提前知道第二次状态。没有测定结构计算/候选距离/完整仿真的共同耗时，不把旧方法计时混成新方法时间或成功率。','',
    table(['批次','原版总步数','FIRST','SECOND','FIRST_FILTER保存路线','TWO_WINDOW保存路线'],[[b,sum(x['metrics']['PPCPP']['length'] for x in a['states'] if x['batch']==b),sum(x['metrics']['FIRST']['length'] for x in a['states'] if x['batch']==b),sum(x['metrics']['SECOND']['length'] for x in a['states'] if x['batch']==b),s['replay']['FIRST_FILTER']['totals']['length'],s['replay']['TWO_WINDOW_REPLAY']['totals']['length']] for b,s in ss.items()]),'',
    table(['批次/规则','使用原版/FIRST/SECOND状态数','对原版短/平/长','对FIRST短/平/长','对SECOND短/平/长'],[[b+'/'+policy,'/'.join(str(v['source_counts'][m]) for m in ('PPCPP','FIRST','SECOND'))]+['/'.join(str(v['pairs'][m][k]) for k in ('shorter','equal','longer')) for m in ('PPCPP','FIRST','SECOND')] for b,s in ss.items() for policy,v in s['replay'].items()]),'',
    '以上是规则在已有完整分支上的回顾性路程核算，不是新增方法的实验成绩，即使数值有利也不能直接晋升。原20与受控27分开，不合成一个泛化分数。','',
    '## 4. 回顾性完整指标','']
    fields=[('length','含返航步数'),('fresh_target_steps','新采集移动'),('historical_target_steps','历史重复'),('repeated_new_target_steps','本轮重复'),('non_target_steps','非目标移动'),('turns90','90度转弯'),('turns180','180度折返'),('direction_changes','总方向变化'),('completion_step','完成覆盖前步数'),('return_tail_steps','返航尾段（已含）'),('remaining_before','起点采集前待检'),('newly_completed','本次完成待检'),('active_targets','当前可检目标格次'),('active_covered','可检已完成格次'),('missing_active','可检遗漏'),('published_targets','已公开目标格次'),('published_covered','已公开已完成格次'),('deferred','暂缓格次'),('uncompleted_published','已公开未完成格次'),('target_arrivals','目标到达步数'),('duplicate_target_arrivals','重复目标到达步数')]
    for b,s in ss.items():
        lines += ['### '+b,'',table(['指标','FIRST_FILTER','TWO_WINDOW_REPLAY'],[[label]+[s['replay'][policy]['totals'][key] for policy in ('FIRST_FILTER','TWO_WINDOW_REPLAY')] for key,label in fields]),'',table(['比率（计数加权）','FIRST_FILTER','TWO_WINDOW_REPLAY'],[[label]+[f"{s['replay'][policy]['totals'][key]:.4%}" for policy in ('FIRST_FILTER','TWO_WINDOW_REPLAY')] for key,label in [('active_coverage_pooled','当前可检覆盖率'),('published_coverage_pooled','全部已公开覆盖率'),('overlap_pooled','目标到达重复比例')]]),'']
    lines += ['没有新增运行，故没有新规划时间、超时率和独立成功率表。四分类移动和为总步数，返航不重复相加；暂缓不计完成。已公开格次跨快照重复，不是唯一物理面积。所有数据来自已合法验收的保存路线，不代表新门槛实现已经验收。','',
    '## 5. 每状态的两个结构检查点','',
    '每个窗口显示U块数/候选覆盖块数；—表示原版本身未到达该恢复位置。E取决于第二个数是否至少2，不读取收益。','',
    table(['状态','FIRST 块数/候选块数','FIRST E','SECOND 块数/候选块数','SECOND E','两窗口选中来源'],[[x['batch']+'/'+x['case_id']]+sum(([str(x['features'][m]['component_count'])+'/'+str(x['features'][m]['candidate_component_count']) if x['features'][m]['triggered'] else '—',x['features'][m]['eligible']] for m in ('FIRST','SECOND')),[])+[x['selections']['TWO_WINDOW_REPLAY']] for x in a['states']]),'',
    '## 6. 开销、边界和停止规则','',
    'U四邻接分块本身时间/空间均为O(|U|)，还需获得原最近/基地近/基地远三个候选的图距离，后者不能当免费。当前rollout实现先算完整原分支才生成额外入口，若真要用E节省完整试走，须另实现前置候选生成并重新验收截止与计时；仅后置加一个if不等于已节省计算。','',
    '一个U连通块可以很长、有转角、有障碍边界或多种入口，仍可能因入口和覆盖方向不同产生完全不同的结束点。同样，多个U块且候选跨块也不保证有净收益；原版可能已经很好，或更远衔接抵消后续收益。E最多是结构机会描述，不能自动当作总成本估计。','',
    '按审查前约定只检验一次这个谓词，不从本轮结果追加其他特征/阈值。若不能通过无损门槛审查，就保留为否定证据，不拿总体步数“还不错”掩盖漏判。后续提出另一机制必须独立说明目的和预算，不持续堆叠规则追求开发数据最好。','',
    '## 7. 证据和复核','',
    'protocol.json固定特征提取前规则、输入和来源；analysis.json含47状态两检查点、完整指标、来源路径和两规则回顾记账；rule.py只做分块/特征和不读结果的结构选择；audit.py不调用任何规划器；verify.py用独立并查集核验全部分块和选择，双指标复核193条候选保存分支，另有5个空/单格/对角/连通/分离夹具，不算地图实验。manifest.json封存本次交付。','',
    '```powershell',"& './运行环境/python/python.exe' -B -X utf8 'PPCPP结构触发可辨识性审查_v0.1_20261020/verify.py'",'```','',
    '旧实验和冻结源码不改，未使用留出，未推送GitHub。本文不宣称自适应触发已实现、没有额外算法成本或已确认创新。','']
    (H/'结构触发审查结果与设计取舍_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()
