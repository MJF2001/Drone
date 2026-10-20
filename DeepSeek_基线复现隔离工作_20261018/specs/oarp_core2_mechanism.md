# OARP_CORE2 适配规格（文献核心适配，不是完整 OARP-Replan）

原文：OARP-Replan，arXiv `2311.17837v2`。本地文本
`sources/literature/OARP-Replan_2311.17837v2.txt`；精读笔记
`sources/reports_referenced/04_OARP-Replan精读_问题与机制.md`。

## 1. 原机制 → 源码位置 → 当前适配

| 原机制 | 源码位置 | 当前适配 | 保留 / 损失 |
|---|---|---|---|
| 把覆盖区域划成平行条带（rank），每格恰属一条 | `oarp_replan/ranks.py::partition` | 方向标注 `{cell: 'H'|'V'}` 后按轴向切连续段 | 保留"条带划分"；方向若由求解器给出，则划分必须与之一致 |
| rank 目标函数：新增/延伸端点越少越好，`min #ranks + changed/(cap+1)` | `ranks.py::_build` 三个变体；`metrics()` 计算 `rank_count / new_rank_count / added_endpoints / extended_endpoints / endpoint_bound` | 冻结调用用 **variant 2**：`changed = 新增端点 + Σβ/2`，β 为"旧端点仍在但方向翻转" | 保留两段式目标；原文公式编号(7)—(36)只作实现依据，本文件不复述为逐式等价 |
| 连续线性规划（LP）+ 整数回退 | `_build(vtype='C')` → SCIP LP；不整则 `vtype='B'` MIP | `rank_replan(..., integer_fallback=True)`，LP 非整则显式整数重解 | 保留；SCIP 由 OUT 内 `.deps/pyscipopt` 提供，版本 6.2.1 |
| rank 数预算来自计算预算 | `budget.py::cap_for_time(frozen runtime_profile)` | 冻结 `runtime_profile.json` 的单调上包络按剩余时间反查 `cap`；`cap=None` 视为预算不足 | **这是工程近似，不是原文常数**：合成格点上 `2m+1` 组标定、1.5×包络 + 10ms，不含几何预处理 |
| 保留旧计划的连续段（path set）与它们的合法连接 | `tour.py::path_sets`、`old_services` | 从旧路线恢复互不相交的直线作业段与段间真实连接；保留段必须整体落在当前 free 内 | 保留；`old_services` 是**我们加的适配器**（P2 不存 rank ID），不是原文初始化 |
| 定向起终点的 GTSP：起点=当前位置，终点=基地 | `tour.py::gtsp_instance`（矩阵 `matrix[end][start]=0` 实现定向终端）、`decode_tour` | 与原文一致的两态（顺/逆向）path set | 保留；`decode_tour` 校验每组恰选一状态、禁用边不被使用、展开长度=代价 |
| GTSP 求解器 | `tour.py::tour_replan` → `glns`（作者维护的 C++ 版 GLNS python 扩展 0.1.0） | 固定 `mode='default'`、`trials=5`、`restarts=3`、给定 `seed` 与 `max_time` | 保留；GLNS 是启发式，**不是最优证书** |
| 小规模精确核对 | `tour.py::exact_gtsp`（Held-Karp，≤12 组） | 只在开发核对里用 | 保留，用于验证解码与代价一致 |

## 2. 单位步数模型带来的改动

原文代价是"加速度/角速度过渡时间"模型，本项目是单位步数。这里统一用自由图 BFS 距离，
转弯不额外计费。影响：原文的"转弯/作业时间"权衡在本适配里不存在，
因此**不能**继承原文的路径长度界或时间结论。

## 3. 输入前提（本轮新发现，必须披露）

`oarp_replan/tour.py::old_services` 在旧剩余路线没有枚举出全部"原待完成格"时抛
`ValueError('old route omitted original pending targets')`。
这不是 bug，而是该适配器的前提：它要靠旧路线的首次访问顺序恢复 rank 序列。

- 由真实执行前缀生成的夹具（`m01`—`m16`）都满足；
- 声明的账本边界状态 `m17_start_pending` 的旧路线只是片段，不满足；
- 适配器报 `status='input_precondition_unmet'`，traceback 保存在 `meta.traceback`，
  **不**伪造替代路线。

## 4. 已知损失清单

1. 不是完整 OARP-Replan：没有原论文的连续事件框架、后台计算和在线重规划循环；
2. 不是 OARP-Original，也不是作者在线化版本；`variant 2` 只是论文目标的一种实现形式；
3. `cap_for_time` 是经验运行时估计，不是最坏时限，也不是实时保证；
4. GLNS 是启发式；`tour_replan` 只保证"展开长度 = 求解器代价"这一自洽性；
5. rank 方向若由 LP 给出，`partition` 后还要回收方向，两者必须一致，否则
   `rank_replan` 会走认证修复分支（`certification_repair`），该分支是**实现补丁**，不在原文里。

## 5. 验收测试覆盖

- `tests/test_contract_and_identity.py`：经适配器与直接调用冻结入口的路线逐格相同；
- `tests/test_edge_cases.py`：空 Q、起点=基地、基地/起点属于 Q、途经基地、暂缓目标、
  不可达目标/基地、资源不足；
- `tests/test_exact_and_connector.py`：与精确最优比较（启发式允许更长）。
