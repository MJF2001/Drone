from common import *
import csv
def table(head,rows):return '\n'.join(['|'+'|'.join(map(str,head))+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(map(str,row))+'|' for row in rows])
def main():
 a=read(H/'analysis.json');rows=a['states'];report=[]
 def add(x):report.append(x)
 add('# PPCPP保留末采集格候选：实现与开发验收结果\n\n2026-10-20。候选PPCPP_LAST_RESERVE_v0.1，简称LAST。**执行完成，待负责人审核**。只通过当前开发可行性检查，不确认为主算法或论文创新。')
 add('## 结论与性质\n\n固定60开发状态×两方法×3重复=360次新正式调用，全部完整合法及时，无截止/异常/看门狗；三个重复完整route/trace稳定。主36：8短28平0长，总430→414少16步（3.7209%，逐状态平均减少2.7720%）。补24：2短22平0长，266→262少4步（1.5038%，逐状态平均减少1.1040%）。分别计状态一次，重复不是新地图。')
 add('主批改善来自L/Z两道路族、4个非等价已知几何组，各两相关历史进度；补批2改善仍是原一个L形拐扩几何。当前固定实现达到“跨不同族/非等价几何有严格改善、正确且及时”的开发可行性门槛，但输入全是已见开发回测，不能当独立新验证。未启动大图或强P2共同预算比较。')
 add('原已最优状态全部保留：主批原28/36最优，LAST32/36最优；补批原22/24，LAST24/24。主批理论28步追回16，仍剩12；补批4步全追回。最终完整成功不长于原版，主要由保留P0并严格比较的构造保证，不能把零退化率当创新。')
 add('## 策略性保留如何实现\n\n真实F/T/H/公开与暂缓账本不改。U=T-H-{current}，e按原F至基地的最短图距离和坐标序选择；不读取原路线结束格或精确结果。P0先由冻结原版完整求解，失败则直接失败。P1从真实原位置/朝向用私有状态重来；阶段一F_work=F-{e}、pending=U-{e}，仍用原奖励、最近恢复和原连接器，沿途逐格采集。只检查阶段一待检可达，不套用即时返航预检；阶段二恢复F，到e再返航，按真实原输入审核。仅严格更短采用P1，同值保P0。e不是物理障碍，不能记暂缓或提前经过不采集。')
 add('变化代码集中candidate.py：输入候选距离、私有work_snapshot、工作待检可达检查（不用work.precheck）、原局部/恢复在F_work运行、release恢复F的两段连接、完整审核和严格择优。P0通过原native.solve调用不改；runtime.py只统一入口截止/编码/ONE消融，worker.py只管理输入与读路径审计。原奖励权重/捕食者/历史朝向/tie规则均不改。')
 add('全程同一个20秒截止，包含解码/验证/构造/P0/e距离/工作缓存/P1/审核/完整原输出编码。P0和P1没有各自20秒；即便P0完成，只要整体晚到，route为空且不作为及时输出接受。诊断分支继续保留。启动/导入、磁盘、外审不计。各输入统一1000000距离预算，当前小图不活跃。')
 add('## 门槛与版本记录\n\n首次gates.py导入时碰到冻结代码同名audit.py，门槛调用0、正式0；失败脚本/gates.log保留。另版gates_v02.py仅显式按绝对路径加载本地审核器，不改候选或审核公式。随后218门槛调用全通过：180开发（60输入×PPCPP/ONE/LAST）、27固定夹具（9×3）、1缓存Spy、9截止注入、1原分支失败。另8次仅夹具精确last查询离线核验P1不短于最优，不计正式求解。')
 add('60组三方法门槛核对ONE完整route/trace及LAST中P0等于当次原版；正式180状态-重复组P0仍逐路线/trace等于同批原版。全部原分支和P1的成功轨迹独立重算原奖励、工作图BFS最近恢复、逐格采集、保留e不提前进入、release后原图连接及最终择优。三种图缓存是独立对象，Spy核其free/cache/distance_rows；输入未改，P0在P1前后完整序列化一致。')
 add('固定夹具覆盖空任务、单任务、当前位置即时采集、候选同距、e必经导致reservation_infeasible、e=base移除后基地不可达但其他任务仍可完成、障碍图距离、恢复连接逐格采集、历史目标后来被挡。实际最近恢复不会在去最近目标之前途经更近待检格，故“沿途多目标采集”另用真实append_segment收集器的固定远端连接单测，不假造原生恢复例。')
 add('9个可控时钟推进注入分别在P0完成、候选距离、phase1、release、return、最终审核前/后、编码前/后。每次P0已完整，整入口仍deadline拒收，未回填P0。原分支资源不足另1夹具，未生成P1。全部固定门槛通过后source_seal冻结，再开始360正式。')
 add('## 分批正式结果与候选状态')
 add(table(['批次','状态','完整及时调用','短/平/长','原总步','LAST总步','省步','P1短/平/长','空U','原最优→最终最优'],[[b,s['states'],s['states']*6,f"{s['short']}/{s['equal']}/{s['long']}",s['PPCPP'],s['LAST'],s['saved'],f"{s['P1_short']}/{s['P1_equal']}/{s['P1_long']}",s['P1_statuses'].get('empty_U',0),f"{s['baseline_optimal']}→{s['final_optimal']}"] for b,s in a['batches'].items()]))
 add('主批35替代完整、1空任务；补批23替代完整、1空任务。正式reservation_infeasible=0、P1异常=0、原分支失败=0、整体截止=0；策略性不可达只在门槛观察到，不补正式图。主批5条、补批6条更长替代均保存并保P0；主22条/补15条同长也保P0。按三重复调用计，LAST180次含174完整P1、6空U；选P1共30次，对应10个状态。')
 for batch in ('main36','supp24'):
  add('## '+batch+'：全部逐状态')
  rr=[r for r in rows if r['batch']==batch];heads=['状态','原P0','P1','选中','LAST','L*','追回','剩余差','e','P1−Lnear','额外工作连接步']
  tab=[]
  for r in rr:tab.append([r['name'],r['PPCPP_metrics']['length'],r.get('P1_metrics',{}).get('length','不适用'),r['selected'],r['LAST_metrics']['length'],r['reference']['Lstar'],r['saved'],r['final_gap'],r['e'],r.get('P1_minus_Lnear','无参考'),r['audit']['extra_work_connection_steps']])
  add(table(heads,tab))
  with (H/f'{batch}_状态表.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(heads);w.writerows(tab)
 add('## 已知理论差距：实际追回与未实现的潜力')
 gaps=[r for r in rows if r['reference']['original_gap']>0]
 add(table(['状态','原理论差','追回','最终剩余','Lnear','P1','P1−Lnear','达到L*'],[[r['id'],r['reference']['original_gap'],r['saved'],r['final_gap'],r['reference']['Lnear'],r['P1_metrics']['length'],r['P1_minus_Lnear'],r['final_gap']==0] for r in gaps]))
 add('十个已有差距状态均实际缩短2步；主批4个达到L*、另4个未达（L拐扩25%剩2、Z直扩25%剩2、Z拐扩两进度各剩4）。这些未达例e的既有Lnear=L*，说明候选格本身可达到最优，但当前PPCPP式行进没有实现其完整潜力，不是需要再猜一个末采集格才能解释。补2例均达到L*。不据此追加搜索/候选或精确补全。')
 add('主批全部35成功P1都有同输入/同last的既有Lnear界，均未突破该下界。补批原24协议只有全局和原结束格查询，没有为所有最近格做C：23成功P1中15有可用界（同last旧查询，或全局下界加同last最短见证给出等号），8个无对应最近格最优参照，明确记无参考，不新增端点查询。两旧正例属于全局最短见证的最后格恰为e，因此受限最优可证明等于L*；不是重新运行了精确求解。所有参考只在360调用结束后离线读，输入哈希一致才用。')
 add('## 五个已知近基地反例：正确保原但仍付计算')
 known=['narrow_I_straight_p25','narrow_I_straight_p60','narrow_L_straight_p60','narrow_Z_straight_p60','narrow_Z_obstacle_p60'];counter=[r for r in rows if r['batch']=='main36' and r['name'] in known]
 add(table(['状态','P0','P1','Lnear','选中','原均值ms','LAST均值ms'],[[r['name'],r['PPCPP_metrics']['length'],r['P1_metrics']['length'],r['reference']['Lnear'],r['selected'],f"{sum(r['PPCPP_entry_times'])/3*1000:.6f}",f"{sum(r['LAST_entry_times'])/3*1000:.6f}"] for r in counter]))
 add('5例P1均比P0长2步，均保留P0；这说明完整成本比较能排除这里的坏替代，不是近基地候选没有坏处。所有额外计算仍计入LAST入口，不能把未选P1的代价删掉。')
 add('## 临时禁入的额外通路成本\n\n对所有P1阶段一连接，用实际F_work路径长度减原F同端点BFS距离独立重算：主批合计10步、补批10步（每状态一次，含未选替代）；每段起止/长度/原图距离见analysis.states.audit.work_segments。它衡量临时禁入对相同连接端点的代价，不等于P1对P0的总差，也不能再次与净省步相加。物理账本未改、e仍属待完成任务；真实障碍的暂缓和此策略禁入有本质不同。')
 add('## 完整指标\n\n每状态一次；P1主35/补23，与最终主36/补24分母不同，不能直接比较总量。四分类之和=总步，返航已含。')
 keys=['N','length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','initial_credit','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','target_arrivals','duplicate_target_arrivals','active_coverage','published_coverage','overlap']
 for batch in ('main36','supp24'):
  add('### '+batch)
  add(table(['指标','PPCPP','LAST','P1全部成功替代'],[[k]+[a['metric_totals'][batch][m][k] for m in ('PPCPP','LAST','P1')] for k in keys]))
 add('主批净少16全部来自非目标移动203→187，历史重复18、本轮重复26不变；90度129→143增加14，180度22→15减少7，不能称全部指标改善。覆盖阶段223→227多4，尾段207→187少20，净少16。补批本轮重复14→12、非目标108→106各少2，90/180不变81/6，覆盖阶段151不变、尾段115→111。转弯不能推真实能耗。')
 add('两批可检与待检完成100%、漏检0。主公开306完成297/暂缓9，97.0588%；补公开224完成219/暂缓5，97.7679%。历史后来被物理障碍覆盖仍保留已完成；策略性保留e不改变这些数值。格次共享地图，不是独立物理面积。')
 add('## 时间：额外计算不能忽略')
 tt=[]
 for batch,methods in a['timing'].items():
  for method,t in methods.items():tt.append([batch,method,t['N']]+[f"{t[k]*1000:.6f}" for k in ('mean','median','p95','max')])
 add(table(['批次','方法','调用N','均值ms','中位ms','P95ms','最大ms'],tt))
 ratios={b:a['timing'][b]['LAST']['mean']/a['timing'][b]['PPCPP']['mean'] for b in a['timing']}
 add('LAST均值为原版：主%.4f倍、补%.4f倍。绝对小图耗时约1毫秒，仍约增加一倍实际计算，不能仅凭20秒内完成就说开销可忽略。这是同机同批暖入口，3重复不足稳定速度或跨机器/大图结论；不拼旧计时。P95按(n−1)×0.95线性插值。'%(ratios['main36'],ratios['supp24']))
 ph=[]
 for batch,methods in a['phase_timing'].items():
  for method,v in methods.items():ph.append([batch,method]+[f"{v[k]*1000:.6f}" for k in ('p0','candidate','p1','final_audit','encoding')])
 add(table(['批次','方法','P0 ms','候选ms','P1含分支审核ms','最终审核ms','编码ms'],ph))
 add('分段仅供解释，P0已含原内部审核，P1已含替代审核；额外预处理、输入解码/构造、P0完整性快照/隔离验证、选择和框架成本在总入口内，不把分段和当总时间。统一比较使用完整总入口。')
 add('### 每状态3次入口时间（毫秒）')
 timerows=[[r['id'],', '.join(f'{t*1000:.6f}' for t in r['PPCPP_entry_times']),', '.join(f'{t*1000:.6f}' for t in r['LAST_entry_times'])] for r in rows];add(table(['状态','PPCPP r0/r1/r2','LAST r0/r1/r2'],timerows))
 with (H/'全部调用时间与分段.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['id','batch','method','repetition','eligible','status','entry_seconds','p0','candidate','p1','final_audit','encoding'])
  for x in a['calls']:w.writerow([x[k] for k in ('id','batch','method','repetition','eligible','status','entry_seconds')]+[x['phases'].get(k,0) for k in ('p0','candidate','p1','final_audit','encoding')])
 add('## 生产读取隔离与复核\n\n正式worker为独立进程，先导入冻结源码和本地runtime/candidate，再开启求解期只读allowlist：只允许唯一原始输入文件，其余读取报错；360调用的runtime_reads均仅该输入，导入模块来源也保存，无exact.py/independent.py/分析模块。生产代码没有读取旧route/最优值/实验标签选e。输入文件读取、进程启动/导入在计时外；解码及全部算法/原结果编码计时。参考路径与哈希另封reference_seal，仅由全部正式结果完成后的离线analyze使用，不是操作系统级沙盒声明。')
 add('完整输出保存jobs/execution、360调用台账和运行日志；gate_index逐条218门槛、8夹具最优界、source_seal/protocol固定来源。verify_v02.py只读重审全部门槛/截止、360双指标及分支动作、180P0配对、120方法状态组的3重复稳定性、参考界、60行报告和manifest。不重跑正式求解或精确查询。')
 add('## 固定图示与缺类\n\n严格改善最大同值编号最小与有理论空间未完全追回最小均为main36__wide_L_corner_p25，复用同图。P1更长最小为main36__narrow_I_straight_p25。正式策略性不可达缺类，不拿门槛补正式图。')
 for name in dict.fromkeys(v for v in a['selected'].values() if v):add(f'![{name}](figures/{name}.png)')
 add('## 偏差、局限与停止\n\n唯一执行故障为门槛审核模块导入冲突，另版运行器修复；正式0失效、0重跑，未调规则或参数。补批8成功P1没有既有同last最优参照，明确未做该项精确差距判断，未补额外查询；其合法性/动作仍完整审核。所有预定夹具和截止门槛均在正式前完成。')
 add('交付审核首次verify.py在完整重审后比较analysis时遇到重算work_segments.goal为tuple、保存JSON为list的表示差异，AssertionError；原脚本及delivery_verify_v01_failure.json保留。另版verify_v02.py只在整表比较前规范化JSON表示，审核通过。正式候选/输入/结果不变，正式失效/重跑均0；详见交付审核器v0.2影响说明.md。')
 add('当前有跨L/Z几何的实际严格收益，可以称“该固定实现通过开发可行性检查”。证据仍是已见小图、紧凑阶梯带、单一PPCPP历史来源、宽松资源和固定基地/捕食者；正例集中既有宽规格。没有新独立开发验证、大图可扩展性、强P2同预算胜率或论文创新证据。保留一个候选和全部不利分支，到此停止；后续验证须另立方案，不自动加终点/恢复窗口/奖励或精确补全。未用留出、不改旧冻结/封存、不提交推送GitHub。')
 add('## 交付与命令\n\n**执行完成，待负责人审核。**\n\n```powershell\n& ./运行环境/python/python.exe -B -X utf8 PPCPP保留末采集格候选_v0.1_20261020/verify_v02.py\n```\n\nREADME和review_packet说明复核、代码差异与原始证据映射。')
 (H/'保留末采集格候选开发结果.md').write_text('\n\n'.join(report)+'\n',encoding='utf-8')
if __name__=='__main__':main()
