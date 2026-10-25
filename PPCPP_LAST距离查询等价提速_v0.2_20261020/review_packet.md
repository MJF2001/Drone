# 负责人审核包

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
