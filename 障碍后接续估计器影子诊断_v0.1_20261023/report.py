"""Reports from sealed predictions and joined saved evidence only."""
from common import *
from collections import Counter
def write(name,text):
 with (H/name).open('x',encoding='utf-8') as f:f.write(text)
def fmt(x):return '未知' if x is None else f'{x:.9f}'
def main():
 start=time.perf_counter();rows=read(H/'joined_results.json');s=read(H/'summary.json');w=read(H/'workload.json');m=read(H/'manifest.json');status=read(H/'status.json');b=s['datasets']['base'];v=s['datasets']['variants'];lookup={r['key']:r for r in rows}
 labels={'caught_improvement':'抓住改善','missed_improvement':'漏掉改善','wrongly_accepted_deterioration':'错误接受退化','correctly_rejected_deterioration':'正确拒绝退化','equal_true_biased_q1':'实际等长却估q1更短','equal_true_retained_q0':'实际等长，保留q0','unavailable':'不可用'}
 text='# 固定估计器影子诊断：未过继续门槛\n\n这是19对已见开发材料的阶段A诊断；没有接管规划、没有运行真实有限推演、没有调整16/64或旧序尾段政策。**本固定配置的继续信号关闭，不进入阶段B同机计时。**\n\n'
 text+='它能抓住部分改善，但关键两项均失败：I_gap_B__p60被判q0更好，真实q1明显更短；T_gap_B__p25及两个障碍变体均被判q1更好，真实却退化。基础12对采用建议后的合计距离仍为负，只满足第三项，不能抵消前两项失败。\n\n'
 text+='|固定检查|估计q1−q0（米）|真实q1−q0（米）|建议|结论|\n|---|---:|---:|---|---|\n'
 for key in ['base__I_gap_B__p60','base__T_gap_B__p25','base__I_gap_A__p25','base__I_gap_A__p60','base__L_gap_A__p25','base__L_gap_B__p60']:
  r=lookup[key];text+=f"|{key}|{fmt(r['delta_hat'])}|{fmt(r['delta_true'])}|{'q1' if r['prediction']['choice']=='ALT1' else 'q0'}|{labels[r['classification']]}|\n"
 text+='\n![19对估计与真实差](figures/19对估计与真实差.png)\n\n基础12对：4个真实改善中抓住3个、漏1个；唯一真实退化被错误接受；7个真实等长中6个保留q0，L_gap_B__p60却估计q1少3.219810994米而实际等长。没有不可用、失败或数值未知。建议q1共5对，相对全保留q0合计−13.558736680米；六几何各两状态，先状态均值再几何等权为−1.129894723米。两候选遗憾合计37.351122093米，最坏实际退化+8.587181813米，最坏单例遗憾28.763940280米。这里的遗憾只相对已测试的两个候选。\n\n'
 text+='变体7对单列：4个I改善全部漏掉，2个T退化全部误收，1个等长保留q0；建议q1共2对，相对q0合计+17.174363625米。它们复用已见基础几何，其中I的B进度变体还与原例触发状态及两臂原生尾部重复；不得与12对拼总体胜率、独立样本数或显著性。5个原无资格槽不进入预测，不算等长或求解失败。\n\n'
 text+='## 为什么I主正例会被漏掉\n\nOFF有限前缀13边，到[13,7]后将再次恢复，停时右块还剩32格；ALT有限前缀31边（恢复15＋局部16），停在[38,10]，还剩左侧1格及右侧15格。按被冻结的旧序，ALT补尾先回左侧[13,7]（旧rank11），再去右侧[37,9]（rank30）继续收尾，两臂替代轨迹最终都在右侧[38,9]末采。保存的真实ALT则先完成右块、最后回左侧[13,7]再返航。旧序补尾把真实候选的重要收尾安排重新打散。\n\n'
 text+='OFF完整替代估计118.117433696米，真实124.701701785米，误差e0=−6.584268089；ALT估计143.523451953米，真实95.937761505米，误差e1=+47.585690448。两误差之差+54.169958537米，把真实−28.763940280反成估计+25.406018257。两个A障碍变体同样漏判；两个B变体重复这一局部模式，不能作五次独立验证。\n\n![I主正例路线](figures/I主正例_真实与替代.png)\n\n'
 text+='## 为什么T会被误收\n\n两臂均从选择点推进24边，OFF停[27,31]、ALT停[26,32]，都将再次恢复、都剩100任务。旧序补尾均先向左侧[19,31]，最后在右侧[44,32]末采；真实后续则先右后左，并以左侧不同位置收尾。估计的补尾不是原PPCPP的未来。\n\n'
 text+='OFF估计251.528987661米、真实219.680746818米，e0=+31.848240843；ALT估计249.528987661米、真实228.267928630米，e1=+21.261059030。两误差都为正，却不相等；差−10.587181813米将真实+8.587181813反成估计−2米。两个障碍变体完全重复该排序错误；早公开B变体换了目标对且真实同路等长，估计也等长，不能算正确避免原T退化。\n\n![T反例路线](figures/T反例_真实与替代.png)\n\n'
 text+='## 其他结果不能略去\n\nI_gap_A_p25估计差−3.148163406、真实−14.372543110：OFF绝对误差−11.224379704、ALT误差0，排序仍正确。p60两臂估计与真实距离均精确相等，识别同块改善−6.793888511米。L_gap_A_p25估计−10、真实仅−0.979486872米：抓住直达改善，但明显夸大；其真实原生差仍为+2步，不能说原生路线改善。L_gap_B_p60两臂绝对误差+3.607417978/+0.387606984，使真实等长被判为q1更短。\n\n![L例路线](figures/L小收益例_真实与替代.png)\n\n'
 text+='5对真实原生/直达同路等长（基础4＋变体1）全部估计等长；基础3对等长不同路中2对估计等长、1对偏向q1。逐例两臂估计、真值、误差、停止位置/剩余责任、选择实际损益和两候选遗憾见[全表](02_逐例预测与真实结果.md)及joined_results.json。\n\n'
 text+='误差恒等式(delta_hat−delta_true)=(e1−e0)已逐对精确核验；它只是数学分账，不是独立机制因果。本轮改变了停止状态后的整条替代路线，并对完整路线共同直达，不能把误差一概视为某段局部路径代价。结果与旧序尾段的两臂非对称误差一致；未验证“延长前瞻一定解决”，也没有据此提出第二个配置。\n\n'
 text+='## 调用、成本与结论边界\n\n固定提取38臂、补尾38条、公共直达38次，新增原生/直达视图76；真实历史、完整PPCPP/H1/P2、真实有限推演核心均0。18项纯技术首轮通过，修复0；38臂全合法完整并返航、无超限/失败/未运行，独立前缀及完整替代路线审核通过。预测封存后才合并真值；设计者早已见过案例，信息隔离不能消除开发偏差。\n\n'
 text+='补尾共2160次任务连接＋38次返航，生成5677边；完整替代原生共6694边，公共直达候选3426次。每臂仍构造完整替代路线并做完整post及信用验证。读取保存前缀的耗时不能代替真实推演成本，本轮不能证明加速。详见[工作量与未知](03_计算工作量与未验证事项.md)。\n\n'
 text+='这只关闭本次固定估计配置在这19对已见材料上的继续信号，不证明所有尾段估计、所有有限前瞻都无效，也不把部分识别成功称为规则可靠或创新。旧H2保持未确认，不改写旧封存结论。完成后封存、根进度仅前缀追加，停止交负责人审核。\n'
 write('00_通俗影子评估结论.md',text)
 text='# 规则与信息隔离\n\n规则在真实补尾前登记于manifest.json与freeze.json；controller_registration.json另绑定串行控制器。18项纯技术首轮通过，未使用修复轮；真实阶段未改科学政策、源码或补跑。\n\n'+json.dumps(m['policy'],ensure_ascii=False,indent=2)+'\n\n'
 text+='固定19对：基础12＋变体7、38臂。五无资格槽只保留gaps引用；无新图、目标、seed、候选序或阈值搜索。q0/q1保持原登记，两臂事件初始H/当前来向/资源/捕食者/旧计划相同；本批seed原值20261020。\n\n'
 text+='裁剪器可读原始完整保存资料，但只按逐边前缀谓词推进，独立审核器从原轨迹再次核最早截止及pending全集。到所选q后，若无合法待采邻格且还有pending，便已按原规则将进入恢复分支，停在选择目标和算路径之前；不读取下一恢复目标。另到16条局部边/总64边/末采点即停，若同点同时满足，按已登记顺序标签，物理截断点相同。恢复中途/64边/末采点本批未实际触发，均有手写纯案例核验。\n\n'
 text+='估计器每臂独立新进程，审计open事件，只允许读取自己的一个裁剪包、冻结代码/manifest/freeze及Python运行时；旧目录、其他输出、source_guards和真值表均拒绝，纯隔离探针实际拒绝4种读入。估计器不是操作系统安全沙箱，限制的是本程序的文件数据流；输入白名单和读取路径完整保存于manifest/read_guard。允许的事件old_route及旧任务序是事前计划；没有真实候选后缀、末采点、完整长度或结果标签。共同前缀是事件起点至指定选择点的已规划原生路线，不把它写成已飞物理H。\n\n'
 text+='每臂冻结旧任务序只扫一遍，顺带采格更新原生pending；已完成/重复访问跳过、缺责拒绝，不增最近邻兜底。使用v2 UnifiedGeometry，固定按端点字典序调用原A*，返回反向路径时只反转已存路径；本轮没有另写路径平局算法。每臂新建缓存，无跨臂复用；本批2198次路径调用全缓存未命中。model/bfs_metric_geometry/unified_geometry只把绝对导入改成独立包内相对导入，完整diff及来源hash见protocol。中心直达、信用、独立审核源码逐字节复用，命名为frozen_shadow_center_20261023。导入纯检查无solve/core_route/process执行。\n\n'
 text+='替代完整路线＝共同原生前缀＋有限原生前缀（去重复接缝）＋旧序补尾＋返航；共同前缀只收费一次。公共post对整条替代路线执行同版直达、使用原事件初始H/责任；有限前缀预测采集不反馈物理历史。新补尾只是假设路线，Jhat不是实际PPCPP未来，也没有对真实完整路线的上下界保证。\n\n'
 text+='主判据只用直达全程Jhat。delta_hat<−1e−8且两臂合格才q1，其余q0并保留等长/未知/不可用标签。根式先精确合并，128bit有理界转换为向外舍入80位十进制界；独立Fraction/isqrt再从实体顶点重建距离与阈值比较，不根据显示小数改胜负。本批无数值未知/阈值内负数/不可用。\n\n'
 text+=f"predictions_seal.json UTC={s['prediction_seal_utc']}，后合并真值UTC={s['truth_released_utc']}，绑定预测、全部裁剪/输出/审核hash；compare.py只有见到预测seal才开放原始完整真值。隔离防止程序直接偷看结果，无法使已见开发材料成为盲测。\n\n"
 text+='有限推演加保留旧次序的路线估计，与已有rollout/保底连接思路有重合；本轮未作新文献检索或创新确认，不能把工程组合称为新方法。旧H2未确认，不以这套估计指标替换旧H2。\n'
 write('01_规则与信息隔离.md',text)
 text='# 逐例预测与真实结果\n\n单位米；差均q1−q0，负表示q1短。e0/e1=Jhat−J；遗憾仅相对两个已测试候选。表内显示值供阅读，机器表保留精确根式。基础与变体分别保留，不拼总体胜率。\n\n'
 for ds,title in [('base','基础12对'),('variants','受控变体7对')]:
  text+='## '+title+'\n\n|案例|Jhat0|Jhat1|J0|J1|估计差|真实差|e0|e1|e1−e0|建议|采用实际差|两候选遗憾|类别|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|\n'
  for r in rows:
   if r['dataset']!=ds:continue
   a,z=r['arms']['OFF'],r['arms']['ALT1'];text+=f"|{r['key']}|{fmt(a['Jhat_post'])}|{fmt(z['Jhat_post'])}|{fmt(a['J_true'])}|{fmt(z['J_true'])}|{fmt(r['delta_hat'])}|{fmt(r['delta_true'])}|{fmt(a['error'])}|{fmt(z['error'])}|{fmt(r['error_difference'])}|{'q1' if r['prediction']['choice']=='ALT1' else 'q0'}|{fmt(r['actual_selected_delta'])}|{fmt(r['two_candidate_regret'])}|{labels[r['classification']]}|\n"
  text+='\n'
 text+='## 全部38臂的截止与补尾\n\n局部16和再次恢复为本批两个实际截止类型，恢复边与局部边都包括在有限边数。pending全集见每臂crops与joined_results，不只保留计数。\n\n|臂|停点|截止|有限边/局部边|新采格|剩余任务|补尾新边|任务连接|原生Jhat|直达Jhat|\n|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
 for r in rows:
  for arm,a in r['arms'].items():
   p=a['prefix_summary'];text+=f"|{r['key']}__{arm}|{p['stop_current']}|{p['stop_reason']}|{p['finite_edges']}/{p['local_edges']}|{p['new_tasks']}|{p['tail_start_pending']}|{a['tail_new_edges']}|{a['tail_task_queries']}|{a['Jhat_raw']}|{fmt(a['Jhat_post'])}|\n"
 text+='\n## 六基础几何等权汇总\n\n|几何|状态数|采用实际差合计|该几何状态均值|\n|---|---:|---:|---:|\n'
 for geo,a in b['by_base'].items():text+=f"|{geo}|{a['pairs']}|{fmt(a['selected_sum'])}|{fmt(a['selected_mean'])}|\n"
 text+='\n六几何等权均值−1.129894723米。本批每几何两状态恰等权，不据此拟合新阈值。变体的重复身份保留旧duplicate_levels.json；完整E/旧序19签名不同，局部触发重复及原生尾部重复不能当独立几何。\n\n五个缺口原样引用于gaps.json，无新估计值。\n'
 write('02_逐例预测与真实结果.md',text)
 text='# 计算工作量与未验证事项\n\n**本轮没有证明加速，也不进入真实有限推演计时。**来源是保存前缀；少做原生决策不能自动推出总工作量下降。\n\n|项目|实际|\n|---|---:|\n|固定裁剪/补尾/公共post|38 / 38 / 38|\n|新增原生/直达替代视图|76|\n|新完整核心/真有限核心/历史核心|0 / 0 / 0|\n|纯技术案例/修复轮|18 / 0|\n|失败/不可用/超限/迟到/未运行|全部0|\n'
 count=w['main_counts'];text+=f"|有限前缀总边数|{sum(x['prefix']['finite_edges'] for x in w['arms'])}|\n|共同前缀总边数|{sum(x['prefix']['common_edges'] for x in w['arms'])}|\n|补尾新边（含返航）|{count['tail_new_edges']}|\n|完整替代原生边|{count['post.source_validation']}|\n|旧序扫描/跳过/重复|{count['old_order_entries_scanned']} / {count['old_entries_skipped']} / {count['old_duplicate_entries']}|\n|任务连接/返航连接|{count['task_path_queries']} / {count['return_path_queries']}|\n|路径调用/缓存命中/A*搜索|{count['path_queries']} / {count['path_cache_hits']} / {count['astar_searches']}|\n|独立新缓存几何实例|{count['geometry_contexts']}|\n|补尾采格/其中顺带采格|{count['tail_new_tasks']} / {count['incidental_tasks']}|\n|post候选/原边合法性/输出合法性|{count['post.candidate']} / {count['post.source_validation']} / {count['post.output_validation']}|\n|post服务交测试|{count['post.service_intersections']}|\n\n"
 text+='每臂尾段始态剩余任务均须补齐；全38臂共2204格，实际发起2160次任务连接，另44格顺带采集。故补尾确实访问了几乎全部尾段目标，生成完整替代路线后还做一次完整公共post，以及原生/直达全信用评价。这是实质工作量，不能只报前缀16边。\n\n'
 text+='geometry_contexts各有冻结model构造器的可达性BFS，38个上下文/可达集合大小保存；未重新插桩的生产BFS出队和邻居次数为null。distance_BFS_rows=0仅表示没有调用批量distance建立距离行，不表示完全没有BFS。A*次数可读searches=2198，节点展开未暴露则null。在线详细profile关闭；只在纯导入测试中临时观测有无入口执行。\n\n'
 text+='查询字段的别名不得重复相加：post.service_intersections与post.post_service_intersections均指同一291394次服务交检查；原边/候选/输出与主metrics额外几何、独立审核是不同阶段，分别计账。完整逐臂计数、各视图计数和主外独立BFS/信用费用见workload.json。\n\n'
 text+='|阶段（每臂秒）|均值|中位|P95|最大|合计|\n|---|---:|---:|---:|---:|---:|\n'
 for k,a in w['timing_statistics'].items():text+=f"|{k}|{a['mean']:.6f}|{a['median']:.6f}|{a['P95_nearest_rank']:.6f}|{a['max']:.6f}|{a['sum']:.6f}|\n"
 text+='\n读取、冷导入、源码哈希、主计算、结果写盘、主外审核没有混作单个速度指标。worker_wall包括本进程读入/导入/冻结源码hash/补尾/post/必要信用等，结束于最后输出写盘前；父controller的逐臂wall另包含进程启动/退出/输出读取/写盘/独立审核。尾段构造计时包含快照/几何上下文预检/路径/顺带采格，join_native_contract单列。post_call包含冻结引擎的请求解码、原边检查、全程post和编码；full_credit_metrics是额外必要信用/指标。请求JSON编码、日志写入等余量包含worker_wall，未假装为0。主外独立审核不作为在线主成本，仍保存其实际费用。\n\n'
 text+=f"准备和来源审核总wall={read(H/'setup_receipt.json')['wall_seconds']:.6f}秒；裁剪wall={read(H/'extraction_receipt.json')['wall_seconds']:.6f}秒；独立原始前缀核验wall={read(H/'crop_audit_receipt.json')['wall_seconds']:.6f}秒；父批wall={status['wall_seconds']:.6f}秒。这些是本次诊断处理成本，不与旧批毫秒数做速度比。报告/画图/封存/最终只读verify另有回执；未观测的细次数保持未知。\n\n"
 text+='以后若另行研究真实有限推演，须收费：共同前缀、状态复制、候选产生、两臂可中止推演、补尾、所有post、选择、选中臂真实续跑或重算及最终检查；比较方是“两目标完整试走并复用短者”，不能再收一次赢家计算。当前判断门槛未通过，阶段B不启动。\n'
 write('03_计算工作量与未验证事项.md',text)
 text='# 审核入口\n\n先读00_通俗影子评估结论.md，再读01规则/02全表/03费用。门槛不通过：原I未建议q1、T及两障碍变体全误收；基础净负只满足第三项。固定配置结束，不调参、不真实有限推演/计时/扩图/留出/线上接管。\n\n证据：manifest/freeze/controller_registration→technical/round1→38 crops/crop_audits→38独占输出/完整audits→predictions及seal→后合并joined_results/summary/workload→preseal_verify/final/verify_receipt。\n\n独立审核不使用主clip/tail/join，从原始保存轨迹核最早截止与原奖励局部前缀；从原旧序按实际保存连接逐段核责任/顺带采集、独立BFS最短性；同长路线身份由冻结原连接代码/仅导入diff绑定，不写第二条平局规则。完整替代路线再经独立中心区信用与post合法/锚点/根式审核。最终verify.py不导入核心/post/几何/BFS，从实体顶点用独立Fraction/isqrt重核76条估计/真实直达长度、19组误差/阈值/选择/遗憾/分组算术，并绑定此前独立几何回执。\n\n19对不是19独立几何：基础6几何各两进度，变体在3个原点设计但仅I/T的7槽合格；5无资格缺口保留。旧重复关系及原生/直达等长分类沿用冻结证据。\n\n旧基线、旧数据、旧final及旧root_after均只读；来源旧verify在各自历史root_after投影下真实执行，当前根到三旧包的后缀/hash链另核，未篡改旧manifest消除进度差异。protocol/source_verify_0/1/2逐项说明范围；不是负责人此前已复核原始数据。\n\n最终核验命令：项目Python -B -X utf8 本包/verify.py。该命令只读；最终verify_receipt在封存后单独独占生成，不写旧材料。\n'
 write('review_packet.md',text)
 (H/'gaps.json').write_bytes((STRUCT/'gaps.json').read_bytes());(H/'duplicate_levels.json').write_bytes((STRUCT/'duplicate_levels.json').read_bytes())
 dump(H/'report_receipt.json',dict(passed=True,seconds=time.perf_counter()-start,source='sealed predictions and joined results only',new_core=0,new_post=0,new_geometry=0))
 print(dict(reports=5,gate_passed=False,seconds=time.perf_counter()-start))
if __name__=='__main__':main()
