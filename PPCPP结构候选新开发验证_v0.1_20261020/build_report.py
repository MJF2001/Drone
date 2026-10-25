from common import H,read
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def main():
    a=read(H/'analysis.json');s=a['summary']['newdev36'];st=read(H/'strata.json');ia=read(H/'input_audit.json');ms=('PPCPP','FIRST','STRUCT')
    lines=['# STRUCT冻结后新开发矩阵：验证结果与保留判断','','2026-10-20。冻结原STRUCT v0.1、FIRST、PPCPP的6个运行/审核模块逐字节复用，没有为新输入调规则。**本轮不是最终留出，也不是36张统计独立地图：36快照来自6个初始基础道路、18个事件构型，5个计时重复不扩充地图样本量。**','',
    '## 1. 固定了什么，验证什么','',
    '在准备与生成前预登记参数和来源哈希。小/中/大(L,w)为(18,3)/(42,5)/(84,9)，A水平带、B末端向上L形；分别直线扩展、拐角扩展、新障碍，历史进度25%/60%，共36快照。公开飞行矩形只按尺寸预设，不从未来事件裁剪；基地(1,1)、捕食者(-1,0)，四邻接等长，单格向下采集，障碍禁飞且遮挡，暂缓不算完成。','',
    '本轮问题是既有结构规则能否在首次生成的新开发输入保留净收益，不是继续解释旧47状态或筛出有触发的新地图。生成规则由已知旧结果者制定，是冻结后开发验证，不是盲测或最终泛化验收。全矩阵一次，不因结果或是否触发筛图。','',
    '## 2. 历史与可行性证据','',
    '先6次独立进程原PPCPP准备调用，只给事件前目标和公开飞行域，H为空、起点基地、朝向为空，不传未来事件或见证。按实际模拟执行轨迹，首次采集到ceil(25%/60%×原目标数)时截取前缀，H精确为这段轨迹在事件前目标中的采集集合，当前位置/上一格和旧后缀均来自保存计划。每个基础计划共享产生6个快照，不能称36份独立历史。','',
    '另一独立实现逐格审核36段历史、6个初始地图和事件足迹；构造36条新地图覆盖返航可行见证并双指标核对。这些见证从未传入算法或作为候选。统一宽松移动预算1000000，不研究真实能耗或紧资源调度。输入及平移规范化签名与旧47状态均不重复；这只能排除直接复用，不等于统计独立。','',
    table(['基础道路','初始目标数','准备完整路线步数','准备暖入口秒'],[[path.stem,len(read(H/'prep/inputs'/path.name)['targets']),len(read(path)['raw']['route'])-1,f"{read(path)['entry_seconds']:.6f}"] for path in sorted((H/'prep/results').glob('*.json')) if not path.name.endswith('.job.json')]),'',
    '准备费用单独披露，所有事件后方法共享同一真实历史，不算进事件后求解排名。该历史来源只用PPCPP，尚未验证其他初始规划来源。新障碍半带位置只按预设位置与避免当前格的规则确定，上下半带切换记录在见证中；进度组并非严格单因素因果实验。','',
    '## 3. 门槛与正式调用','',
    '新输入预检/封存后，36状态×原PPCPP/ONE=72次等价门槛调用，验证同结构只原入口时完整route/trace与原版一致、真实输入不变、独立窗口/奖励/采集规则。门槛也使用这批输入，不能称未看过的正式盲测；它的时间不混入正式成绩。','',
    '然后36状态×3方法×5固定种子=540次全新正式调用。串行独立进程、方法轮换、线程限制1、共同20秒暖入口，所有源结果保留。输入解码验证、Snapshot构造、结构和候选距离、全部分支及内部审核、完整原结果编码均计时；启动/导入、文件读写和外部独立审计不计。另审调用者墙钟<20秒，90秒看门狗不扩充预算。','',
    table(['方法','完整合法及时/调用','全部5重复及时状态','完整试走状态','选非原分支状态'],[[m,f"{s['methods'][m]['eligible']}/{s['methods'][m]['calls']}",s['methods'][m]['complete_timed_states'],s['methods'][m]['triggered'] if m!='PPCPP' else '—',s['methods'][m]['selected_alternative'] if m!='PPCPP' else '—'] for m in ms]),'',
    '## 4. 主比较：总量与逐状态','',
    table(['前者_vs_后者','共同及时状态','短/平/长','前者/后者总步数','净差','逐状态相对差均值'],[[name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}" if v['mean_relative'] is not None else '—'] for name,v in s['pairs'].items()]),'',
    '负差为前者更短。每状态路程计一次，5次完整路线稳定性另核对；实际时间使用全部5重复。迟到/失败不删除或计0，比较只在共同完整及时状态交集，数量明确列出。总量比例与逐状态相对差均值是不同口径；部分状态共享基础道路和历史，不能作为36个统计独立成功样本。','',
    '## 5. 分层结果（STRUCT对参照）','']
    for key,title in [('event','按事件'),('size','按尺寸'),('progress','按历史进度'),('layout','按基础布局')]:
        lines += ['### '+title,'',table(['分组/参照','共同及时状态','短/平/长','净步数差'],[[str(value)+'/'+ref,v['pairs'][ref]['common_states'],f"{v['pairs'][ref]['shorter']}/{v['pairs'][ref]['equal']}/{v['pairs'][ref]['longer']}",v['pairs'][ref]['difference']] for value,v in st[key].items() for ref in ('PPCPP','FIRST')]),'']
    fields=[('length','含返航总步数'),('fresh_target_steps','新采集移动'),('historical_target_steps','历史重复'),('repeated_new_target_steps','本轮重复'),('non_target_steps','非目标移动'),('turns90','90度转弯'),('turns180','180度折返'),('direction_changes','总方向变化'),('completion_step','完成可检覆盖前步数'),('return_tail_steps','返航尾段（已含）'),('initial_credit','起点即时新采集'),('remaining_before','扣H后待检（含起点）'),('newly_completed','本次完成待检'),('active_targets','当前可检目标格次'),('active_covered','可检已完成格次'),('missing_active','可检遗漏'),('published_targets','已公开目标格次'),('published_covered','已公开已完成格次'),('deferred','暂缓格次'),('uncompleted_published','已公开未完成格次'),('target_arrivals','目标到达步数'),('duplicate_target_arrivals','重复目标到达步数')]
    lines += ['## 6. 全部方法完整指标','',table(['指标（每状态一次）']+list(ms),[[label]+[s['methods'][m]['totals'][k] for m in ms] for k,label in fields]),'',table(['比率（计数加权）']+list(ms),[[label]+[f"{s['methods'][m]['totals'][k]:.4%}" if s['methods'][m]['totals'][k] is not None else '—' for m in ms] for k,label in [('remaining_completion_pooled','本次待检任务完成率'),('active_coverage_pooled','当前可检覆盖率'),('published_coverage_pooled','全部已公开覆盖率'),('overlap_pooled','目标到达重复比例')]]),'',
    '各方法总计仅对该方法全部5次完整及时的状态，若样本不同不可直接比较总量。四分类移动之和为路线步数，返航已含、不再相加；暂缓不计完成。格次跨事件/进度快照重复，不代表独立物理面积。转弯仅按输出连续边，不另加历史朝向至首边的角度。','',
    '## 7. 时间与结构实际开销','',
    table(['方法','均值秒','中位秒','P95秒','最大秒'],[[m]+[f"{s['methods'][m][k]:.6f}" for k in ('time_mean','time_median','time_p95','time_max')] for m in ms]),'',
    table(['方法','结构窗口检查数（每状态一次）','首/次窗口结构触发数','完整试走状态'],[[m,s['methods'][m]['structural_checks'],f"{s['methods'][m]['trigger_at_first']}/{s['methods'][m]['trigger_at_second']}",s['methods'][m]['triggered']] for m in ('FIRST','STRUCT')]),'',
    f"STRUCT对FIRST共{st['overall']['times']['paired_calls']}对实际调用：更快{st['overall']['times']['struct_faster']}、更慢{st['overall']['times']['struct_slower']}；每轮分方法均值见strata.json。5个重复仍不足以给硬实时保证或跨机器速度结论。少触发不等于按同等比例省计算；STRUCT的结构/候选距离和编码成本均已支付。",'',
    '## 8. 逐状态原始比较','',
    table(['状态','PPCPP','FIRST','STRUCT','STRUCT−FIRST','STRUCT触发窗口'],[[x['case_id']]+[x['methods'][m]['metrics']['length'] if x['methods'][m]['metrics'] else '无完整路线' for m in ms]+[x['methods']['STRUCT']['metrics']['length']-x['methods']['FIRST']['metrics']['length'] if all(x['methods'][m]['metrics'] for m in ms) else '—',x['methods']['STRUCT'].get('trigger_recovery')] for x in a['states']]),'',
    '## 9. 边界与本轮停止','',
    '新构造只覆盖矩形飞行域内两种多格宽道路，6基础图、18事件构型共享结构，不代表复杂道路、未知探索、连续多事件或真实飞行。历史来源单一，资源约束宽松，计算平台单一。生成方案利用了既有研究经验，不能把这批叫最终留出，也不能因生成后首次运行就宣称普遍泛化。','',
    '按预登记完成固定矩阵即停止，结果不利也不改参数重挑图。若旧收益消失，降级或停止该候选；若保留也先承认适用边界，再单独决定强基线对照和更广验证，不在本轮无限叠机制。所有反例、迟到、失败保留。原算法和旧实验不改，最终留出未用，未推送GitHub。','',
    '## 10. 证据与复核','',
    '预登记/spec/protocol固定生成前参数和冻结模块；prep为6准备调用，inputs/witnesses为36快照及72历史/未来见证；input_audit/input_seal为输入复核与哈希；gates为72等价门槛；execution为540新调用完整原始输出；analysis/strata为总体及分层完整指标。verify.py只读重审上述来源、见证、事件、逐候选机制、双指标、原分支及5重复稳定性；manifest封存交付。','',
    '```powershell',"& './运行环境/python/python.exe' -B -X utf8 'PPCPP结构候选新开发验证_v0.1_20261020/verify.py'",'```','']
    (H/'新开发验证结果与候选保留判断_20261020.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()
