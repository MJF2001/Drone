import ast,collections
from diag_common import *
def table(h,rr):return '\n'.join(['|'+'|'.join(map(str,h))+'|','|'+'|'.join('---' for _ in h)+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])
def write(n,s):
 with (D/n).open('x',encoding='utf-8') as f:f.write(s)
def main():
 a=read(D/'source_audit.json');selection=read(D/'selection.json');exact=read(D/'exact_index.json');accepted=read(D/'exact_acceptance.json');positive=read(D/'positive_index.json');assert positive['passed']
 rows=[]
 for c in exact['records']:
  p=read(D/'exact_inputs'/(c['family']+'.json'));rows.append([c['family'],c['id'],len(p['required']),len(p['free']),len(p['old_patch'])-1,c['results']['exact_bfs']['length'],c['results']['exact_dijkstra']['length'],'通过'])
 sourcepaths=[S/'hybrid.py',S/'runtime.py',S/'audit.py',R/'range_p2_engine_20261015.py',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/planners.py',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/model.py',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/unified_geometry.py']
 anchors=[]
 for path in sourcepaths:
  for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
   if any(x in line for x in ('def window','def combine','def run','def accept','local=replace','er=(engine','def offer','def opt','def fallback','demand=','if valid and','offer(g.expand','stage(label','def expand','def precheck','s.targets-s.covered','distance_budget','same current')):anchors.append(dict(file=str(path.relative_to(R)),line=i,text=line.strip(),sha256=sha(path)))
 save(D/'source_anchors.json',anchors)
 lines=['# 局部P2最后有效性检查\n\n2026-10-20。**已封存，待负责人审核。**\n',
 '**未发现生产局部任务/固定出口/验收更新链的具体错误；三个固定抽查小窗口已证明原窗口最优。** 正控制证明同一引擎和生产验收链能把6步冗余窗口改成4步。这个结论不等于102窗口全最优，也不保证不存在其他未覆盖错误。原324的零完整收益结果没有被本轮推翻。\n',
 '## A：102原始调用与真实责任\n',
 f'先运行上游verify通过，新增求解0；再逐一核原manifest、输入hash、worker实际源码hash，独立重建窗口/真实H/任务/前后缀/固定出口，并重核全部102非空调用。任务数范围{min(x["task_count"] for x in a)}～{max(x["task_count"] for x in a)}，每次required与local_H交集为空，入口即时已采不重复分派，实际初始pending数=required数。没有把H误传成“全部责任任务已完成”。\n',
 '局部Snapshot在生产hybrid.py的replace处构建：targets=责任子集，covered=真实前缀已采，free=完整当前s.free，current=入口，base=固定出口，old_route=原窗口，distance_budget扣外部固定步数。任务与H允许不为包含关系，但g.precheck/g.expand/single_cell_audit都按targets−covered判剩余，不会把不在targets内的H错误视作任务。局部g.expand最后只连到局部base=出口；真实返航基地仅在保留后缀中，不多返航一次。\n',
 '这批原始输出记录了cfg/返回patch/events，而没有另存引擎收到参数的独立receipt；“实际传入值”由原始cfg加已封存且hash一致的生产replace调用推导，不把它冒充原始参数日志。新正控制及精确验收探针对收到的snapshot字段逐项断言，来源界限见source_audit.snapshot_evidence。\n',
 '原P2 offer保留：g.check_time→生产accept→g.check_time→valid且len(route)<len(best)才更新。旧窗口与候选都以含两端的顶点数比较，len差等于步数差；没有混用步数/顶点数。生产accept先验局部任务/出口/预算，再用原combine验完整路线；没有禁止经过外部未采任务、没有删保留后缀或重复吞接口。若局部/完整非法则抛显式失败，不会悄悄用old_suffix掩盖；原102均正常finished。\n',
 '生成→优化→展开→检查证据来自原events以及未变源码。H/V_generate、H/V_raw、NN_raw、scan/NN_opt与expand、deep和multi额外候选阶段均完成；源码在这些stage里确实调用candidates、opt、g.expand和offer，因此不是仅空循环。但旧improvements只记录严格接受改进，未记录未改进候选的顺序、展开长度或拒绝原因。它们统一标为**未记录**，不能用新测试倒填原102日志，也不能断言曾产生了更短而被拒的候选。逐调用ID/输出路径/入口出口/任务/H/预算/原窗口/events见source_audit.json；函数行号、文本及源码hash见source_anchors.json。\n',
 '## B：4个真实局部入口正控制\n',
 table(['问题','原窗口步数','手算下界/最优','真实局部入口','生产拼接/offer测试'],[['冗余合法窗口',6,4,'4步、source改变','4步、选择LOCAL_P2'],['最优保底',4,4,'4步、old_suffix','4步、同长P0']]),'\n',
 'F为0..4的一维五格，责任{1,3}且H空，入口0、出口4，资源上限6。完整fixture、预期及运行器均事前封存，固定seed20261020，20秒入口含构造/真实引擎/生产检查及完整编码。起终点曼哈顿下界4，4步路线可行，因此该人工问题最优4是手算证明，不是额外精确求解。\n',
 '外层正常调用会强制重生成PPCPP，所以没有声称测试了完整生产hybrid入口。四次都没有调用PPCPP：直接局部测试先用纯桩取得未改生产accept闭包，再运行原局部引擎；拼接测试只注入合法手工P0，后续用原hybrid生产选区/原局部引擎/原accept/combine/严格择优。两类每夹具各一次，共4真实局部引擎调用，未另写宽松验收器。获取闭包的桩不算求解，日志边界明确。\n',
 '## C：3个固定选样与双独立精确诊断\n',table(['族','原调用ID','责任数','F格数','原窗口/原P2','BFS最优','独立Dijkstra','原生产验收'],rows),'\n',
 '所有事件rep0非空窗口的资格及未入选原因在selection.json，按(责任数,F格数,ID)每族取首个，未按收益挑例。三个具体输入均保留完整F、真实H、入口/出口/旧窗口和距离额度。BFS使用(格,已采bitmask)，Dijkstra另用(格,剩余任务frozenset)、独立优先队列和邻居顺序；不共享搜索函数或planner距离。两者初始位置都即时采集，完整单位四邻接；状态上限2000000、每次60秒软检查+60秒进程看门狗，均正常证明最优而非超限。\n',
 '最优性依据为BFS按层首次弹出“全部任务已采且在出口”的状态，所有更浅层已穷尽；另由独立Dijkstra最小代价settle同一接受状态复算。原始路线、深度计数/发现与弹出数、时间、独立复算结果均保留。三例还恰好达到入口出口距离下界2/3/4；不需要假设目标间曼哈顿可替代障碍图距离。没有裁剪F。\n',
 '六条精确路线逐格核查后，经未改原hybrid accept/combine和独立完整audit通过；局部snapshot字段逐一对照，拼接后外部前后缀保持。精确值等于原窗口和原P2，无更短值触发条件，故诊断引擎重放0，未增加只读候选插桩或改搜索。\n',
 '验收探针首版失败是测试载荷错误：JSON读回的原P0.route仍是list坐标，原生产内存接口需要tuple坐标，最终set(route)触发unhashable list。失败原脚本/日志与捕获reason保留；validate_exact_v02只把注入手工P0恢复为生产相同tuple表示，原引擎/验收/324输出未改，随后六纯验收探针通过。不是精确路线被真实合同拒绝，也没有额外求解或重试精确。\n',
 '## 能证明什么、不能证明什么\n',
 '①三个被选小窗口：原窗口=精确最优，因此确实没有固定接口内少步空间。②其余99次局部调用：未证明最优；重复共享几何，三个抽查也不等于三个大窗口。③本轮未发现适配/验收阻止短候选的生产错误；人工6→4及精确生产验收提供正证据。④未记录的旧候选长度/拒绝原因仍证据不足，不能将finished升格为最优或把所有old_suffix归于实现错误。本轮未出现“精确更短而P2漏掉”的例子，不能据此排除其他窗口可能漏解。\n',
 '建议结束本固定混合规则，不扩窗口、不追改搜索。可以向负责人建议回到四方向支线的接口讨论；**本稿没有授权恢复或删除捕食者断言**，仍须明确新接口授权与新门槛。没有修复生产核心，也不需要据当前证据重跑324；若后续发现具体错误再另立影响清单。\n',
 '## 实际调用账与停止\n',
 '正控制真实入口4（原局部引擎4，PPCPP0）；精确BFS3、独立Dijkstra3；诊断引擎重放0；原324重跑0。纯闭包获取/手工P0注入/6条精确路线验收及失败定位探针不算真实规划器。原历史与冻结字节不改，不扩图/窗口/出口/预算，不用留出，不提交推送。\n',
 '只读verify只核来源/原102日志/选样/原正控制输出和精确路线/生产验收记录，**不再运行精确搜索**，避免超过最多6次的诊断上限。完整运行环境继承上一批事前byte清单并在新增求解前加入本轮程序/输入/配置，Windows系统范围限制保留。\n\n已封存，待负责人审核。\n']
 write('最后有效性检查报告.md','\n'.join(lines));save(D/'call_ledger.json',dict(positive_entries=4,positive_real_local_engine_calls=4,real_PPCPP_calls=0,bfs_calls=3,dijkstra_calls=3,replay_calls=0,original324_reruns=0,exact_acceptance_pure_probes=6,positive_full_hybrid_tested=False,failures=[dict(path='validate_exact.log',stage='pure acceptance payload',reason='JSON coordinate lists not restored to production tuple representation',successor='validate_exact_v02.py',extra_solver_calls=0,production_code_changed=False)]))
 write('README.md','# 局部P2最后有效性检查\n\n已封存，待负责人审核。先读最后有效性检查报告.md。来源审核102、预登记/事前环境、两夹具/4正控制、3固定选样/全部未选理由、两独立搜索/6原结果、6生产验收探针、失败首版/后继、call_ledger、manifest和verify齐全。旧324和冻结不改，四方向仍暂停。\n\n命令：包内Python -B -X utf8 本目录/verify.py。只读复核不重跑任何规划器或精确搜索，manifest仅排除自身与verify.log。\n')
 write('review_packet.md','# 负责人审核包\n\n请先读最后有效性检查报告。原324的verify已实际运行，102原局部调用逐项source_audit；cfg/patch/events是原始记录，snapshot字段由封存replace推导，不冒称独立原参数日志。原improvements只是接受者，未记录拒绝/非改进长度。\n\n正控制4真实局部引擎，手工旧窗口6→4/4→4，原生产accept/combine，显式手工P0桩，未声称原生PPCPP完整hybrid测试。事前清单覆盖程序输入、继承原运行环境，未事后补录solver依赖。\n\n固定选样小I2任务/L3/Z4任务，原窗口2/3/4，BFS与独立Dijkstra一致，原验收通过，未触发诊断重放。不能推广102全部最优。验收探针旧版JSON list/tuple失败，原日志保留，v02仅改测试载荷，无真实求解追加/生产修改。\n\nverify只读核原始证据/路线/选择/调用账，不再执行最优搜索。建议结束固定混合，但四方向必须另授权接口与门槛，执行者到此停止。\n')
 print('REPORT/LEDGER COMPLETE')
if __name__=='__main__':main()
