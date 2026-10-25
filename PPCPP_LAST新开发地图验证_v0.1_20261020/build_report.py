from common import *
from analyze import timing
import csv
def table(headers,rows):return '\n'.join(['|'+'|'.join(map(str,headers))+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,row))+'|' for row in rows])
def main():
 a=read(H/'analysis.json');rows=a['states'];s=a['summary'];novel=read(H/'novelty.json');ia=read(H/'input_audit.json');report=[]
 def add(x):report.append(x)
 add('# LAST固定实现：新开发地图验证结果\n\n2026-10-20，v0.1。**执行完成，待负责人审核**。固定算法的新开发输入验证，不是最终留出、算法改进、强基线排名或论文主算法确认。')
 add('## 结论与实际取舍\n\n固定54槽位全部有效，9准备、108新输入原版/ONE等价及540正式调用完成。正式两方法各270/270完整合法及时，双方54状态均5次完整route/trace稳定。LAST对原版27短27平0长，总5530→5476省54步，总量减少0.9765%、逐状态相对差均值−1.6210%；没有排除失败后才得到的子集收益，本轮实际没有失败/迟到。')
 add('全部27改善状态均只省2步。改善分布于18个非旧复制、非D4等价事件后道路/遮挡组，I/L/Z各6组，达到运行前规定的“本固定新开发矩阵观察到跨形状收益保留”判据。最大改善单例省2，占总省54的3.7037%；绝对最大并非单例撑起总体，但中规格16状态贡献32步（59.2593%），仍须保留收益分布。')
 add('**路线收益保留，但计算开销明显扩大。** 原版入口均值6.462889ms，LAST90.339822ms，约13.9782倍；LAST最大0.639499秒。相同20秒上限不是相同实际CPU用量，及时不意味着开销可忽略。平均少不到1%的总路程，并且90度转弯增加，当前不能据此认定方法实际价值充分或批准主算法/强P2排名。先交负责人审核路程—计算取舍，本轮不改缓存或规则。')
 add('## 固定实现与问题口径\n\ncandidate.py/runtime.py/worker.py/audit.py/common.py与已审核LAST逐字节一致，原PPCPP、奖励、几何、模型与契约依赖受protocol/source_seal哈希保护。沿用单一输入最近基地e、F-e覆盖其他任务、恢复F到e返航、完整总步严格更短择优且同值保P0。原权重/捕食者(-1,0)/朝向/连接器/缓存作用域/截止均不变，无新终点、过滤、试走或精确补全。')
 add('四邻接等长、下视单格即时采集，历史保留。策略性禁入e不是真实障碍，不改F/T/H或暂缓；真实新障碍禁飞且遮挡，未完成被挡暂缓、历史已完成被挡仍保留。统一1000000步宽松距离预算，所有成功路线核验；不研究真实能耗或紧资源。没有完整P0时不替代补救；P1策略性不可达与整入口超时分开。整体20秒晚到拒收，P0仅诊断不能回填及时输出。')
 add('## 生成前几何与历史\n\n3族I/L/Z×3规格×3事件×30%/70%=54计划槽位；9基础道路共享历史，不是54独立地图。small/medium/large(L,w)=(6,2)/(12,3)/(24,4)，是本轮相对命名，不是真实大规模性能验证。各族直扩/拐扩均按L//2的固定新增长度，半带障碍固定首水平段中部、备用侧仅避免current，无第三位置。F按族/规格预先公开完整矩形，含道路外合法通路，未按事件裁域。')
 add('Z两角间不含角方块的独立直段为L-w=4/9/20格，分别至少2w；与上轮紧凑阶梯小图不同。原图/扩展无重叠、全宽末端接合，无分叉。m=3固定余量；域最大3036格、公开目标最大336，低于10000/1500上限。精确矩形坐标、ASCII全图在几何坐标表.json/几何概览.md，均在任何准备前固定。几何数量/连接/非重叠、障碍首备与所有冲突格、当前即时采集、历史被挡、保留连续通行带均在正式前preflight通过。')
 add('9次准备只输入当时初始任务/F，不给事件或可行见证。首次累计ceil(旧目标×30%/70%)截前缀，逐格H/current/previous及旧后缀保存；三事件共享同一历史。54历史与54当前覆盖返航见证由独立坐标谓词/路径/双指标审核，见证不传算法。障碍首侧遇当前格改备用实际1槽位，规则固定且记录不删。所有54可检任务可达，无准备失败/无新增/无效/超规模；未换图补图。')
 prep=[]
 for d in read(H/'protocol.json')['definitions']:
  x=read(H/'prep/results'/f"{d['base_id']}.json");c=read(H/'prep/inputs'/f"{d['base_id']}.json");prep.append([d['base_id'],d['L'],d['w'],len(c['free']),len(c['targets']),len(x['raw']['route'])-1,f"{x['entry_seconds']:.6f}"])
 add(table(['基础图','L','w','公开F','旧目标','准备步数','准备入口秒'],prep))
 add('准备、108门槛、独立外审均不混正式性能。仅前置ONE门槛采用新输入，因此称开发验证而非盲测。门槛108完整route/trace逐状态等价，输入哈希不变；因生产与审核核心字节一致，旧218边界/隔离/9截止及8夹具界引用已封存证据，不在本轮运行任何精确搜索。独立audit_adapter只在计时外缓存同一输入的BFS距离，60固定小图查询与原未缓存BFS双核一致，audit.py未改，不能把这种审核加速算作算法提速。')
 add('## 旧复制与形状分组\n\n从封存协议定位原件：LAST旧主36/补24=60、STRUCT新开发36、FIRST/SECOND/STRUCT原20+受控27=47，共143路径/143字节输入。不是把多个复制文件重复计数；old_input_catalog逐条来源、protocol和哈希可查。')
 add(table(['旧集合','条数'],[[k,v] for k,v in novel['old_collections'].items()]))
 add('新54状态对旧143：原始完整状态复制0、统一平移完整状态复制0、完整任务D4复制0、道路/遮挡形状D4复制0。新54形成27形状组、54完整状态组；各形状通常两进度。shape只用公开目标+遮挡，完整状态另含F/H/current/base/previous/predator/初始/当前/公开/暂缓目标、旧后缀和资源。签名不同不证明统计独立，对称/历史变体不计独立新形状。')
 add('排除明确旧完整状态复制后仍54状态27短27平、省54；再保守排除旧形状复制后也完全相同。因此本轮收益不是旧输入复制造成的，但仍只代表9规则基础道路和PPCPP单一历史来源。')
 add('## 全槽位、重复级与配对分母\n\n54槽位准备/输入/门槛全部通过；两方法270调用各自完整合法及时270，异常/技术故障/输出损坏/看门狗/截止/超软预算>10ms均0，最大超时量0。双方5次均成功且完整轨迹稳定的交集N=54。所有540结果保留，不挑最好重复；270个状态—重复组LAST中P0完整route/trace等于同批原版，108方法—状态组5次稳定。')
 add(table(['方法','正式调用','合法','严格及时','5次成功稳定状态','软超时>10ms','最大超时秒'],[[m,x['calls'],x['legal'],x['eligible'],x['stable_success_states'],x['overruns_gt_10ms'],x['max_overrun']] for m,x in a['call_stats'].items()]))
 add('原版与LAST均新调用、同封装/机器/线程1/入口，不拼旧计时。执行顺序按重复和协议槽位，方法先后随输入序号+重复号交替；进程启动/导入/磁盘/外审不计，解码/构造/全部分支/距离/几何/内部审核/完整原输出编码都在统一20秒内。90秒看门狗没有扩充20秒。')
 add('## 全54状态比较\n\n每状态只计一次；P1包括未选分支。全状态表/5次原始时间及每调用分段CSV另存，原已无收益的状态未删。')
 head=['状态','形状组','PPCPP','P1','LAST','省步','相对省步%','最终选择','P1状态','e'];tab=[]
 for r in rows:tab.append([r['id'],r.get('shape_group','—'),r.get('PPCPP_metrics',{}).get('length','—'),r.get('P1_metrics',{}).get('length','—'),r.get('LAST_metrics',{}).get('length','—'),r.get('saved','—'),f"{r['relative_saved']*100:.4f}" if r.get('relative_saved') is not None else '—',r.get('selected','—'),r.get('P1_status','—'),r.get('e')])
 add(table(head,tab))
 with (H/'54槽位完整状态表.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(head);w.writerows(tab)
 add('## 按道路族、尺寸、事件、进度分层')
 st=[]
 for key,groups in a['strata'].items():
  if key=='shape_group':continue
  for label,x in groups.items():st.append([key,label,x['slots'],x['paired'],f"{x['short']}/{x['equal']}/{x['long']}",x['PPCPP'],x['LAST'],x['saved'],f"{x['mean_relative_change']*100:.4f}",x['improved_groups']])
 add(table(['因素','层','槽位','配对','短/平/长','原步数','LAST步数','净省','逐状态相对差%','改善组数'],st))
 add('I族7/18改善省14，L/Z各10/18省20。small5、medium16、large6状态改善，分别省10/32/12；三个尺寸都有未改善。三事件直扩7/18、拐扩9/18、障碍11/18改善；30%12/27、70%15/27。长宽/面积/历史同时变化，不把这些数字解释为宽度、规模、进度的独立因果效应；large绝对路程较长而每例仍只省2步。')
 add('### 按道路/遮挡形状组\n\n27组来自9基础道路的3事件，不是27独立随机试验。进度配对不当新形状；组内P1坏分支也保留。')
 gt=[]
 for gid,x in a['strata']['shape_group'].items():
  rs=[r for r in rows if r['shape_group']==gid];gt.append([gid,','.join(r['id'] for r in rs),x['paired'],f"{x['short']}/{x['equal']}/{x['long']}",x['saved'],f"{x['P1_short']}/{x['P1_equal']}/{x['P1_long']}",any(r['old_copy'] or r['old_shape_copy'] for r in rs)])
 add(table(['组','槽位','配对','短/平/长','省步','P1短/平/长','旧复制'],gt))
 add('跨形状最低判据通过：I/L/Z各6个非旧复制改善组，相互非D4等价；不把18组当独立随机成功数，也不设置结果后的收益百分比门槛。')
 add('## 全分支状态、不利候选与代价\n\n54/54状态均U非空，P1全部完整，策略性不可达0；空U0、原分支失败0、替代异常0、整体截止0。每状态一次P1对P0：27短、25平、2长，最终选P1=27、P0=27。按270次LAST调用计：P1全部270完整，135短、125平、10长，135次选P1。这些重复计数不当作270新地图。')
 bad=[r for r in rows if 'P1_metrics' in r and r['P1_metrics']['length']>r['P0_metrics']['length']]
 add(table(['不利状态','P0','P1','多步','最终选择','原5次均值ms','LAST5次均值ms'],[[r['id'],r['P0_metrics']['length'],r['P1_metrics']['length'],r['P1_metrics']['length']-r['P0_metrics']['length'],r['selected'],f"{sum(r['methods']['PPCPP']['entry_times'])/5*1000:.6f}",f"{sum(r['methods']['LAST']['entry_times'])/5*1000:.6f}"] for r in bad]))
 add('两坏分支分别多10与2步，最终都保P0，但全部额外计算仍计入LAST。最终完整成功不变长是完整保留P0的构造，不作为额外创新或服务质量任意预算不退化证明。本轮两法及时率相同，不能外推任意规模。')
 add('工作阶段额外连接代价（相同连接端点在F-e路径长度减原F图距离）本轮合计0，逐段证据在analysis.calls.audit和states.audit。只说明这些实际连接不因禁入多走最短连接步，不表示P1全过程相对P0没有覆盖顺序/返航损失；两个P1更长例仍然存在，不能混淆端点固定的连接账与全路线差。')
 add('## 完整指标与账本\n\n三列均54状态一次，包含全部成功P1，不只选中分支。返航已含总步，四分类之和=步数，转弯不能推真实能耗。')
 keys=['N','length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps','initial_credit','active_targets','active_covered','remaining_before','newly_completed','published_targets','published_covered','deferred','missing_active','target_arrivals','duplicate_target_arrivals','active_coverage','published_coverage','overlap']
 add(table(['指标','PPCPP','LAST最终','P1全部替代'],[[k]+[a['metric_totals'][m][k] for m in ('PPCPP','LAST','P1')] for k in keys]))
 add('净省54步由历史重复多2、本轮重复少8、非目标少48组成；90度752→796多44、180度34→31少3，并非全指标改善。覆盖完成前4148→4491多343步，返航1382→985少397，净少54；不能把397尾段差单独当作可追回收益。目标到达重复比例11.5724%→11.4345%，不是图像面积重叠。')
 add('当前可检5982与本次待检3408格次完成100%、漏检0；公开6048完成6027，99.6528%，暂缓21格次不算完成。45格次以前已完成而后来被障碍覆盖仍保留；共享事件/历史的格次不是独立物理面积。')
 add('## 时间与分段成本\n\n所有270次/方法全部计入，包括坏P1、同长与保原；没有只挑获益/快的重复。P95按(n−1)×0.95插值。')
 add(table(['方法','N','均值ms','中位ms','P95ms','最大ms'],[[m,t['N']]+[f"{t[k]*1000:.6f}" for k in ('mean','median','p95','max')] for m,t in a['timing'].items()]))
 add(table(['方法','P0 ms','候选ms','P1含审核ms','最终审核ms','编码ms'],[[m]+[f"{x[k]*1000:.6f}" for k in ('p0','candidate','p1','final_audit','encoding')] for m,x in a['phase_timing'].items()]))
 add('LAST候选生成均值77.203643ms，占总入口均值约85.4591%，远高于P1均值4.395599ms。源码仍对每个待检q查询distance(q,base)，全部查询/几何成本真实进入计时；这里是已有实现的成本定位，不在本轮缓存提速或改查询方向。P0/候选/P1/审核/编码分段仅解释，总入口另含解码/构造/隔离快照与框架成本。')
 add('上轮小图约2.1倍与本轮约14倍来自不同输入/尺度，不当成同条件速度退化配对；可以确认的是本轮在本机约增加83.88ms平均入口，仅换取54状态合计54步。5重复仍不足跨机器或硬实时结论，绝对秒和比例同时保留。')
 # Route and timing strata are independent descriptions, not causal tests.
 trows=[]
 for key in ('family','size','event','progress','shape_group','old_copy','old_shape_copy'):
  for label in sorted({str(r[key]) for r in rows}):
   ids={r['id'] for r in rows if str(r[key])==label}
   for method in ('PPCPP','LAST'):
    t=timing([c['entry_seconds'] for c in a['calls'] if c['case_id'] in ids and c['method']==method]);trows.append([key,label,method,t['N']]+[t[k] for k in ('mean','median','p95','max')])
 with (H/'全部分层计时.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['factor','level','method','N','mean_seconds','median_seconds','p95_seconds','max_seconds']);w.writerows(trows)
 add('各族/尺寸/事件/进度/形状/旧复制分层计时见全部分层计时.csv；逐调用完整分段见540调用时间与分段.csv。')
 add('### 每状态5次入口毫秒原值')
 time_rows=[[r['id'],', '.join(f'{x*1000:.6f}' for x in r['methods']['PPCPP']['entry_times']),', '.join(f'{x*1000:.6f}' for x in r['methods']['LAST']['entry_times'])] for r in rows];add(table(['状态','PPCPP r0..r4 ms','LAST r0..r4 ms'],time_rows))
 with (H/'540调用时间与分段.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['id','method','repetition','status','eligible','legal','entry_seconds','overrun','p0','candidate','p1','final_audit','encoding'])
  for c in a['calls']:w.writerow([c[k] for k in ('id','method','repetition','status','eligible','legal','entry_seconds','overrun')]+[c['phases'].get(k,0) for k in ('p0','candidate','p1','final_audit','encoding')])
 add('## 固定选图与收益集中度\n\n绝对改善最大：large_I_corner_p70（所有正例均省2，按编号选）；相对改善最大：medium_I_obstacle_p70（19→17，10.5263%）；无改善最小：large_I_corner_p30；P1更长最小：large_I_straight_p30。正式策略性不可达与失败/迟到类别为空，不补图。最大改善单例占总省3.7037%，不能把相对最大单例10.5263%当总体。')
 for name in dict.fromkeys(v for v in a['selected'].values() if v):add(f'![{name}](figures/{name}.png)')
 add('## 独立核验、未解决项与停止\n\n全部9准备、54历史/54可行见证、108等价、540正式及全部P0/P1/final双指标/逐决策通过，生产读取路径每次只有原始输入，导入模块不含精确/分析；270个P0配对和108组5重复稳定。未运行精确最优查询，既不宣称达到最优也不投射旧小图最优差距。审核适配仅为计时外距离缓存，原审核源码未改且前置等值验证。')
 add('本轮无协议偏差、无无效/准备失败/门槛失败、无正式故障/迟到/未解决项；没有改运行模块、追结果加图、加终点或提预算。所有旧复制检查为0，因此无剔除后才出现的结论变化。几何是9个规则道路、固定基地/捕食者与单一历史来源，仍非一般施工道路/方向因果或现场证据。')
 add('交付审核首次verify.py在重审后整表比较遇到calls中坐标tuple/保存JSON list表示差异；完整失败日志verify_initial.log及原脚本保留。另版verify_v02.py只规范化重算calls，正式数据和运行/审核核心不改，失效和需重跑正式项均0；该交付审核故障不混入正式失败计数，详见交付审核器v0.2影响说明.md。')
 add('按540上限矩阵停止。本轮比FIRST/STRUCT全平背景保留了净路线收益，但只有约0.98%总步收益，约14倍入口计算和更多90度转弯必须一并评估。保留LAST为待审核开发候选，当前不确立主算法/创新，也不自动启动更大图、强P2排名或任何算法提速/改规则。由负责人判断是否值得继续投入。旧冻结/历史封存/最终留出不改，未提交推送GitHub。')
 add('## 交付核验\n\n**执行完成，待负责人审核。**\n\n```powershell\n& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST新开发地图验证_v0.1_20261020/verify_v02.py\n```\n\nREADME及review_packet提供证据映射、前置门槛和只读核验说明。')
 (H/'LAST新开发地图验证结果.md').write_text('\n\n'.join(report)+'\n',encoding='utf-8')
if __name__=='__main__':main()
