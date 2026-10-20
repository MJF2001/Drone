# C* 历史复现 → 当前模型适配规格

- 适配标签：`cstar_adapt_v0.1_20261018`（`METHOD_ID="CSTAR"`，`METHOD_VERSION="cstar_adapt_v0.1_20261018"`）
- 默认模式：**`mode="public_map"`**（`sensed` 为非默认诊断模式）
- 原实现：`OUT/sources/cstar_historical/cstar_strict/`（`planner.py` / `rcg.py` / `geometry.py`，未知环境、圆盘足迹 `r_c=0.75`、`w=1`）
- 论文：Shen, Wilson, Gupta, *C\*: A Coverage Path Planning Algorithm for Unknown Environments*，arXiv 2505.13782v3，Algorithm 1–4、III-B
- 本移植：`OUT/src/cstar_core/{public_map,rcg,planner}.py` + 信封 `OUT/src/adapters/cstar.py`
- 本文件只记录**实际做到**的内容；没有做到的写在“损失”和“不能声称”里。

---

## 0. 三条硬结论（先看这里）

1. **交付的 C* 路线 = C* 自己的路线 + 固定基地返航，仅此而已。** 没有任何后处理被追加到评分路线，也没有任何补全 TSP 的步数被算到 C* 头上。
2. **C* 是“整片区域扫掠”算法，不是“只访问目标点”算法。** 在当前“只要求目标格”的任务里它会过覆盖（走过大量非目标自由格），所以比精确目标 TSP 长是**任务定义不匹配**的结果，不能据此说 C* 算法差；反过来，如果某个待完成目标它没走到，适配器就如实报 `status="coverage_incomplete"`、`errors=["coverage_omitted:<n>"]` 并保存路线，不删任务、不补路线。
3. **可选的补全 TSP 是另一个方法行**：`completion_tsp=True` 默认**关闭**；打开时方法版本变为 `cstar_adapt_v0.1_20261018+completion`，`final_source` 变为 `completion_tsp_*`，并且永远不进评分行。它是“额外增加的机制”，不是 C*。

另外三处与原文的根本差异必须显式承认：

- **足迹半径为 0**：原文靠半径 `r_c` 的圆盘扫掠“覆盖面积”，本适配改为“到达/经过目标格即完成”，历史连续覆盖审计删除；
- **当前公开地图**：`public_map` 在 k=0 一次观测完整公开地图，采样前沿因此退化为“已公开区域边界环”，不再是未知环境里的渐进展前沿（第 4 节给出具体数字）；
- **固定返航与事件后重启**：历史 C* 在最后一个 waypoint 结束，没有基地返航，也没有旧计划复用。本适配加“四邻接返航”，并把事件时刻视为一次重启而不是维护中的树状态（第 5 节 A4/A7）。

---

## 1. 当前模型 vs 历史 C* 模型

| 维度 | 历史 C* 复现 | 当前任务模型 | 适配后果 |
|---|---|---|---|
| 环境信息 | 未知，只能靠在线感知逐步发现 | 只给“当前已公开地图”（`request.free` 等） | 两种模式：`public_map`（默认，一次性观测）/ `sensed`（同一公开地图经历史射线传感器逐步揭示） |
| 足迹 | 圆盘 `r_c`，扫过的面积算覆盖 | 半径 0，站到/经过目标格才算完成 | 删除连续面积审计；覆盖由调用方按真实账本逐格重算 |
| 运动 | 图上直线段（可对角） | 四邻接、一步一格 | 图度量保留 `1/√2`；执行时每条边用 `GridMetric.path` 展开为四邻接格序列 |
| 任务 | 覆盖整个自由空间 | 完成当前可检的剩余目标 `Q=(P−C)∩F` | 目标访问 = 覆盖；被挡目标 `D` 暂缓、保留 |
| 起点 | `p_0`，未知环境下必是前沿采样点 | 真实当前位置，可能在任何自由格（含内部） | 起点无条件入图并作为 `current_anchor` 保护（A5） |
| 终点 | 最后一个可用 waypoint | 必须返回基地 `base` | 加直接返航段（A4）；历史终止点不同 |
| 历史 | 无旧计划复用 | 有旧路线、旧账本 | 事件时刻视为重启；`covered` 注入、已覆盖格保持可通行；`old_route` 只读记录不复用（A7） |

---

## 2. 八项机制：原文 → 历史源码 → 本移植

所有“位置”均为 `OUT/src` 下路径（历史源码为 `OUT/sources/cstar_historical/cstar_strict/`）。

| # | 机制 | 原文 | 历史源码 | 本移植位置 | 保留 / 损失 |
|---|---|---|---|---|---|
| 1 | 采样前沿 / 节点生成（frontier samples on laps） | III-B2, Def. III.2–III.4 | `rcg.RCG.sample_front`、`geometry.KnownMap.frontier/endpoint`、`planner.CStar.__init__` | `cstar_core/rcg.py:RCG.sample_front`；`cstar_core/public_map.py:PublicMap.frontier/endpoint`；`CStar.__init__` | **保留**：新发现自由格里满足“8 邻域含非自由格”的格成为节点；`w=1` 整数格、以 `p_0` 为锚。**损失**：`public_map` 一次性观测后没有“新发现”，采样只发生一次，且只产出边界环（第 4 节）；`sensed` 模式保留渐进采样。 |
| 2 | RCG 增量扩展：同 lap 竖边、√2 跨 lap 邻域、新节点落在旧长竖边内部时拆分 | III-B3a, Lemma IV.2 | `rcg.RCG.expand/connect` | `cstar_core/rcg.py:RCG.expand/connect` | **保留**：同列按 y 排序重新 zip（先删同列旧边 ⇒ 自动拆分长竖边），再对每个新节点连 `(x±1, y+dy), dy∈{−1,0,1}`。**损失**：环境静态，`public_map` 下扩展只发生一次；对角边可行性用闭方格 supercover（不切角），因此比“四邻接可达”更保守。 |
| 3 | Def. III.8/III.9 必要点分类与剪枝（端点过渡、当前点/执行锚保护） | III-B3b, Def. III.8/III.9, Fig. 7 | `rcg.RCG.essential/prune/validate` | `cstar_core/rcg.py:RCG.essential/prune/validate` | **保留**：未知邻接、lap 端点、端点过渡三选一（端点邻居优先 / 唯一邻居 / 净空最小）；剪非必要点并合并同列两边；保护 `current`、未完成的 link/TSP 锚点；非过渡跨 lap 边剪除。**损失**：全图分类，不声明原文的局部复杂度；`public_map` 下几乎所有点都“邻接未知”，节点剪枝退化，只剩少量锚点被删。 |
| 4 | Algorithm 1 选点：固定 Left → Up → Down → Right，组内按种子随机 | Algorithm 1 | `planner.CStar.select_goal` | `cstar_core/planner.py:CStar.select_goal` | **保留**：四组按固定顺序取第一个非空组，组内 `rng.choice(sorted(group))`；trace 记录 `group/options/chosen/seeded_choice`。**损失**：无。可复现性依靠排序 + 固定种子（测试断言两次运行路线相同）。 |
| 5 | retreat 死端回退：取 RCG 最短路最短的 retreat node | Algorithm 1 line 11–12, Def. III.13 | `planner.CStar.refresh_retreat/register_new_retreats` | 同上 + `cstar_core/planner.py:refresh_retreat` | **保留**：Open 且距已走轨迹 ≤√2 的节点进 retreat；关闭即出；无 Open 邻居时按 `graph.path` 欧氏最短路选最近 retreat。**损失**：历史按“连续轨迹段”刷新，本适配按**每条执行单元步**刷新（一格一格），对角图边贡献两段；语义等价但离散化更细。 |
| 6 | Algorithm 2 状态更新 + 向左切换时距 w 处插入 link node | Algorithm 2, Lemma IV.6 | `rcg.RCG.update_state` | `cstar_core/rcg.py:RCG.update_state` | **保留**：仅当上下两个垂直邻居都 Open 时当前点保持 Open，否则关闭（缺失邻居视为非 Open，取正文/Lemma IV.6 读法）；`goal` 在左侧且当前点已关闭时，对仍 Open 的垂直邻居在 ±1 格（=w）处插入 link；已有样本恰在 w 处则复用并标 `kind="link"`。**损失**：无机制损失；原文未写出“距离 > w”数值条件，沿用历史实现的处理（先试插 ±1，存在则复用）。 |
| 7 | 覆盖空洞检测 + densify + 最近邻 + 2-opt TSP，含三种终点（goal / start / free end） | III-B4d, Def. III.14, Algorithm 3 | `planner.CStar.detect_holes/densify/cover_holes`、`planner.optimize_tsp` | `cstar_core/planner.py:CStar.detect_holes/densify/cover_holes`、`cstar_core/planner.py:optimize_tsp` | **保留**：从当前点相邻 Open 点 flood fill，全分量都不邻接未知才算 hole；同 lap 按 w 加密成 TSP 节点；边权为 RCG A* 最短路；固定起点=当前点；终点三情形 `case=1/2/3`；NN 初解 + 穷尽改进 2-opt。**损失**：`public_map` 下节点几乎都邻接未知，hole 很少成立（14 个可解 C* 运行只有 1 次），`sensed` 下才活跃（另外 3 次）；TSP 是启发式，不保证最优。 |
| 8 | Algorithm 4 外层顺序 | Algorithm 4 | `planner.CStar.run` | `cstar_core/planner.py:CStar.run` | **保留**：感知(仅 sensed) → 采样 → 扩展 → 剪枝 → validate → 快照 → 选点/回退 → Algorithm 2 → 空洞检测 → TSP → 前进。**损失**：加了硬墙钟上限和迭代上限（都不是自然终止）；每轮多写一条 trace 记录。 |

> 机制 7 的具体证据（本适配要求写进数字）：
> - `m03` + `public_map`：hole 节点 `(4,1)`，加密为 `(4,0),(4,1),(5,0)`（TSP 规模 3 节点），`case=1`（终点=goal），NN/2-opt 长度均 2.414，order `[(5,0),(4,1),(4,0)]`，移动 3 格；
> - `m04` + `sensed`：hole `(6,0)`，TSP 3 节点，`case=3`（自由终点），order `[(7,0),(6,0),(6,1)]`；
> - `m11` + `sensed`：hole `(2,3)`，TSP 3 节点，`case=1`，order `[(1,3),(2,3),(2,2)]`；
> - 34 次 fixture 运行共 4 次 hole TSP、7 次 retreat、14 个新建 link node。

---

## 3. 两种模式（适配参数，当前模型未规定）

`run(request, clock=None)` 的参数从 `request.meta` 或 `request.termination.extra` 读取（同键时后者优先）：

| 参数 | 默认 | 含义 |
|---|---|---|
| `mode` | **`"public_map"`** | `"public_map"`：当前公开地图在 k=0 一次观测；`"sensed"`：同一公开地图作为真值，经历史理想栅格射线传感器按半径逐步揭示 |
| `sensor_radius` | `2.0` | 仅 `sensed` 使用；**当前模型没有规定感测半径，这是本适配声明的参数** |
| `holes` | `True` | 是否启用机制 7（Algorithm 3 的洞内 TSP，属于 C* 本身） |
| `max_iterations` | `400` | Algorithm 4 迭代上限（安全上限，不是自然终止） |
| `completion_tsp` | **`False`** | **非默认的额外机制**：把未被 C* 路线访问的待完成目标交给同一套 TSP 机制；打开时方法版本加 `+completion`，`final_source` 用 `completion_tsp_*`，绝不进评分行 |

- `public_map`：`published_observation()` 只观测“自由格=True”和“已发布但被挡目标=False”，其余格保持未知。因此占用图完备、前沿采样退化。
- `sensed`：`PublishedWorld(free=当前公开自由格, published_targets, radius)` 复用历史 `World.observe`（同半径、同 entry-time 分组、遮挡不可穿透）。传感器只读取当前公开地图，**不可能泄漏未来事件**；`mode="sensed"` 只限制 C* 图能看到什么，连接器与返航仍使用当前公开地图（这就是当前模型的信息水平）。
- 时间信息：`sensed` 下 `navigate` 每走一格感知一次（间距 ≤ w/2）；图与连接器只用当时已揭示的自由格，避免“用以后才知道的格”。

---

## 4. 公开地图退化：具体数字（不粉饰）

### 4.1 采样只得到边界环

`public_map` 下没有任何格“邻接未知”（除了公开区域边界和未公开的障碍旁边），所以 `frontier()` 只在边界环与障碍环上成立。14 个可解且进入 C* 的 fixture（完整表见 `artifacts/cstar_trace/degeneration_public_map.json`）：

| 例子 | 公开自由格 | k=0 采样点 | 末端节点 | 采样到的内部格 | 从未被采样的自由格 |
|---|---|---|---|---|---|
| `m01_pure_obstacle` | 23 | 21 | 17 | 0 | 6 |
| `m05_no_change` | 20 | 14 | 14 | 0 | 6 |
| `m03_corner_extension_and_obstacle` | 38 | 30 | 23 | 0 | 15 |
| `m11_covered_corridor_blocks` | 33 | 28 | 23 | 0 | 10 |
| 9×9 深部目标探针 | 81 | 32（=边界环） | 32 | 0 | 49 |

14 次运行全部 `sampled_interior_cells=0`、`boundary_ring_only=True`，**RCG 全部连通**（P3 成立，`validate` 不抛错）。

### 4.2 但 RCG 仍然连通，而且退化成“整列扫掠”（这是任务定义不匹配的来源）

边界环上的节点仍然是 lap 端点；Def. III.8 保留每条 lap 的两个端点，扩展阶段把同列所有节点重新 zip，于是每个内部列得到**一条贯穿该列的长竖边**（如 9×9 的 `(4,0)–(4,8)`，权 8）。执行时 `GridMetric.path` 把这条长边展开为整列 8 个格，于是路线变成逐列往返的 boustrophedon，而不是前沿驱动的探索。

9×9 深部目标探针（目标 `(4,4)`，内部格 49 个从未被采样）：

- 采样 32 点 → 剪枝后 32 节点 / 39 边（**这就是 public_map 下的实际 TSP/图规模**：没有洞内 TSP，只有整图扫掠）；
- 31 个 Algorithm 4 迭代（30 次选点 + 最后一次 graph_exhausted），C* 执行 80 格，返航 8 格，总计 88 格；
- 目标 `(4,4)` 被第 4 列的长竖边扫过，**覆盖完整**，`completion_steps=0`。

**结论（必须原样引用）**：交付的 C* 路线是“对 RCG 采样点所覆盖整片区域的扫掠”，在“只要求目标格”的任务下必然过覆盖；同样的目标任务，精确目标 TSP 可以短得多。这是**任务定义差异**，不是 C* 质量差的证据。本适配不因此给 C* 加目标优化后处理；可比性应放到下一轮统一协议的“整片区域覆盖”口径下讨论。

### 4.3 真正断开的情形：公开自由格里的“口袋”

若某个自由格被两格厚的障碍环包住（离最近其他前沿采样点 > √2），它会被采样成一个孤立节点：既不在任何有效 lap 上，也没有同列/跨列邻居。

9×9、中心 `(4,4)` 留空、其 Chebyshev 距离 ≤2 的 24 格全部被挡（探针 `free_pocket_probe`，目标 `(1,1),(7,7),(1,7)`）：

- 自由格 57，采样 57，剪枝后 57 节点 / 87 边，**连通分量 = [56, 1]**（1 = 孤立口袋 `(4,4)`）；
- `RCG.validate` 抛 `RCGCut`（历史不变式），外层循环在 iteration 0 中止：`cstar_steps=0`；
- 评分路线 = C* 路线（仅 `[current]`）+ 直接返航 8 格；`status="coverage_incomplete"`，`errors=["coverage_omitted:3", "cstar_rcg_disconnected:..."]`；独立审计 `uncovered_count=3`；
- **没有**补全 TSP 进入这条路线。若显式打开 `completion_tsp=True`（另一个方法行），同一探针会用 3 个目标的 TSP 在 10 步内补完并返回基地，状态改为 `finished`、版本 `...+completion`、`final_source="completion_tsp_after_rcg_failure"`；该结果**只作为额外机制记录**，不参与 C* 评分。

这就是“图断开 / 退化成一个 TSP”的证据：**不是伪造连通，也不是把补全算成 C***，而是如实报 `coverage_incomplete` 并保留路线；补全只在明确命名的变体里出现。

---

## 5. 适配清单（每项都有损失）

| 编号 | 适配 | 损失 / 保留 |
|---|---|---|
| A1 | `mode="public_map"`（默认）：k=0 一次观测完整公开地图 | 保留采样/扩展/剪枝代码结构；**损失**：没有“新发现”，采样只发生一次，前沿退化为边界环（第 4 节数字）。 |
| A2 | `mode="sensed"`（非默认）：公开地图经历史射线传感器按 `sensor_radius` 揭示 | 保留渐进采样与逐格感知；**损失**：传感器真值是“已公开地图”，不能发现未来信息；半径 `2.0` 是适配参数，当前模型无此规定；非自由格在半径内一律视为遮挡（建模选择）。 |
| A3 | 足迹半径 0：删除历史连续圆盘覆盖审计，覆盖=访问；**评分路线 = C* 路线 + 固定返航**；未访问的待完成目标 → `coverage_incomplete` + `coverage_omitted:<n>`，不补路线 | **损失**：C* 不再自证“面积覆盖”，历史 `coverage_audit`/certified bound 全部不适用；C* 的整片扫掠在目标口径下过覆盖。**保留**：不删任务、不虚报覆盖、不把额外机制算成 C*。 |
| A3b | **可选**、非默认的 `completion_tsp=True`：用 Algorithm 3 的 TSP 机制（固定起点=最后 C* 格、固定终点=base）补完未被访问的目标 | **这是新增机制，不是 C***：默认关闭；版本后缀 `+completion`；`final_source=completion_tsp_*`；`fallback_used=True`；`meta.completion_tsp.attribution="NOT part of the C* result"`；任何评分行都不得使用。损失：额外求解时间与额外候选，不能归功于原算法。 |
| A4 | 基地返航：路线末尾用 `GridMetric.path` 直接回 base（C* 之后固定一段） | **损失**：历史 C* 在最后一个 waypoint 终止，没有返航项；返航会加步数，可能触发资源超限（`m12`：34 步 > 3）。 |
| A5 | 起点采样锚：`p_0` 无条件入图；`public_map` 下它可能位于内部，标 `kind="start"`，由 `current_anchor` 保护 | **损失**：这是原文前沿规则不会产生的内部采样点；没有它，`public_map` 下起点孤立、P3 在 iteration 0 就失败。**保留**：仍走同一套同列/跨列扩展，不额外造边。 |
| A6 | 四邻接执行：图度量保留论文的 `1/√2` lap 几何，执行时每条 RCG 边用 `GridMetric.path` 展开 | **保留**：对角边在图上仍是 √2；`feasible` 用闭方格 supercover 且不切角，因此每条对角边的两个侧格都自由 ⇒ 一定存在合法四邻接实现（测试逐边断言）。**损失**：执行步数大于图上欧氏代价；路线长度不能当作 C* 目标值。 |
| A7 | 历史初始化=重启：事件时刻从“空图 + 真实当前位置 + 真实账本”重建；`covered` 注入，已覆盖格保持可通行；`old_route` 只记录不复用 | **损失**：没有旧计划复用，可能重复已走过的路；历史 C* 本来就无此机制，本适配不假装有。**保留**：绝不重置历史、绝不把已覆盖格变障碍、暂缓目标只留账。 |
| A8 | 终止与状态信封：自然终止=`graph_exhausted`；硬墙钟上限 → `termination={"natural": False, "reason": "wall_clock_cap_triggered"}`；迭代上限 → `iteration_cap_triggered`；`rcg_disconnected`/`invariant_failure` 也非自然 | **损失**：上限是新增安全阀，不是原算法终止规则；次数与秒数写进 `termination`/`meta`。 |

### 5.1 路线合法性

- 唯一连接器是 `common_geometry.GridMetric`：`path(a,b)` 只走四邻接，`path(b,a)` 就是反向，路径几何唯一。
- `CStar.navigate` 对每条图边先断言 `b ∈ edges[a]` 且 `map.feasible(a,b)`，再用连接器展开；`sensed` 下连接器建在“当时已揭示的自由格”上，`public_map` 下建在公开自由格上，两者都是公开地图子集。
- 测试逐边断言：图边权 = 欧氏距离；每条边的连接器步数 = 曼哈顿距离；因此对角边必然 2 步、长竖边必然 |Δy| 步。

---

## 6. 结果信封语义

| 字段 | 本适配取值 |
|---|---|
| `status` | `environment_infeasible` / `finished` / `coverage_incomplete` / `resource_exceeded`（优先级：覆盖不全 > 资源超限 > 完成） |
| `reason` | `cstar_<cstar_status>`，可带 `+base_return` / `+coverage_incomplete`；仅在打开额外变体时带 `+completion_tsp`；空待完成时 `empty_pending_direct_return`；环境不可行时直接是环境码 |
| `route` | 从 `request.current` 到 `request.base` 的逐格四邻接路线：**C* 段 + 返航段**；默认不含任何补全段 |
| `resource_check` | `{limit, used, ok, source="recomputed_from_route", cstar_steps, completion_steps=0, base_return_steps}`，始终填写 |
| `termination` | 自然：`{"natural": True, "reason": "graph_exhausted", "iterations": n}`；墙钟：`wall_clock_cap_triggered`；迭代上限：`iteration_cap_triggered`；图断开/不变式失败也非自然 |
| `fallback_used` / `fallback_steps` | 默认恒为 `False` / `None`（评分路线没有保底、没有后处理）；只有显式打开 `completion_tsp` 且补全真的跑了时才为 `True`，步数只计补全段 |
| `best_candidate_source` | `cstar_rcg`（C* 有位移）/ `cstar_start_only` / `direct_return` |
| `final_source` | 默认：`cstar_rcg`、`cstar_rcg+base_return`、`cstar_start_only[+base_return]`；额外变体：`cstar_rcg+completion_tsp`、`completion_tsp_after_rcg_failure` |
| `method_version` | 默认 `cstar_adapt_v0.1_20261018`；打开额外变体时 `cstar_adapt_v0.1_20261018+completion` |
| `errors` | 环境码、`coverage_omitted:<n>`、资源超限、C* 异常摘要；**不隐瞒** |
| `meta` | `mode`、选项、`cstar`（状态/迭代/节点边数/采样数/link/retreat/TSP 事件/连通分量/节点表）、`public_map`（采样证据）、`coverage`、`completion_tsp`（默认 `enabled=False, steps=0`）、`route` 分段、逐迭代 `trace` |

**墙钟上限的语义**：上限终止 C* 搜索；评分路线仍是“已走 C* 段 + 返航”。测试用 `time_limit_seconds=1e-9` 强制触发：`cstar_steps=0`、`completion_steps=0`、返航 1 段、`status="coverage_incomplete"`、`errors=["coverage_omitted:<|Q|>"]`，`termination.natural=False`。

**`coverage_incomplete`**：只要 `pending − route` 非空就设该状态并写 `errors=["coverage_omitted:<n>"]`；微图上只在“RCG 断开 / 墙钟截断”时出现——这正是当前模型下 C* 的真实边界，不作为算法改进的借口。

---

## 7. 微图验证结果

命令见第 8 节。17 个 fixture × 2 模式 = 34 次适配器运行，另有 34 次同种子重复运行：

| 项目 | 结果 |
|---|---|
| fixture 数 | 17 |
| 运行数 | 34（+34 次确定性重复） |
| `finished` | 28（含 `m06_empty_pending` 2 次“空待完成直接返航”） |
| `resource_exceeded` | 2（`m12_resource_tight`，34 步 > 3，路线仍记录且覆盖完整） |
| `environment_infeasible` | 4（`m14` base 不可达、`m15` 目标被封死，两种模式各一次；无路线） |
| `coverage_incomplete`（fixture） | 0；专门探针（RCG 断开、墙钟截断）各 1 次，证明该状态可达且 `coverage_omitted:<n>` 正确 |
| 路线合法性 | 30 次可解运行全部：起点=current、终点=base、无碰撞、无斜跳、覆盖声明无凭空 |
| 覆盖完整性（独立审计） | 30/30 可解运行 `coverage_complete=True`（含 `m12`） |
| 独立性 | 适配器从不调用 `audit_independent`；测试对每条路线重新审计 |
| 暂缓集合 | 34 次运行均未被访问、未被删除；`m13` 的暂缓目标仍在账上 |
| 确定性 | 34/34 两次同种子运行路线与状态完全一致 |
| 保底/后处理 | 34/34 评分运行 `fallback_used=False`、`completion_steps=0` |
| RCG 连通性 | 30/30 可解 fixture 运行 `rcg_connected=True`；空洞 TSP 4 次、retreat 7 次、link 14 个 |
| 额外变体（不进评分） | 墙钟截断探针打开 `completion_tsp=True`：3 目标、补全 8 步、状态 `finished`、版本 `+completion`、审计 `valid=True` |

**必须说明**：微图上 C* 路线本身就覆盖了全部待完成目标（长 lap 边整列扫掠），所以默认评分路线里没有补全段、没有保底。补全只在“图断开 / 墙钟截断”的显式变体里出现；把它写成 C* 的贡献会是不诚实的。

---

## 8. 复现命令

```powershell
$OUT="D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018"
$py="D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe"
$env:PYTHONDONTWRITEBYTECODE="1"; $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"
cd $OUT\src
& $py -B -X utf8 -m unittest discover -s "$OUT\tests" -p "test_cstar*.py" -v
```

测试会（重新）写：

- `artifacts/cstar_trace/m01_pure_obstacle__public_map.json`
- `artifacts/cstar_trace/m01_pure_obstacle__sensed.json`
- `artifacts/cstar_trace/m03_corner_extension_and_obstacle__public_map.json`
- `artifacts/cstar_trace/m04_two_events__sensed.json`
- `artifacts/cstar_trace/degeneration_public_map.json`

每个 trace 的 `iterations[]` 是一次 Algorithm 4 迭代：节点/边计数、选中的 goal、由哪一组（left/up/down/right/retreat/exhausted）触发、组内候选与被种子选中的点、是否 retreat、是否 TSP 空洞、Algorithm 2 结果、执行模式与步数，并附当轮完整节点/边快照；`how_to_read` 字段给出逐键说明；`completion_tsp` 字段明确记录默认关闭。

---

## 9. 不能声称的内容

1. **不是历史 C* 的逐行等价**：模式、执行、覆盖口径、返航、历史初始化都变了；`METHOD_VERSION` 已标注 `cstar_adapt_v0.1`。
2. **没有复现论文的连续面积覆盖定理**：足迹半径 0 下，论文的 `r_c` 覆盖、certified lower bound、`w ≤ 2r_c` 讨论全部不适用；这里只证明“逐格访问 + 四邻接合法 + 独立审计”。
3. **没有性能结论**：不比较 C* 与 P2/ε*，不声称步数更短或计算更快；微图只验证机制与正确性。C* 的整片扫掠在目标口径下过覆盖，长路线是任务定义不匹配，不能当作算法优劣证据。
4. **没有恢复 P4–P6 的最优/稀疏/平面性证明**：只保留构造规则与 `validate` 的连通/对称/可行性检查。
5. **`public_map` 模式不是未知环境算法**：它是“当前公开地图”的一次性离线采样，前沿退化已量化；只有 `sensed` 模式保留渐进发现。
6. **TSP 是启发式**：NN + 2-opt，不保证最优；三端点情形只证明语义正确。
7. **补全 TSP 不是 C***：默认关闭、版本另标、`final_source` 另标，任何评分行都不使用；不能把它带来的覆盖或步数记在原算法名下。
