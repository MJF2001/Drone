"""Write static review artifacts from already saved/certified numbers."""
from common import *
def write(name,s):
 with (H/name).open('x',encoding='utf-8') as f:f.write(s)
def f(x,n=6):return '未知' if x is None else f'{x:.{n}f}'
def ms(x):return f(x*1000,3) if x is not None else '未知'
def vector(d):return '/'.join(str(d[k]) for k in ('total','90','180','other'))
def link(src,line,label=None):return f'[{label or Path(src).name+":"+str(line)}]({str(src).replace(chr(92),"/")}:{line})'
def main():
 start=time.perf_counter();r=read(H/'twelve_candidate_reference.json');s=read(H/'reference_summary.json');t=read(H/'timing_summary.json');p=read(H/'two_independent_call_cost_sums.json');matrix=read(H/'FIRST_capability_matrix.json');snips={x['id']:x for x in read(H/'static_source_evidence.json')};times={(x['id'],x['arm']):x['timing'] for x in read(H/'response_timing_observations.json')};cost=t['two_independent_call_sum_statistics']
 text='# 既有双候选证据：路线参照已知，干净总成本仍缺\n\n**优先建议只有一项：提交一项最小同机干净成本核查协议，待负责人另行批准；本轮不实施。** 不再为已知距离收益重跑，也不开发第二个估计器。若下一步要依据计算成本决定是否确需近似，当前缺的是完整双候选总入口的可信计时。\n\n'
 text+='固定12基础状态的保存完整结果已经足够计算两候选参照：4个选q1，7个等长和1个q1退化均保留q0。默认直达总长1741.413810128米，保存较短者总长1690.503951355米，合计少50.909858773米。六原始几何先各取两状态均值、再等权，平均少4.242488231米、逐状态相对变化均值−3.696287625%；总路程比例−2.923478525%，两种分母不同。\n\n'
 text+='这只是**保存结果中两候选较短者参照**，不是新算法实测收益、全局最优界或独立泛化成绩。保留合法默认完整结果并有足够预算完成两臂时，候选集内择短不更长，是选择结构本身的性质；预算、转弯、当前输入适配仍须核查。\n\n'
 text+='直达路线转弯总数合计增加5次：90°多3、180°少3、其他角度多5；累计转角多3.071625454弧度。原生总长1870→1826步，少44步，但转弯总数多3（90°多6、180°少3），原生累计角差精确为0；保存浮点累加仅有约−1.4e−14的舍入残差。不能说全指标改善或节能。\n\n'
 text+='|关键原例|q1−q0原生|q1−q0直达（米）|保存较短者|意义|\n|---|---:|---:|---|---|\n'
 for ident,meaning in [('I_gap_B__p60','取到已知I主收益'),('T_gap_B__p25','拒绝已知退化，不依赖近似判断'),('L_gap_A__p25','原生+2而直达改善；按旧FIRST步数择优会漏掉'),('L_gap_B__p60','不同路等长，严格保留q0')]:
  x=next(x for x in r if x['id']==ident);text+=f"|{ident}|{x['delta_raw_ALT_minus_OFF']:+d}|{x['delta_post_ALT_minus_OFF']:+.9f}|{'q1' if x['choice']=='ALT1' else 'q0'}|{meaning}|\n"
 text+='\n已有费用给出的绝对量级如下，均是旧批保存的单次观测：\n\n|两个独立处理的成本和|均值|范围|\n|---|---:|---:|\n'
 for key,label in [('solver_seconds','原生求解器自身（含诊断钩子/原生审核）'),('native_entry_seconds','原生入口（含选择/日志/编码）'),('post_engine_seconds','公共直达引擎'),('combined_main_seconds','两次主处理总成本和'),('independent_total_seconds','两次主外独立审核和'),('parent_wall_seconds','两次父进程墙钟和')]:
  a=cost[key];text+=f"|{label}|{a['mean']:.6f}秒|{a['min']:.6f}～{a['max']:.6f}秒|\n"
 text+='\n两个主处理成本和平均0.467736秒，原生求解器自身合计仅0.025638秒，公共直达引擎0.119076秒。按该旧批保存区间的总和，二者分别占5.48%和25.46%；另外69.06%是入口日志/编码/信用与报告性指标等混合区间，无法精确拆成纯诊断或在线必要成本。钩子已在求解器时间里，不能再加，也不能减去它就声称得到干净运行时间。\n\n'
 text+='这些数值未显示原生全程求解本身在这12小状态中已是主要计时瓶颈；公共后处理和包装必须一起看。它们说明了已保存调用的绝对费用，但没有用户给定响应期限，不能自行判“工程足够快”。每状态每臂仅一次，固定REF→OFF→ALT顺序、含完整pending/逐决策记录；不能当稳定速度结论，也不能把相加结果改名共享前缀在线实现耗时。\n\n'
 text+='另发现原worker scope文字将磁盘概括为主计时外，但源码中的entry/returned会在主时钟内读写并fsync入口日志。此次按实际时钟拆账，不改旧报告/数据，不把这段费用藏起来。必须完成的原生合法覆盖返航审核、post几何/信用/资源检查仍计在线必要工作；主外独立复核另列。必要检查与报告性指标混在同一函数里的精确费用为未知。\n\n'
 text+='旧FIRST已具备首次恢复完整分支、私有pending/路径/trace克隆、保留原分支、直接复用选中完整计划的代码能力。因此不能把“完整试走后选短者”重新命名成创新。它用最近/近基地/远基地候选、按原生步数选择，且无当前公共直达与中心区合同；当前双候选目标规则、完整post选优及共同截止仍需独立适配。旧代码存在共享几何能力，不等于当前模型已验证共享前缀兼容或省时。详见[静态对照](03_旧FIRST重合与当前适配缺口.md)。\n\n'
 text+='待批准协议只补一件事：在原12状态、原seed下，对单默认完整处理与双候选独立完整处理做同机同配置计时；先不共享前缀/缓存，也不重算赢家，避免同时改变接口和目标。两次重复、两方法共48总入口，最多72核心＋72公共post，无历史准备/热身；纯技术最多12项且真实入口0。未来一切合法性/信用/候选取得/编码与选择均入共同总时钟，详细诊断关闭但必要目标取得计费。完整方案见[唯一待批准协议](04_唯一待批准的最小成本核查协议.md)。这些只是建议，本轮实际新增调用全部0。\n\n'
 text+='创新、独立样本泛化、事件专属性和共同截止下及时性仍未证明。失败影子估计器保持关闭，16/64、尾序和权重均不调整，不进入它的阶段B。本轮只读审查完成后封存并停止交审。\n'
 write('00_通俗结论与下一步建议.md',text)
 text='# 十二状态的保存两候选参照与代价\n\n每状态一次、原seed=20261020；REF仅作等价和成本背景，不算第三个候选/独立案例。只比较原q0与冻结q1完整结果，按认证直达距离择短，同长保留q0，不按显示小数改胜负。原12例来自6几何，每图两进度；变体不加入此统计。\n\n'
 text+='|状态|q0|q1|原生q0/q1步|直达q0米|直达q1米|选择|采用直达差|采用原生差|\n|---|---|---|---:|---:|---:|---|---:|---:|\n'
 for x in r:
  a=x['arms'];text+=f"|{x['id']}|{x['default']}|{x['alternative']}|{a['OFF']['raw_length']}/{a['ALT1']['raw_length']}|{f(a['OFF']['post_length'],9)}|{f(a['ALT1']['post_length'],9)}|{'q1' if x['choice']=='ALT1' else 'q0'}|{x['selected_change_post']:+.9f}|{x['selected_change_raw']:+d}|\n"
 text+='\n|触发状态|trace记录/路径索引|当前位置/来向格|触发pending数|q0/q1旧rank|当前首次恢复同一条记录|\n|---|---|---|---:|---|---|\n'
 for x in r:
  z=x['trigger'];tags=z['old_order_tags'];text+=f"|{x['id']}|{z['trace_record']}/{z['route_index']}|{z['current']} / {z['previous']}|{z['pending_count']}|{tags['q0_old_rank']}/{tags['q1_old_rank']}|{z['equals_first_recovery']}|\n"
 text+='\n触发pending全集、共同原生前缀、当前/previous/旧rank与输入hash见twelve_candidate_reference.json。q1从原事件前旧任务序第一个仍pending且不等于q0的目标取得，不用完整候选结果挑选。本批12例恰均在第一次恢复触发，不推导任意输入都与旧FIRST一致。\n\n'
 text+='## 覆盖责任与资源（OFF、ALT两视图全部保留）\n\n|状态/臂|P/事件H/当前可检|入口剩余/本轮新采|原生遗漏/暂缓/返航|直达遗漏/暂缓/返航|原生/直达覆盖率|剩余资源预算|\n|---|---|---|---|---|---|---:|\n'
 for x in r:
  for arm in ('OFF','ALT1'):
   a=x['arms'][arm];A=a['coverage']['A'];B=a['coverage']['B'];text+=f"|{x['id']}/{arm}|{A['published']}/{A['initial_H']}/{A['active']}|{A['remaining_before']}/{A['new_credit']}|{A['missing']}/{A['deferred']}/{A['return_success']}|{B['missing']}/{B['deferred']}/{B['return_success']}|{A['published_coverage']}/{B['published_coverage']}|{a['resource_budget']}|\n"
 text+='\n已完成后被新障碍覆盖的H不回滚，当前可检active可小于P；保持物理H与原始责任，不能从active数差推断删了未采任务。两臂初始暂缓列表均原样保留，当前批均空；所有完整结果在各自原20秒native/post合同内合格，不能据此保证未来共同预算中的两臂均完成。REF的全部覆盖指标在机器表/72保存响应视图完整指标.json中保留。\n\n'
 text+='## 转弯全表\n\n向量依次为总数/90°/180°/其他；角度单位弧度。按原保存指标的整条路线相邻边方向计，不额外添加历史来向起始角。所有REF/OFF/ALT原生和直达、引擎原/直达方向变化数与累计角均保留在机器表。这里列实际两个候选。\n\n|状态/臂|原生转弯向量|原生累计角|直达转弯向量|直达累计角|\n|---|---|---:|---|---:|\n'
 for x in r:
  for arm in ('OFF','ALT1'):
   z=x['arms'][arm]['turns'];text+=f"|{x['id']}/{arm}|{vector(z['A']['counts'])}|{f(z['A']['total_turn_radians'],9)}|{vector(z['B']['counts'])}|{f(z['B']['total_turn_radians'],9)}|\n"
 text+='\n|状态|选中臂相对q0的原生转弯变化|直达转弯变化|直达累计角变化|\n|---|---|---|---:|\n'
 for x in r:text+=f"|{x['id']}|{vector(x['selected_turn_delta']['A']['counts'])}|{vector(x['selected_turn_delta']['B']['counts'])}|{x['selected_turn_delta']['B']['total_turn_radians']:+.9f}|\n"
 text+='\n合计原生转弯变化3/6/−3/0，累计角差由整数90°/180°计数认证恰0（保存浮点相加残差约−1.4e−14）；直达5/3/−3/5，累计角+3.071625454弧度。等长始终保留q0，不借转弯二次择优。\n\n'
 text+='## 六原几何分组\n\n|几何|状态数|采用直达差合计米|状态均值米|逐状态百分比均值|\n|---|---:|---:|---:|---:|\n'
 for geo,a in s['by_base'].items():text+=f"|{geo}|{a['states']}|{a['selected_change']:+.9f}|{a['state_mean_change']:+.9f}|{a['mean_state_percent']:+.6f}%|\n"
 text+='\nI主正例真实收尾变化、T退化、L原生/直达异号与不同路等长都保留。7等长含4对同物理路线与3对不同物理路线，默认都保留；不把等长不同路称为没有行为改变。基础与变体的重复关系只引用旧结构包duplicate_levels.json，不扩充质量/成本样本，也不把REF或seed当新地图。\n\n独立verify从原保存顶点重建根式长度与转弯、核原责任回执及触发身份，未生成任何新路径。\n'
 write('01_十二状态两候选参照与代价.md',text)
 text='# 保存计时的边界与未知\n\n原42处理含6历史＋36响应。这里只对12×REF/OFF/ALT=36响应给成本统计，6历史另存history_costs_excluded.json；不混入响应时间。每状态每臂一次，只有不同状态的分布，没有同状态重复计时；REF→OFF→ALT固定次序，不作因果差值或稳定提速比较。\n\n'
 text+='## 先看可加与不可加\n\n```text\nparent_wall_seconds\n  worker_wall_seconds\n    combined_main = raw_common_end_to_end + post_increment\n      raw_common = native_entry + raw_metrics混合区间\n        native_entry 包含 solver.seconds\n          solver.seconds 包含 hook.seconds 与原生完整合法审核\n      post_increment 包含 engine.entry_seconds\n        engine含源/输出合法性、中心信用、资源、部分报告、编码\n      post_increment剩余还含请求/响应编码、入口日志、完整B指标\n    independent_seconds（含独立views/post及逐决策审核）\n    其余冷加载/哈希/文件/等价核对等混合区间\n  其余进程启动/结束和父端文件处理混合区间\n```\n\n同层也不能任意相加：native_entry不与solver/hook再加；post_increment不与engine再加；independent总时间不与内部两审核秒再加。worker/parent是包围层，不额外加到主时间。唯一直接时钟分账为combined=raw_common+post_increment。各混合余量只是同层包含区间的算术，不是删诊断后的干净速度。\n\n'
 text+='## 字段与源码时钟\n\n|保存字段|边界与内容|包含关系/限制|\n|---|---|---|\n'
 for x in read(H/'timer_boundary_catalog.json'):
  evidence=snips[x['evidence'][0]];text+=f"|{x['field']}|{x['clock']}；{x['contains']}；{link(evidence['file'],evidence['start'])}|{x['nested_in'] or '外层边界'}；单位{x['unit']}；{'单次观测' if x['single_observation'] else '未单独观测'}|\n"
 text+='\n**源码校正：**旧timing.scope文字将disk概括在外，但entry/returned在solver前后和post前后读entry_log并append/fsync，位于主时钟内；详见'+link(BASE/'worker.py',17)+'、'+link(BASE/'common.py',12)+'及static_source_evidence中current_entry_return_log。这里澄清边界，不改旧数据或靠猜测分配每毫秒。\n\n'
 text+='关闭核心详细profile也不表示没有诊断：OFF/ALT每步record会排序/规范化并保存完整pending、事件和segment，choose另扫旧序/说明距离。hook累计秒不包含export、后来norm/JSON编码和主外审核，不能假定减去hook即获得干净核心。REF没有该钩子，但完整求解后又扫描保存trace以定位触发，且原生结果仍带trace/奖励选项；它也不是本次干净性能对照。\n\n'
 text+='## 十二状态逐次真实耗时\n\n均为毫秒；“solver/入口/主处理/主外审核/worker/parent”六项各是原保存时钟，存在包含关系。完整秒值及全部子项见response_timing_observations.json。\n\n|状态|REF六项毫秒|OFF六项毫秒|ALT六项毫秒|\n|---|---|---|---|\n'
 keys=['solver_seconds','native_entry_seconds','combined_main_seconds','independent_total_seconds','worker_wall_seconds','parent_wall_seconds']
 for x in r:text+='|'+x['id']+'|'+'|'.join(' / '.join(ms(times[x['id'],arm][k]) for k in keys) for arm in ('REF','OFF','ALT1'))+'|\n'
 text+='\n## 两个保存独立处理的调用成本和\n\n仅T_OFF+T_ALT；没有共享前缀，没有新增选优入口，绝不称最小可能耗时或在线实现时间。REF不加进这一双候选和。\n\n|状态|solver和ms|原生入口和ms|公共post引擎和ms|主处理和ms|主外审核和ms|parent和ms|\n|---|---:|---:|---:|---:|---:|---:|\n'
 for x in p:text+='|'+x['id']+'|'+'|'.join(ms(x['sum'][k]) for k in ('solver_seconds','native_entry_seconds','post_engine_seconds','combined_main_seconds','independent_total_seconds','parent_wall_seconds'))+'|\n'
 text+='\n|两个独立处理之和的阶段|均值ms|中位ms|最小ms|P95ms|最大ms|\n|---|---:|---:|---:|---:|---:|\n'
 for k,a in cost.items():text+='|'+k+'|'+'|'.join(ms(a[z]) for z in ('mean','median','min','P95_nearest_rank','max'))+'|\n'
 text+='\nP95为最近秩ceil(0.95N)，N=12时恰最大值；不是12次重复同一输入。RAW求解器和公共post引擎合计分别占保存主成本5.48%/25.46%，其他混合区间69.06%。这些区间有输入、日志、必要完整信用/合法性、报告性指标、诊断序列化，不能统归post、诊断或纯算法。T_gap_B_p60 ALT原生入口194.067ms而求解器20.990ms，保留该观测，不无依据归因CPU/磁盘。\n\n'
 text+='必须计在线的工作已有源码证据：原生最终single_cell_audit、post源/输出几何、中心区完整信用、距离资源及认证比较；不能因为“审核”二字把它们全移出。主外独立BFS/奖励复核和图/封存是研究费用，另列。原生/直达metrics.evaluate同时做必要断言与报告性转弯/重复/阶段指标，原计时没有分离两类子费用；编码、候选取得、状态复制、REF扫描的单独时间也未知。post.timing.encoding赋值发生在结果JSON编码之后，未进入保存响应，不能伪填0或用阶段差值精确当它。\n\n'
 text+='旧FIRST和影子诊断属于不同批次、模型、输出/时钟范围，本文不据其毫秒数计算跨批速度比；没有新增profile、热身或性能实验。\n'
 write('02_保存计时边界与未知.md',text)
 text='# 旧FIRST重合与当前适配缺口\n\n仅静态读源码、核hash及保存回执，未导入或执行旧FIRST，不重跑其门槛/BFS/候选。旧包预登记/报告已将完整试走称为候选机制，不称rollout本身创新。保存门槛211、开发282及94组原分支等价为旧包既有证据；本轮不重新宣称复现这些调用，也不将旧47状态加入当前12样本。\n\n|项目|判定|旧能力|当前边界/缺口|源文件/行号|\n|---|---|---|---|---|\n'
 for x in matrix:
  evidence='，'.join(link(snips[z]['file'],snips[z]['start']) for z in x['evidence']);text+=f"|{x['item']}|{x['classification']}|{x['old']}|{x['current']}|{evidence}|\n"
 text+='\n“代码已有能力”只指所列旧代码存在相应操作；“当前模型已验证能力”限当前完整两独立臂/冻结合同的已存证据；“仍需适配”不能提前说实现兼容。每行代码逐行副本与hash在source_snapshot、static_source_evidence.json；源码上下界均可核。\n\n'
 text+='优先复用入口：旧FIRST rollout.finish的完整分支/私有状态与最后selected整条返回；当前expand_hook.select的冻结两目标规则；当前worker/public engine的整条原生→直达及中心区责任审核。不能直接把旧THREE的最近/近基地/远基地改名q0/q1，也不能沿用len(route)选择后声称按post距离择优。L_A_p25是明确反证。\n\n'
 text+='共享几何与共同前缀可能减少重复工作，但本轮没有在当前中心区整条post合同下验证：post可以跨接缝，不能分别优化两段后相加；分支预测pending不能写回事件物理H；缓存查询顺序/可达性/截止与状态必须隔离并重新验收。故唯一待批准小批先采用独立两臂、不共享前缀缓存，不把共享节时当既成事实。\n\n'
 text+='旧FIRST保留原分支仍在任何后续deadline时整体报deadline并不给及时完整输出；所以它原本就未保证默认及时率不退化。当前两臂分别通过20/20秒不等于总入口有双倍预算或同截止不退化。新的候选结构性质只在两臂都合法完整且总预算允许时成立。\n'
 write('03_旧FIRST重合与当前适配缺口.md',text)
 text='''# 唯一待批准建议：12状态最小干净成本核查

状态：仅协议建议，未实现、未启动，不是失败估计器的阶段B。目的仅是补“直接完整算两个固定目标并复用短者”的同机总入口成本；已知距离收益无需另作重复发现，也不把完整试走称论文主算法。

1. 固定本轮原12基础输入、原旧任务序/物理H/来向/资源/捕食者/seed20261020。不开新图、变体、候选或留出。SINGLE只按原默认q0完整处理；DIRECT2从同一事件输入独立完整处理q0/q1，原q1规则运行时从当前pending和旧序取得，取得成本计时，禁止读保存答案或事后标签。整条路线各做同版post/中心区责任审核，认证距离择短，同长q0，直接返回已生成赢家，不重算。
2. 最小实现先不共享前缀或几何缓存；复用旧FIRST“保留原分支/完整返回”的结构及当前完整处理合同，不恢复旧THREE候选或步数目标。PPCPP邻格奖励、平局、合法连接与采集合同不改。轻量候选钩子只保留必要目标取得和唯一授权，不保存每步完整pending，仍须纯桩/保存结果一致性验收；实现前冻结源码/配置/输入hash。
3. 两方法各两次重复，12×2×2=48方法总入口。SINGLE每入口1核心+1post、DIRECT2每入口至多2核心+2post，合计最多72核心+72公共post；新增历史/REF/热身/技术真实入口0。纯技术最多12项，只用手写桩/保存身份，不运行真实核心或公共post。两个重复不当独立地图，也不作稳定提速或显著性结论。第一重复按状态索引轮换SINGLE/DIRECT2先后，第二重复反序；串行新进程、相同本机解释器/四线程环境均1。
4. 同一总入口40秒软预算，包含输入解析/验证、状态构造/复制、候选取得、所有核心/整条post/返回前必要完整合法信用资源检查、认证比较、选定完整输出编码；单次核心至多20秒且不超过公共剩余预算，单post原18软/4096候选/20秒迟到规则与公共剩余预算共同约束，父看门狗150秒不是额外计算预算。两臂不各领独立40秒。任何超限/迟到/不完整保留，未完成臂不参与质量择优；不凭保留默认结果就宣称及时率必保留。具体截止传播和已完成默认分支的返回规则须在未来实施前明确核定，不用宽松审核绕过。
5. 本次建议的干净主时钟仍要包含所有返回前用于确认可用输出的检查。主外逐决策独立复核、额外报告性完整指标、图与封存另计；源码中不可分离的冻结post报告开销仍全收，不为变快私改公共层。必要结果编码与两臂选择收费，详细profile关闭；不能通过减去旧hook秒估计本次结果。冷加载/磁盘/进程父wall与主时钟同时报告，主时钟内不写研究性entry/fsync日志；数据记录落点须源码审清。
6. 先纯项通过再最多48入口，每臂仅一次，不技术热身、不自动修复补跑/补参数。每条保存计划与原封存q0/q1的路线、trace语义、post信用和长度逐一核身份；与旧结果不一致或代码异常即停止留证。不能用新的“更好路径”替换固定候选来凑收益。重复不足/超限保未知，不取最有利一次。
7. 报告每方法总入口的核心/候选取得/复制/post/必要检查/编码/选择/父wall边界，逐状态两次真实值、均值范围和全部迟到失败；单臂不可分项标未知，不额外开profile。对照是两个候选完整试走且复用短者，不额外向DIRECT2收费一次赢家重算。不给工程足够快阈值、不用旧FIRST/影子毫秒算因果加速。

实施与调用预算须负责人另行批准。本轮实际核心/post/搜索/几何/新候选/训练仍全部0；没有创建这个未来计时执行器或开始任何入口。若未获批准，停留在本审查的已有证据，继续保留创新与泛化未知，不设计更复杂估计器。
'''
 write('04_唯一待批准的最小成本核查协议.md',text)
 text='# 审核入口\n\n本轮仅既有证据与成本审查，新增核心/历史/post/路径距离搜索/几何可视/候选路线/反事实/训练均0；只读哈希、算术、静态源码和表格有实际成本。\n\n先读00结论：保存两候选较短者少50.909858773米，直达转弯多5，非新算法实测；两个独立主处理成本和平均0.467736秒，干净在线入口未知。唯一优先建议为04最小干净成本核查协议待批准，本轮不实施。01有12状态全部触发/两臂距离/责任/转弯与六几何汇总；02逐项时钟和混合边界；03旧FIRST逐项代码/当前适配范围。\n\n数据：twelve_candidate_reference.json、72保存响应视图完整指标、response_timing_observations、two_independent_call_cost_sums、reference_summary、timing_summary；history_costs_excluded保6历史不混响应，变体仅重复背景。timer_boundary_catalog/static_source_evidence/source_snapshot指向每项真实字段、时钟位置及hash。FIRST源码只读不导入，旧211/282调用只是历史保存证据。\n\n独立verify.py只用stdlib，直接读原36响应输出重建72视图的长度/转弯、12组身份/选择/算术与36组时钟导出，分组统计用独立Decimal；长度由实体顶点平方因子枚举和Fraction根式认证，不调用几何或路径搜索。再核22静态源码片段逐行/hash、旧源/root链及新封存。saved独立合法信用回执只绑定复核，不重跑旧BFS/几何。\n\n来源先实际执行影子包只读verify，核实际当前根（本轮无需历史root投影），再核四包旧封存/root字节链及FIRST的866包内/137来源绑定；没有改任何旧manifest或根历史。源码/原始结果不变。若分析脚本出错，analysis_failures独占保失败，修正不得扩范围或重跑算法；没有该目录表示本轮未观察到此类失败。\n\n复核入口：项目Python -B -X utf8 本包/verify.py。完成只前缀追加当前进度，保存root_before/after和最终回执，然后停止交审；不自动性能批/阶段B/共享前缀开发/新估计器/留出/推送。\n'
 write('review_packet.md',text)
 dump(H/'report_receipt.json',dict(passed=True,seconds=time.perf_counter()-start,counts=dict(C),reports=6,recommendation='one minimal clean same-machine cost protocol, pending separate approval, not executed',proposed_future_caps=dict(method_entries=48,core=72,post=72,pure_cases=12),actual_new_experiment_calls=0))
 print(dict(reports=6,actual_new_calls=0,seconds=time.perf_counter()-start))
if __name__=='__main__':
 try:main()
 except BaseException as e:fail_record('report',e);raise
