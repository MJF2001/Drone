# 方法身份与原文对应表

分类（用户要求必须准确，不得混称）：

| method_id | 分类 | 原文 | 版本 | 源码（OUT 内路径） |
|---|---|---|---|---|
| `P2_MULTI` | 自建工程基线 | 无。扫描/最近邻初值 + 2-opt + 多起点组合，项目内增强 | `v2_20261012` | `sources/reference_tree/.../frozen_baselines/v2_20261012/source/{p2_search_audit,planners,unified_geometry,bfs_metric_geometry}.py` |
| `TREE_MST` | 自建工程基线 | 无。**不是** TRACE、**不是** STC/FS-STC、**不是** C* | `v2_20261012` | 同目录 `unified_candidates.py`（`metric_tree` / `preorder` / `solve_candidate`） |
| `OARP_CORE2` | 文献核心适配 | OARP-Replan（arXiv 2311.17837v2）场景 2 | `v2_20261012` | 同目录 `oarp_replan/{ranks,tour,budget}.py`、`baseline_suite.py` |
| `PPCPP_CORE4` | 文献核心适配 | PPCPP（作者机构接受稿）四邻接核心 | `v0.1_20261014` | `sources/reference_tree/.../candidate_baselines/PPCPP_CORE4/v0.1_20261014/` |
| `EPSILON_STAR` | 文献核心适配 | ε*（Song & Gupta 作者原稿） | `epsilon_star_core_v0.1_20261018` | 本轮新增 `src/epsilon_core/`、`src/adapters/epsilon_star.py` |
| `CSTAR` | 历史复现的当前模型适配 | C*（arXiv 2505.13782v3） | `cstar_adapt_v0.1_20261018` | 历史复现 `sources/cstar_historical/`；适配见 `src/cstar_core/`、`src/adapters/cstar.py` |

四个已有方法这次**没有重新实现**：`sources/reference_tree` 是逐字节复制，
`tests/test_contract_and_identity.py` 用各自 manifest 的 SHA256 复核，并逐案例比较
"经适配器调用"与"直接调用冻结入口"的状态与逐格路线完全一致。

---

## 1. P2_MULTI（自建工程基线，代码级说明）

`baseline_suite.solve(..., 'P2_MULTI', ...)` → `p2_search_audit.solve(s, budget, 'multi', seed)`。

### 阶段（真实插桩，`events` 记录 start/end）

| 阶段 | 代码 | 内容 |
|---|---|---|
| `fallback` | `p2_search_audit.solve.fallback` | 先试旧剩余路线；再用"旧顺序里仍能承担未完成覆盖的访问 + 蛇形补齐"生成共同保底，两者都走 `offer` |
| `{H,V}_generate` | `planners.candidates` | 按 `2r+1` 足迹间距取规则采样点，按行/列蛇形排序；再对仍未覆盖的目标做显式贪心修补（按"新增覆盖数、到锚点曼哈顿距离、坐标"排序） |
| `{H,V}_raw` | `offer(g.expand(points))` | 直接把点序交给 `Geometry.expand`，途中已覆盖的访问被跳过，最后接返航 |
| `{H,V}_nearest` | `planners.nearest` | 从当前位置的最邻近邻顺序；`expand` 同上 |
| `{H,V}_NN_raw` | `offer` | 最近邻原始顺序的候选 |
| `{H,V}_scan_opt` / `{H,V}_NN_opt` | `p2_search_audit.opt` | 固定起点/终点的 2-opt，最多 8 轮；每轮取全局最优改进对；记录 `passes/swaps/termination`，终止原因是 `no_improving_2opt_move` 或 `pass_limit` |
| `*_expand` | `offer` | 优化后的顺序展开后提交 |
| `core_finished` | — | 4 个核心候选（H/V × scan/NN）全部提交完毕 |
| `*_deep` | `opt(p, 120, ...)` | 每个核心顺序再跑最多 120 轮 2-opt |
| `reverse_H/reverse_V`、`perturb_H/V`×4、`shuffle_0/1` | `variant == 'multi'` 分支 | 多起点：两个反向扫描序；每轴 4 次随机区间反转；2 次 `sorted(demand)` 随机洗牌 |
| `*_raw` / `*_opt`（多起点） | `offer` + `opt(p,32,...)` | 每个多起点初值先提交原始序，再最多 32 轮 2-opt 后提交 |

### 候选保留与代价

- `offer` 只接受**完整合法**路线：起点=当前位置、终点=基地、每格在 `views` 内、逐步四邻接、
  覆盖全部 `targets`、不超过 `distance_budget`；保留**最短**的一条并记录来源标签。
- 距离/路径来自 `UnifiedGeometry`（BFS 批量精确距离 + 同一对端点只生成一种最短路径几何）。
  2-opt 只用 `distance`，不展开路径；`expand` 才对每个相邻访问调用 `path`，
  并对整条路线逐格重算覆盖——这是"完整展开"的主要开销。
- 终止：墙钟软截止（`DeadlineExceeded`）+ 每段 2-opt 的轮数上限。
  截止前已有合法候选则 `planned_at_timeout`，否则 `timeout`。

### 版本关系（必须分清）

- 冻结 `v2_20261012` 的 `P2_MULTI` = 上表的 `variant='multi'`，即**含** 120 轮加深与多起点。
- 第 71—74 轮里的 `SEED / PLUS1 / PLUS2 / ALL` 是**同一个 P2 引擎**在不同"重排范围/责任集合"
  下的配置，不是四种不同覆盖算法；`ALL` 不等于另一个求解器。
- 因此本轮统一接口里只有 **一个** `P2_MULTI`；范围差异属于下一轮协议，
  不混算成多个方法。

### 不能声称的

- 不是 OARP/TRACE/C* 的复现；不是论文创新；
- 多起点数量、120 轮、32 轮这些数字是工程选择，不构成"方法足够强"的证据；
- 2-opt 自然收敛不等于全局最优。

---

## 2. TREE_MST（自建工程基线）

`unified_candidates.solve_candidate(s, 'TREE_MST', ...)`：

1. 顶点 = 当前未覆盖目标 ∪ {当前位置}；边权 = 自由图上的精确 BFS 距离；
2. Prim 生长最小生成树（`metric_tree`）；
3. 从当前位置做先序遍历，正序与反序各一条（`preorder(children, root, reverse)`）；
4. 各提交原始序（`MST_preorder_0/1`），再做 `planners.two_opt(..., 8 轮)` 提交
   （`MST_preorder_2opt`）；
5. 外加快照旧路线（`common_old_suffix`）与共同贪心保底（`common_GD_adapter`）。

损失/边界：

- 树是**目标任务级**的度量最小生成树，不是栅格生成树，也没有沿树侧巡游的细格行走；
- 没有 TRACE 的分解树维护、更新规则和局部覆盖；没有 STC 的起点回路与细格树巡游；
- `preorder` 是二叉前序（按边权排序），不是 STC 的逆时针递归；
- 因此 `TREE_MST` 只能作为"树初始化 + 2-opt"的工程参照。

---

## 3. 记录在案的引擎异常（本轮新发现）

| 现象 | 证据 | 处理 |
|---|---|---|
| 冻结 P2 / OARP / TREE 在资源上限明显不足时会返回 `status='finished'` 且 `route=()` | 微图 `m12_resource_tight`（`remaining_resource=3`） | 适配器把该状态降级为 `no_legal_route_within_resource`，引擎原状态保留在 `meta.engine_status`；**不改冻结源码** |
| `OARP_CORE2` 的旧路线适配器要求旧剩余路线枚举出全部原待完成格，否则 `old_services` 抛 `ValueError` | 微图 `m17_start_pending`（声明的账本边界状态，旧路线是片段） | 适配器捕获并报 `input_precondition_unmet`，traceback 入 `meta`；不伪造替代路线 |
| `TREE_MST` 返回 `status='planned'`（不是 `finished`） | 全部微图 | 原样透传，不做归一化 |

`p2_search_audit` 的 `events` 直接把阶段时刻写在返回值顶层（没有 `detail` 键），
`OARP_CORE2`/`PPCPP_CORE4` 嵌在 `detail` 里；适配器同时支持两种形状，否则 P2 的阶段计时会被静默丢掉。
