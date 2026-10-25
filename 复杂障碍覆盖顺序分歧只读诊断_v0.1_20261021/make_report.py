"""Summarize saved facts. Post hoc hypothesis is labeled, no experiments."""
from order_common import *
import collections

def write(name,txt):
    with (H/name).open('x',encoding='utf8') as f:f.write(txt)
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])+'\n'

if __name__=='__main__':
    a=read(H/'analysis.json');pairs=a['pairs'];routes={r['id']:r for r in a['routes']};seeds=sorted({p['seed'] for p in pairs})
    core=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py';native=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
    anchors=[]
    for path,spans in [(core,[(25,46)]),(native,[(26,38)])]:
        lines=path.read_text(encoding='utf8').splitlines();anchors.append(dict(file=str(path),sha256=sha(path),excerpts=[dict(start=lo,end=hi,lines=[dict(line=i,text=lines[i-1]) for i in range(lo,hi+1)]) for lo,hi in spans],evidence='Source-known rule only; not a reconstruction of unrecorded runtime scores.'))
    save(H/'frozen_rule_anchors.json',anchors)
    csvsave(H/'48共同轨迹与采集分歧.csv',[{k:p[k] for k in ('id','case','rep','seed','timely','classification','route_status','common_vertex_count','common_state','PPCPP_next','P2_next','acquisition_divergence','delta')} for p in pairs])
    csvsave(H/'全批反向关系账.csv',a['counterexamples'])
    save(H/'counterexample_ledger.json',dict(records=a['counterexamples'],tags=dict(collections.Counter(t for r in a['counterexamples'] for t in r['tags'])),note='Same-proportion observational rows, not independent geometries. Empty/missing relation categories remain in report; all signed pair deltas retained.'))
    provenance=[]
    for ex in a['examples']:
        p=next(p for p in pairs if p['id']==ex['pair_id']);d=p['decision_evidence'];provenance.append(dict(pair_id=p['id'],selection=ex,owner_kind=d['owner_kind'],pointer=d.get('event_pointer'),source=d.get('PPCPP_output'),source_sha256=d.get('PPCPP_output_sha256'),at_event_start=d.get('at_event_start'),direct_record=d.get('direct_record'),nearby=d.get('nearby'),missing_scores=d.get('missing_scores','no fork: no next action to inspect'),P2_stepwise_trace='not recorded; final saved route/source/search-stage fields only',source_rule_anchors='frozen_rule_anchors.json',causal_claim='none'))
    save(H/'decision_provenance_and_missing.json',provenance);csvsave(H/'固定深读决策出处与缺失.csv',provenance)
    support=[p for p in pairs if p['timely'] and p['kind']!='control' and p['decision_evidence'].get('P2_next_in_recorded_options') is False and p['decision_evidence'].get('P2_next_was_initial_history') is True]
    hyp=dict(label='唯一探索性决策假设；阅数后提出，未经干预',observable_condition='存在未检四邻格，同时存在初始已完成历史四邻格；PPCPP local分支只给未检格评分，不允许此时先走历史格。',phase='两个已保存31x21、p30输入的事件起点共同状态；原seed逐项保留。',decision_to_test_later='只检验一次先走指定历史邻格是否改变完整后续成本；其后恢复原PPCPP。此为固定状态因果探针，尚非可部署选择器。',support=[dict(pair_id=p['id'],seed=p['seed'],delta=p['delta'],current=p['common_state']['current'],PPCPP_next=p['PPCPP_next'],saved_P2_next=p['P2_next'],trace_pointer=p['decision_evidence']['event_pointer']) for p in support],denominators=dict(timely_events_pairs=24,timely_event_states=8,timely_event_geometries=5,support_pairs=len(support),support_states=len({p['case'] for p in support}),support_geometries=len({p['geometry_id'] for p in support}),all_legal_events_pairs=36,all_legal_event_states=12,all_legal_event_geometries=6),boundary='2族2几何，未达2族3几何描述性重复条件；支持不是因果。其他12个主视图正差配对无此首分叉证据；6同长配对也不支持普遍阻碍。',evidence='原始local候选和P2字面下一格直接记录；只凭冻结源码说明未检候选门；P2为何走该格未知。',future_single_variable_test='如负责人另行批准：只在这两个原始输入和既定seed上做一次动作干预，指定动作使用本轮封存的P2历史邻格，仅作为诊断处理而非给在线算法P2预知；控制组原版，处理组仅该一步改变，其余保持原版/同历史previous/预算/截止。预登记动作与停止条件后才可运行，不扩地图和窗口、不重启局部P2、不加终点奖励。审查完整合法覆盖、遮挡暂缓、返航、L/C/R、历史重复、90/180转弯及完整入口时间，失败/反向/迟到全保留。',not_proven='只改一步会否收益、收益幅度、何时应走历史格、在线判别规则与计算开销均未知；不能归因全部8或70步，更不能直接归因133或255步返航差。')
    save(H/'探索性假设.json',[hyp])
    report='# 覆盖顺序分歧只读诊断：通俗结论与完整报告\n\n'
    report+='本轮已定位到真实的覆盖顺序和首分叉决策差别，尚未验证任何改进算法。不是把旧返航差再解释一次，也不能据此把P2当最优。全部证据来自原96正式路线；新增规划器、覆盖精确搜索、候选生成、地图、seed、预算档和留出均0。完成后封存停止，交负责人审核。\n\n'
    report+='## 1. 固定样本、预算与主要结果\n\n原16状态、48同输入同seed配对全部保留；两历史准备仅核来源。原入口严格<20秒，未放宽；18个迟到配对只进附视图。每种布局最多两个尺寸几何，进度10/30不增加几何分母；三个seed不是三张地图。原seed：'+str(seeds)+'。\n\n'
    rows=[]
    for v,label in [('timely','主及时'),('legal','附全部合法含迟到')]:
        for z,zn in [('events','障碍'),('controls','控制')]:
            x=a['views'][v][z];rows.append([label,zn,x['pairs'],x['states'],x['geometries'],f'{x["positive"]}/{x["equal"]}/{x["reverse"]}',f'{x["signed_costs"]["L"]} = {x["signed_costs"]["C"]} + {x["signed_costs"]["R"]}'])
    report+=table(['视图','组','配对','状态','尺寸×布局','PP更长/同长/更短','ΣΔL=ΣΔC+ΣΔR'],rows)
    report+='\n全48配对：42采集顺序不同、6整条路线相同，0个“不同路线但完整采集顺序相同”。主障碍24配对中21采集顺序不同、3同路线；其中21x15_maze_p10三个seed顺序不同但完整成本同长，不能将顺序不同直接判为决策缺陷或仅凭某个评分判错。主控制6配对也全部顺序不同且PP更长；没有识别出障碍专属因果效果。\n\n'
    report+='## 2. 全16状态与种子范围\n\nΔ统一为PPCPP−P2。下表主视图n=0仍保留；附表列所有合法seed均值。所有原seed值/范围/目标前五详见timely与legal状态CSV，全目标未筛选原值另表。\n\n'
    ll={s['case']:s for s in a['views']['legal']['states']};rows=[]
    for s in a['views']['timely']['states']:
        m=s['mean'];l=ll[s['case']];rows.append([s['case'],s['n'],str(m) if m else 'NA：迟到',s['ranges'] or 'NA',l['mean']])
    report+=table(['状态','及时seed n','主均值L/C/R','主范围L/C/R','附均值L/C/R'],rows)
    report+='\n尺寸/布局/进度/尺寸×布局均已输出事件专用分层；控制单列。主事件共5几何，附事件6几何，主控制1几何，附控制2几何。主视图缺31x21_maze_p10、31x21_serpentine_p10、31x21_rooms两进度及31x21_control两进度，共18配对；其合法结果不能冒充共同20秒成绩。\n\n'
    report+='## 3. 第一次分歧与成本事实\n\nA按完整顶点共同前缀，含previous、已采集合与累计资源；B按实际首次采集目标前缀。逐目标排名差与首次到达步差分开，不能以B的相同采集历史替代A的共同完整状态。所有96序列从轨迹重建，不用计划目标次序；初始即时采集单列。U空集分支已实现，本批96路线无空U，六档均对应不同步数，共576切片。\n\n主障碍A处：18次为保存的local事件起点，3次在已选恢复段内部，3次没有分叉。所有有分叉的两条字面后缀均从同位置/previous/历史/资源审计，合法完整；Δ后缀长度等于ΔL。这仅证明存在另一条完整后续方案，不能把收益归因于一个动作。完整后缀已保存在配对索引，未拼接任何路线。\n\n21x15_maze_p30是清楚的A/B不同例：A在第2步(19,7)，两者下一格分别(18,7)/(19,6)；B无共同新采集目标，下一新目标分别第3步(18,7)、第5步(18,5)，其到达前状态不同。PPCPP的恢复事件在第0步选择(18,7)，候选距离未存；不能将第2步的沿途分叉称为重新做了一次恢复目标选择。\n\nΔR大于ΔL的情况保留负ΔC：主事件总账798=−801+1599。31x21_maze_p30每seed为8=−125+133，31x21_serpentine_p30为70=−185+255。返航差不等于可以净省的总步数。两算法各自的已有返航均为自己完成位置的最短图路，沿用前轮复核。\n\n'
    report+='## 4. 六个固定深读例\n\n按运行前规则选首个正差/同差，不选最大值；rooms同长与control同长在主视图缺失，不用迟到补。每例一页SVG/PNG，带共同前缀、分叉、首次不同采集目标、75/90%剩余集合、末格和返航。\n\n'
    for ex in a['examples']:
        p=next(p for p in pairs if p['id']==ex['pair_id']);d=p['decision_evidence'];r=routes[p['PPCPP_id']];q=routes[p['P2_id']]
        report+=f'### {p["id"]}（{ex["category"]}）\n\n[单页图](figures/{p["id"]}.png)，[完整字段](deep_reads/{p["id"]}.json)。PP/P2的L={r["L"]}/{q["L"]}、C={r["C"]}/{q["C"]}、R={r["R"]}/{q["R"]}；Δ={p["delta"]}。A末端步{p["common_state"]["step"]}，共同新增采集数{p["acquisition_divergence"]["common_target_count"]}。\n\n'
        if d['owner_kind']=='local':
            report+=f'原始字段`{d["event_pointer"]}`直接记录选格{d["chosen_record"]["cell"]}、分数{d["chosen_record"]["score"]}，最高分同分候选{d["recorded_max_tie_count"]}个；P2下一格在已存候选中，原评分{d["P2_recorded_option"]["score"]}。'
            if p['delta']['L']==0:report+='虽P2的下一格评分更低、顺序不同，总长度却同长，是“分数/顺序差不直接等于长度缺陷”的反例。'
            elif d['recorded_max_tie_count']>1:report+='这是原评分同分、坐标规则决定选项的事实，未测试改tie会否获益；控制同样存在此现象，不能称障碍专属。'
            else:report+='两条完整后续成本不同，但未干预下一动作；不能断言较高分是差距原因。'
        elif d['owner_kind']=='recovery':report+='原trace仅记录第0步恢复目标(18,7)；A分叉位于该恢复段内部。原候选距离、备选排名未存，未知，不执行核心补trace。'
        else:report+='整条路线相同，无A或B下一分歧；不能虚构决策字段或失败。'
        report+='\n\n'+table(['采集比例','PP/P2剩余碎片数','PP/P2目标基地中位图距','Jaccard'],[[s['percent'],str(s['PPCPP']['fragmentation']['components'])+'/'+str(s['P2_MULTI']['fragmentation']['components']),str(s['PPCPP']['remaining_base_distance']['median'])+'/'+str(s['P2_MULTI']['remaining_base_distance']['median']),round(s['jaccard'],6)] for s in p['slice_pairs'] if s['percent'] in (75,90)])+'\n'
    report+='## 5. 全批切片与反向关系\n\n六档按新增U的ceil阈值切片；剩余集合自身的诱导连通分量不是飞行域断开或必需区域数。主图75/90%的变化说明两条原路线留下的任务不同，不给出同任务局部收益。全576路线切片及288配对比例映射均交付，两空Jaccard=1，空距NA。\n\n'
    for tag in ('PPCPP_fewer_fragments_but_not_shorter_total','PPCPP_lower_remaining_median_distance_but_not_shorter_total'):
        rr=[r for r in a['counterexamples'] if tag in r['tags']];tm=[r for r in rr if r['timely']];report+=f'- {tag}：全合法{len(rr)}个配对×比例观测，主及时{len(tm)}个；全合法涉及状态{sorted({r["case"] for r in rr})}。\n'
    report+='\n全批反向关系账逐条保留全部33项（两个标签无重叠），种子/比例不当独立几何。此账只针对预定25/50/75/90%；不是筛选器。PP总长度更短反例为0；主rooms同长与control同长均缺；不同路径但采集顺序完全相同缺失，未补造。21x15_maze_p10中较少碎片也没有总长度优势，31x21_maze_p30的部分切片距离更小但仍较长：单个规整度或基地距离特征不足以判定哪条完整路线更好。\n\n'
    report+='## 6. 决策证据、唯一探索性假设与停止\n\n所有原始字段/JSON指针/邻近事件/缺失值见decision_provenance_and_missing.json。冻结源码reward_options仅对未检四邻格列候选，权重2与0.5；choose_neighbor按(-score,cell)排序。这是源码规则证据，未重新计算任何运行评分。恢复目标候选及距离缺失，P2没有在线逐步动作trace；它的source/events/improvements是最终路线来源和搜索阶段记录，不能当在线思考过程。\n\n唯一假设：**有未检邻格时的“必须先采邻格”候选门，可能在部分已有历史通道的状态阻止一次有利的先移位。** 它来自阅数后观察，未经预登记检验。31x21_maze_p30与31x21_serpentine_p30三seed的共同起点(5,2)，PP仅存未检候选(5,3)，P2字面下一格(5,1)属于初始已采历史而非pending。这给出了可定位的候选空间差异，不只是在终点说“离基地远”。\n\n支持为6/24主障碍配对、2/8状态、2/5几何；三seed='+str(seeds)+'。全合法为6/36配对、2/12状态、2/6几何。只有2族2几何，未达2族3几何条件，不称有限跨几何重复。另12个主障碍正差配对首分叉没有此证据（9个P2下一格在local候选、3个恢复段），6个同长配对也不支持普遍阻碍；控制首分叉没有这一差异，但不同输入不能据此证明障碍因果。尚未知何时该先移位、只改一步是否有效或在线如何选择。\n\n如未来另获批准，单变量诊断可仅在这两个原始输入/既定seed的封存共同状态，处理组强制一次封存的历史邻格步、其后恢复原PPCPP，对照组原版；动作来自保存P2仅用于诊断处理，不给在线算法P2预知。预登记后才运行，审查完整覆盖/暂缓/返航、L/C/R、历史重复、90/180转弯、完整入口与同预算，反向/失败/迟到都保留。本轮没有执行。仅改一步不能承诺净省8/70步，更不能承诺追回133/255步返航差。\n\n没有第二个足够独立且具体的假设：同分坐标规则虽可定位，但旧四方向已停止，不能换名重开；剩余集合更规整/距离更小存在反例；恢复备选缺trace，不能强补机制。上述候选门检查也不是重启局部P2混合（旧固定窗口未改变路线）、不是LAST、不是终点奖励。当前只有一个待因果验证的决策线索，没有已验证可实施的改进机制、论文主算法或创新点。封存后等待负责人审核，不自动开发或实验。\n\n'
    report+='## 7. 核验与证据入口\n\n先执行上游tail_verify_v02.py，upstream_verify.log全部通过；该日志末句沿用前轮analysis+verify合计32 BFS/58 Dijkstra措辞，本轮这次重跑实际为16 BFS+29唯一起终点Dijkstra、96逻辑终点核查（67缓存命中），未重跑前轮分析。运行前preseal.json封存协议、两分析脚本和414个来源hash；后续图文/复核代码列最终manifest，不冒称它们运行前已存在。\n\n本轮分析16基地BFS、16独立全图Dijkstra，核对5312顶点距离，576切片；最终verify再各16次。连同上游本次核验实际48次BFS、61次Dijkstra（其中29为唯一起终点查询、32为独立全图表）。图表/报告生成无距离查询；连通分量洪泛单独为集合统计，不是距离求解。新增覆盖求解与规划器全部0，不将只读分析耗时称算法提速。最终verify的实际成功状态以verify.log/verification_receipt.json为准，调用账见call_ledger.json。\n\n交付：48全配对索引与分歧.csv、48共同轨迹与采集分歧.csv、96路线指标.csv、acquisitions/96文件、slices/96文件、全部目标排名与首次到达差.csv、全部采集比例配对切片.csv、主/附状态与分层CSV、全批反向关系账.csv、6固定图与deep_reads、decision_provenance_and_missing.json、探索性假设.json、预登记/source_hashes/preseal、review_packet、manifest、实际日志。失败账为空：本轮分析没有技术失败、重试或被替代运行。\n'
    write('通俗结论与完整诊断报告.md',report)
    write('review_packet.md','# 负责人审核入口\n\n先读通俗结论与完整诊断报告.md及预登记操作化协议.md，核对主障碍24配对/8状态/5几何与控制6/2/1，附障碍36/12/6与控制12/4/2。42顺序不同、6同路线；21maze10是不同顺序同长，不能判缺陷。\n\n六例按ID预定规则，不按最大差；rooms/control主同长缺失。原始记录见deep_reads及决策出处表，恢复缺候选距离/P2缺在线trace明确保留。唯一假设是未检邻格存在时先走历史邻格的候选门，支持2族2几何，低于3几何描述条件；并无已验证机制。旧LAST/四方向/局部P2不重启。\n\n只读复核命令（从根目录）：\n\n```powershell\n.\\运行环境\\python\\python.exe -B -X utf8 复杂障碍覆盖顺序分歧只读诊断_v0.1_20261021/order_verify.py\n```\n\nverify仅读；不导入planner，不重做覆盖最优，不生成路线。核对原始来源hash、预封存与最终manifest、双指标、独立采集索引/六档切片、全部JSON/CSV/固定选例/图hash/调用账。每次verify普通BFS16及独立全图Dijkstra16，请审核另行记账；本交付账只包含一次成功最终核验。日志与收据排除manifest自引用。\n\n本轮完成即停，任何动作干预都尚未授权执行；不提交或推送Git。\n')
    print('Saved report, trace provenance, counterexamples, one post hoc hypothesis; searches=0')
