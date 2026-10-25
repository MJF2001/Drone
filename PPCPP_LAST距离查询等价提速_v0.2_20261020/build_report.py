"""Delivery text and tables from measured data; no planning or extra timing."""
import difflib
from common import *
def table(headers,rows):return '\n'.join(['|'+'|'.join(map(str,headers))+'|','|'+'|'.join('---' for _ in headers)+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def write(name,s):
 with (H/name).open('x',encoding='utf-8') as f:f.write(s)
def main():
 d=read(H/'analysis.json');p=read(H/'protocol.json');g=read(H/'gate_index.json');di=read(H/'distance_diagnostics.json');inv=read(H/'imported_dependency_inventory.json');t=d['timing'];s=d['summary'];pairs=d['time_pairs'];v1=t['LAST_V1']['mean']*1000;v2=t['LAST_V2']['mean']*1000;pp=t['PPCPP']['mean']*1000
 failures=dict(formal_calls=810,formal_technical_failures=0,formal_deadlines=0,formal_non_time_discrepancies=0,watchdogs=0,gate_unexpected_failures=0,expected_deadline_injections=9,expected_reservation_infeasible_fixture_versions=2,offline_analysis_attempts=[dict(log='analysis.log',status='failed',reason='statistics launched before asynchronous post-run dependency inventory completed; FileNotFoundError',planner_calls=0,source_changed=False),dict(log='analysis_completed.log',status='passed',reason='same analysis source rerun after inventory completed',planner_calls=0)],impact='No production/input/raw result changes; zero formal invalidation or reruns; failed analysis never enters formal summaries.',protocol_deviation='Individual hashes for 90 eagerly imported optional package files were supplemented after timing. Production project sources, executed geometry, input/order/deadline/gates were presealed and critical production sources logged/hashed by each worker. Full optional package content preseal is not established; disclose for reviewer, do not relabel supplementary inventory as pre-registration.')
 save(H/'failures.json',failures)
 old=R/'PPCPP_LAST新开发地图验证_v0.1_20261020'
 write('wrapper.diff',''.join(difflib.unified_diff((old/'worker.py').read_text(encoding='utf-8').splitlines(True),(H/'worker.py').read_text(encoding='utf-8').splitlines(True),fromfile='old/worker.py',tofile='new/worker.py')))
 write('修改范围与等价依据.md','''# 修改范围与等价依据

1. candidate_v1.py与上轮candidate.py字节相同；candidate_v2.py仅改版本和一行距离方向，见minimal_candidate.diff。e的目标集合、set遍历、坐标tie、候选数、P0/P1流程、严格择优均不变。
2. runtime.py/common.py/audit.py/audit_adapter.py字节相同；共享冻结model/BFSMetricGeometry/UnifiedGeometry/PPCPP/奖励/验证源码不修改。旧目录和历史时长不覆盖。
3. isolation.py在入口开始前以绝对路径加载不同candidate，并为未改runtime的局部import提供确定别名；每个正式进程只运行一种方法一次。PPCPP绑定V1且mode=PPCPP；两LAST均mode=LAST。选择、导入、源码哈希均在原暖入口外。
4. worker.py必要变化见wrapper.diff：预读job后选择版本；计时外收集实际生产源码哈希；外层附加production_sources。原run_payload的计时起止、原raw完整编码、20秒拒收、读输入限制不变；V1/V2做同样来源记录，不加计时内Spy。正式raw结构仅version不同，额外来源元数据与原job/模块清单一样在外层，不参与计时。

F无向单位边使distance(a,b)=distance(b,a)，同一坐标tie得到同一e。数学对称只保证距离/e，不单独保证路径；BFSMetricGeometry记录的first_direction确实不同。实际UnifiedGeometry.path固定sorted端点后调用Geometry.path，绕过其父类依赖first_direction的path，因此连接选择不受此状态改变影响。额外夹具证明原始方向A*会选不同同长路线，而实际Unified连接及完整LAST坐标相同。P0/F/F-e三私有缓存仍隔离，源点行数量影响成本不改变图或采集规则。

逐字段比较以semantics.py为准：raw所有字段均保留，只有raw.version、P0.seconds/accepted_seconds/剩余budget/时间超限标记、P1.accepted_seconds排除。外层entry/phase/injection时间及来源元数据单独验。所有trace options、恢复目标、阶段、全部路线/诊断路线、状态/原因/phase1_end均比较；双指标和末新采集格另算。跨重复seed=20261020+rep是声明元数据，检查seed_used=False后仅稳定性比较把该seed注记归一；同重复V1/V2和P0比较不忽略seed。算法决策始终完整保留。

有限墙钟下不要求两版成功率必然一样；双方完成且无截断时完整语义应相同。九共同截止注入均在P0完整后使整入口拒收，不回填P0。实际单源BFS内部固定钟检查在第三个check_time抛截止，无部分行入缓存。该验证为契约检查，不是硬实时证明。
''')
 lines=['# LAST距离查询等价提速结果\n','2026-10-20。**执行完成，待负责人审核。** 实现效率修正，不是新规划策略或最终留出验证。\n',
 f'**LAST等价实现效率修正通过本轮语义与效率检查。** 114新鲜回归配对、10边界配对均一致；810正式调用全部完整合法及时，270个V1/V2配对逐字段一致，540个P0配对与同批原PPCPP一致，162方法—状态组5重复稳定。正式失败、截止、看门狗和非时间差异均0。\n',
 f'本轮重新实测均值：PPCPP **{pp:.6f}ms**、LAST_V1 **{v1:.6f}ms**、LAST_V2 **{v2:.6f}ms**。V2/V1={v2/v1:.6f}，即V1/V2={v1/v2:.4f}倍、均值少{v1-v2:.6f}ms（{(1-v2/v1)*100:.4f}%）；V2/PPCPP={v2/pp:.6f}，仍多{v2-pp:.6f}ms。新旧同批810新时间，未拼接上轮时间，也未用阶段相减估算新总时间。\n',
 '路线收益完全保留：54状态27短27平0长，5530→5476，省54步（0.976492%）；每个改善仍只省2步。此次没有新增路线收益。90度转弯仍752→796多44，180度34→31，不能把计算提速说成消除了路线代价，也不推真实能耗或最优性。\n',
 '## 前置协议、门槛与语义\n',
 f'预登记先于任何新规划器调用，114输入/10夹具/810顺序固定；门槛实际{g["calls"]}调用：114×2=228、10×2=20、缓存Spy2、V2截止注入9。114完整配对、228次对旧封存逐字段比较（两版本各114）、9旧夹具每版对旧结果均通过。新增夹具包含原始方向A*同长但坐标不同的反例；实际Unified路径及完整route/trace/沿途采集相同。原runtime及V1字节一致，新PPCPP封装还在正式540个P0配对验证。\n',
 'e、selected、非时间P0/P1状态/原因、全部逐决策trace（包括options、goal、phase）、完整route/diagnostic_route、phase1_end和末新采集位置均保留。仅忽略预先列举的时间/版本字段；详见修改范围与等价依据.md、protocol.semantic_whitelist和semantics.py。全部成功P0/P1/final独立奖励/BFS/采集/择优审核及两套指标复核。全局返回路径相同之外，所有未选中的成功替代也审。\n',
 '九截止位置均P0已完成而整体晚到拒收，selected=None、route空，不回填及时P0。单源BFS内部固定钟0、0、2/deadline1验证实际循环第三次检查抛DeadlineExceeded，已缓存行0。两版本Spy均3个不同cache与distance_rows，工作图恰为F-e；单格衔接采集助手检查通过。正式无Spy/注入。截止等价指预算契约相同，不要求任意墙钟下成功率相同；完整语义比较限双方及时完成。\n',
 '## 共同条件新时间\n',
 table(['方法','调用/及时/合法','均值ms','中位ms','P95ms','最大ms'],[[m,f'{t[m]["N"]}/{t[m]["eligible"]}/{t[m]["legal"]}',*[f'{t[m][k]*1000:.6f}' for k in ('mean','median','p95','max')]] for m in ('PPCPP','LAST_V1','LAST_V2')]),'\n',
 '串行独立进程、线程1、种子20261020+rep，三方法按状态序号和重复轮换。共同20秒暖入口包含解码/构造/P0/候选/P1/几何/审核/完整原raw编码；启动/导入/输入输出磁盘/独立外审在外，90秒仅看门狗。五重复全部保留，包括27同长和2坏P1，不取最好一次。P95用(n−1)×0.95线性插值。\n',
 table(['方法','P0 ms','候选ms','P1含审核ms','最终审核ms','编码ms','未分段ms'],[[m,*[f'{t[m]["phases"][k]*1000:.6f}' for k in ('p0','candidate','p1','final_audit','encoding')],f'{t[m]["unsegmented"]*1000:.6f}'] for m in ('PPCPP','LAST_V1','LAST_V2')]),'\n',
 '候选阶段包括新建full几何和所有距离查询；P1分段含其内部审核；P0内审包含在P0。未分段是实测入口减这些分段，含解码、输入契约、Snapshot、P0隔离序列化、标记及框架开销。不是漏计入口，也不能从旧候选时间直接推算新入口。\n',
 table(['参照（V2相对）','均值比例','绝对差ms','54状态均值快/平/慢','270同重复快/平/慢'],[[ref,f'{pairs[ref]["ratio_means"]:.6f}',f'{pairs[ref]["delta_ms"]:.6f}','/'.join(str(pairs[ref]['state_means'][k]) for k in ('faster','equal','slower')),'/'.join(str(pairs[ref]['calls'][k]) for k in ('faster','equal','slower'))] for ref in ('LAST_V1','PPCPP')]),'\n',
 '## 分层\n',
 table(['因素','层','状态','PPCPP ms','V1 ms','V2 ms','V2/V1','V2/PPCPP','V1参照状态快/平/慢','V1参照逐次快/平/慢'],[[r['factor'],r['value'],r['states'],*[f'{r["timing"][m]["mean"]*1000:.6f}' for m in ('PPCPP','LAST_V1','LAST_V2')],f'{r["timing"]["LAST_V2"]["mean"]/r["timing"]["LAST_V1"]["mean"]:.6f}',f'{r["timing"]["LAST_V2"]["mean"]/r["timing"]["PPCPP"]["mean"]:.6f}','/'.join(str(r['state_pairs']['LAST_V1'][k]) for k in ('faster','equal','slower')),'/'.join(str(r['call_pairs']['LAST_V1'][k]) for k in ('faster','equal','slower'))] for r in d['strata']]),'\n',
 '各层完整中位/P95/最大、两参照快慢与绝对时间在analysis.strata和分层时间配对.csv。54状态各5原值/均值/比例/毫秒差在54状态配对.csv；全部810原值与分段在810调用时间与分段.csv，不只汇总均值。尺寸、宽度、族和历史共同变化，不作单因素因果推断。\n',
 '## 只读距离行诊断\n',
 f'主54各用两个独立UnifiedGeometry，按原set遍历查询两方向，全部待检格距离和e相同。pending范围{min(x["pending"] for x in di)}～{max(x["pending"] for x in di)}；旧实际BFS行数范围{min(x["v1_rows"] for x in di)}～{max(x["v1_rows"] for x in di)}，新{min(x["v2_rows"] for x in di)}～{max(x["v2_rows"] for x in di)}；合计{sum(x["v1_rows"] for x in di)}→{sum(x["v2_rows"] for x in di)}。零距离待检格{sum(x["zero_distances"] for x in di)}，current=base状态{sum(x["current_is_base"] for x in di)}，base仍待检状态{sum(x["base_in_pending"] for x in di)}。逐例原值/距离表全部保留；未出现的零距离条件不伪称本54已覆盖，e=base由固定边界测试覆盖。\n',
 '这只是几何距离，不运行覆盖最优搜索，也不是正式速度。缓存行倍率不等于整算法倍率；实测整入口已包含后续路径、几何及编码，不隐藏缓存复用副作用。\n',
 '## 路线、覆盖、未选替代\n',
 table(['指标','PPCPP','V1最终','V2最终','P1全部'],[[k,*[d['metric_totals'][m][k] for m in ('PPCPP','LAST_V1','LAST_V2','P1')]] for k in d['metric_totals']['PPCPP']]),'\n',
 '54输入全部P1完成，P1对P0为27短25平2长。large_I_straight_p30的P1多10、medium_I_straight_p70多2，两版均保P0，所有计算仍计时。完整成功时最终不变长来自保留P0的构造，不作为创新。工作图通路额外代价逐段外审保存在analysis.calls.audit，不能等同覆盖顺序无损。\n',
 '当前可检5982和待检3408格次均100%完成；公开6048完成6027，暂缓21不是完成；45历史后遮挡格次保留。净省54由历史重复+2、本轮重复−8、非目标−48组成；覆盖完成前+343、返航尾段−397。提速保留了这些原取舍。完整路线每项指标见完整路线指标.csv及analysis，不以重复次数扩增样本。\n',
 '## 来源、偏差与证据边界\n',
 f'全部项目生产执行源码、输入、顺序、门槛与计时契约在正式前封存；worker记录输入唯一读取、实际模块路径及关键源码哈希，每次核对通过。原始candidate_v1 SHA256={sha(H/"candidate_v1.py")}；v2={sha(H/"candidate_v2.py")}。runtime/audit/common/adapter字节一致，旧冻结与历史输出保持。Python级open审计不是操作系统隔离；哈希不能独立证明预登记时序。\n',
 f'**已披露封存缺口：** 冻结baseline_suite在导入阶段预加载的可选.deps包，有{len(inv["optional_package_files_without_individual_preseal"])}个文件未纳入本轮事前逐文件哈希。每worker保留实际导入路径，执行的项目生产源码已事前封存；这些可选包在计时后补了文件清单/哈希，不能倒称事前封存，也不能证明整个期间已加载内容相同。详见imported_dependency_inventory.json与failures.json。未因此修改生产或追加810之外的计时；交负责人评估这一来源证据限制。\n',
 '一次离线统计因依赖清单异步未写完被提前启动，FileNotFoundError保存在analysis.log；待清单完成后相同源码运行通过，见analysis_completed.log。未生成失败统计汇总，算法/输入/正式结果不改，失效或重跑正式调用0。未把这次交付流程失败计作算法失败。\n',
 '数学结论仅是本模型距离对称及实际连接规则不受first_direction影响；路线等价证据是有限114回归、10夹具、270正式配对；速度是本机同批5重复观测，不保证跨机器/任意规模/硬实时。114均已见，主54共享9基础道路与PPCPP历史，本轮不是新增泛化或最优性证据。\n',
 '固定810调用后停止，不再加图/重复/候选或第二热点，不用最终留出、不运行精确覆盖搜索、不提交推送GitHub。原v0.1约90.34ms历史记录保留，新时间只表明等价实现可更高效；约0.98%路线收益和更多90度转弯仍不足自动确认主算法或创新。后续强基线共同比较由负责人另行决定。\n',
 '## 复核\n\n```powershell\n& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST距离查询等价提速_v0.2_20261020/verify.py\n```\n\n只读核验，不启动规划器或追加正式计时。全部原始结果、任务、日志、读取路径和来源、配对指标/分层、封存/审核包见README及review_packet。\n']
 write('LAST距离查询等价提速结果.md','\n'.join(lines))
 write('README.md','''# LAST距离查询等价提速 v0.2

执行完成，待负责人审核。先读[结果](LAST距离查询等价提速结果.md)和[审核包](review_packet.md)。810正式调用后已停止；未覆盖历史或使用留出。

- protocol.json、预登记.md、input_seal.json、formal_order.json：调用前固定114输入、10夹具、810顺序/共同20秒/停止规则。
- 修改范围与等价依据.md、minimal_candidate.diff、wrapper.diff、candidate_v1.py/v2.py、runtime.py、isolation.py/worker.py：唯一机制改动及必要隔离；source_seal.json是通过门槛后、正式前的封存。
- gate_index.json、gates/：259新门槛完整原输出/外审；cache_gate、path_direction_gate、bfs_internal_deadline、distance_diagnostics：缓存/连接/截止/54几何查询。无精确覆盖调用。
- jobs/、execution/、actual_order.jsonl、completion.json、run.log：全部810新任务、结果、日志与真实顺序；每份输出含输入哈希、唯一读取、模块来源和关键生产源码哈希。
- analysis.json、810调用时间与分段.csv、54状态配对.csv、分层时间配对.csv、完整路线指标.csv：独立逐决策和双指标重核，所有重复、不利候选及分层均保留。
- imported_dependency_inventory.json：计时后补充的完整导入文件清单。90个预加载可选包文件未事前逐文件封存，不能把此清单当成事前证明。failures.json包含此来源限制和一次离线统计启动次序失败，正式失效/重跑0。
- manifest.json：交付内容哈希，含全部原始/源码/输入/日志；只排除manifest自身与会被复核命令输出的verify.log。verify.py只读重审，不调用规划器。

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST距离查询等价提速_v0.2_20261020/verify.py
```
''')
 write('review_packet.md','''# 负责人审核包

状态：执行完成，待负责人审核。请先读LAST距离查询等价提速结果.md、修改范围与等价依据.md、failures.json。不是主算法/创新审批结论；不启动下一轮排名。

|问题|证据|复核边界|
|---|---|---|
|为何可同距同e|冻结model/BFSMetricGeometry、数学无向单位边、坐标tie|这是数学距离理由，不能单独推出实际route同值|
|first_direction是否影响连接|实际UnifiedGeometry.path、path_direction_gate.json、新增同长方向夹具|raw Geometry正反同长路线不同，Unified固定端点实际相同；完整夹具两版本逐坐标核|
|是否只改一行机制|minimal_candidate.diff、runtime等字节hash、wrapper.diff、source_seal.json|版本另改一行；隔离/来源包装在计时外，raw结构和暖入口不变|
|114回归是否真新调用|gates/、gate_index259、228回归原输出及其输入/源码|114V1/V2完整配对；228对旧封存另核，不能把旧结果代替新调用|
|截止是否仍完整入口|9固定注入、bfs_internal_deadline、gates.py封存|P0完成后整体晚到仍拒收；真实BFS内部抛截止。不是硬实时或任意墙钟成功率一致证明|
|缓存和计数|cache_gate.json、distance_diagnostics.json/54几何CSV|P0/F/F-e三对象私有，54独立对象两方向同距/e；计数不是算法速度|
|正式是否810同条件|formal_order、actual_order、jobs/execution810、completion、worker/read_paths|serial新进程/threads1/20秒暖入口含编码，90秒仅看门狗；不拼历史时长|
|270配对和5重复|analysis、semantics.py、run.py、全部trace原件|只排明列时间/version；跨重复另检查固定seed注记，不删任何决策字段；540P0与PPCPP相同|
|路线/覆盖/转弯|完整路线指标.csv、analysis.calls全部双算、audit.py/adapter字节原样|27短27平，原54步收益与90度+44仍在；未运行最优搜索|
|实际速度与负例|810时间CSV、54均值/5次值、分层时间CSV/analysis.strata|全调用均值/中位/P95/max/及时率；两个坏P1与同长全计；有限本机观测|
|封存缺口和流程失败|imported_dependency_inventory.json、failures.json、analysis.log/completed.log|90个预加载可选包文件只后补逐文件hash；首次离线统计依赖未就绪失败，0正式失效/重跑。不得隐藏或倒称事前封存|

一键：包内Python -B -X utf8 本目录/verify.py。只读核验manifest/源输入hash、259门槛外审、810完整重算、270等价/540P0/162稳定、CSV与报告数值和54距离诊断，不发起规划器/新计时。verify.log是运行记录，故不纳入自指manifest；其他交付全部封存。

请区分：数学对称理由；有限完整路线等价实证；有限计时观测。若接受本轮效率修正，仍只是同一LAST实现效率改善，不是新路径策略。90度代价、约0.98%总路线收益和已见开发输入限制继续保留。执行方完成固定批次后停止等待审核，不擅自启动强基线比较。
''')
 print('report, README, review packet, deviations and exact diffs written')
if __name__=='__main__':main()
