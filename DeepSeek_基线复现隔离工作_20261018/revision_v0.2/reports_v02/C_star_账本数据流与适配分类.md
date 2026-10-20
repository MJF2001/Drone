# C* 的账本数据流与适配分类（R4 修订）

日期：2026-10-18。对应主会话意见 **R4**。
本文件只做语义与数据流修订；按意见要求，本轮**没有**加强 C* 的实现。

---

## 1. 结论先行

v0.1 把 C* 的版本写成 `cstar_adapt_v0.1_20261018`，并说"历史注入"。**这一定性不准确。**

实际数据流是：真实覆盖账本 `C` 只到达**外层信封**（空任务判定、独立审计、可选的
`completion_tsp`），**没有进入核心规划状态**。核心的构造签名是

```python
CStar(start=..., known=..., sensor=..., seed=..., holes=...,
      deadline=..., wall_clock=...)
```

其中**没有任何 `covered` 参数**。因此核心无从知道哪些目标已经完成，
它的行为等价于"从当前位置重新扫一遍当前公开的整片自由区"。

v0.2 因此改名并改分类：

| 项 | v0.1 | v0.2 |
|---|---|---|
| 版本号 | `cstar_adapt_v0.1_20261018` | `cstar_restart_diag_v0.2_20261018` |
| 分类 | `historical_reproduction_adaptation` | `restart_diagnostic_ledger_not_in_core` |
| 描述 | "历史未知环境复现移植到当前模型" | "**重启诊断版**：账本不进入核心规划状态，核心重新扫全 free；不是剩余任务核心适配" |

机器可读分类写在 `registry.METHODS["CSTAR"]["adaptation_class"]`，并逐次写进结果的
`meta.history`（见 §2）。

---

## 2. 完整数据流：账本 `C` 到底流到了哪里

| 环节 | 是否使用 `request.covered` | 具体作用 | 代码位置 |
|---|---|---|---|
| 空任务判定 | **是** | `pending = (P−C)∩F` 为空时直接返航 | `adapters/cstar.py::run` |
| 环境可达性 | **是**（间接） | 只检查 `pending` 的可达性 | `problem.reachability` |
| 公开观测构造 | **否** | `published_observation(free, published_targets)` 只传自由格与发布目标 | `cstar_core/public_map.py` |
| RCG 节点生成（采样前沿） | **否** | 只看 `PublicMap.free` 与"邻接未知" | `cstar_core/rcg.py::sample_front` |
| 必要点分类与剪枝 | **否** | 只看节点状态、lap 端点、未知邻接 | `rcg.py::essential/prune` |
| Algorithm 1 选点 | **否** | 只看 `is_open` 与固定顺序 | `cstar_core/planner.py::select_goal` |
| Algorithm 2 状态更新 | **否** | 只看上下垂直邻居的 Open 状态 | `rcg.py::update_state` |
| 覆盖空洞 TSP | **否** | 只看 Open 节点与未知邻接 | `planner.py::detect_holes/cover_holes` |
| 终止 | **否** | `graph_exhausted` / 迭代上限 / 墙钟 | `planner.py::run` |
| 返航 | **否** | 从最后位置到基地 | `adapters/cstar.py` |
| 独立审计 | **是** | `covered ∪ 路线经过 ∩ P`，与 `pending` 比较 | `audit_independent.audit_route` |
| 可选 `completion_tsp`（默认关） | **是** | 只对"路线没经过的 pending"补一段 TSP | `adapters/cstar.py` |

每次运行的 `meta.history` 会把这张表压缩成机器可读形式：

```json
{"ledger_cells": 12,
 "reaches_core_planning_state": false,
 "used_in_envelope": ["empty_task_test", "independent_audit", "optional_completion_tsp"],
 "not_used_in_core": ["RCG sampling", "pruning / essential classification",
                      "Algorithm 1 waypoint choice", "Algorithm 2 state update",
                      "Algorithm 3 hole TSP"],
 "classification": "restart_diagnostic_ledger_not_in_core"}
```

---

## 3. 一个能保留原机制的历史适配方案（本轮不实现）

要点：**不要把账本当障碍，也不要删掉仍然合法的通道**。历史只改变"谁还需要作业"，
不改变"哪里能飞"。

### 3.1 注入点：节点级任务标记，而不是删除单元格

1. k=0 时按原规则做一次完整观测与采样，得到 RCG。
2. 对每个节点 `p`：若 `p ∈ C`（已是完成目标），把它标成新的节点属性
   `tasked=True`，但**状态仍是 `Op`**。
3. `select_goal` 的候选过滤从 `is_open(q)` 改为 `is_open(q) and not tasked(q)`：
   Algorithm 1 的"左→上→下→右"四组顺序**完全不变**，只是不再把已完成的格当作业对象。
4. `prune` 里把 `tasked` 节点加入保护集合（与现有 `link` / `tsp` 锚点同等待遇）：
   这样即使它不再是作业对象，也**不会被剪掉**，仍然可以作为移动通道。
5. Algorithm 2 的状态更新、link 插入逻辑不动。

这样保留的机制：前沿采样、RCG 扩展、必要点分类、Algorithm 1 顺序、retreat、空洞 TSP。
新增的机制只有一个"节点已完成标记"，必须写成适配，而不是说成原算法自带。

### 3.2 终止条件

原文以 `D_L = ∅`（没有正势粗格）作为完成信号。加入 `tasked` 之后，完成信号应改为
"`pending ⊆ covered` 且没有未完成节点可被选中"，而不是 `graph_exhausted`。
两者要分别记录：`graph_exhausted` 是图的状态，"任务完成"是账本的状态；不一致时以账本为准，
并把图状态一并写进结果（这正是 R5 要求的"状态与语义一致"）。

### 3.3 需要重新测量的东西

实现上述方案后，至少重测三件事，且**不能沿用本轮数字**：

1. **过覆盖比**：扫全区域 vs 只扫剩余任务，差多少；
2. **采样退化**：`sampled_interior_cells = 0` 是否仍然成立（大概率仍成立，因为退化来自
   "整图公开"，不是来自账本）；
3. **RCG 连通性**：`tasked` 节点被保护后，被障碍环围住的"口袋"是否仍会断连。

### 3.4 做不到的部分（要提前说清）

- C* 原文没有"逐格任务账本"这个概念：作业对象是 RCG 节点，不是单元格。
  所以任何账本注入都是**新增机制**，原文的完备性/长度论证不覆盖它；
- 如果坚持"只覆盖目标格"的任务口径，C* 的整区域扫掠本质上就是过覆盖，
  再怎么注入历史也无法把它变成目标导向算法。

---

## 4. 关于"2.60× 最优"的重新表述（待归因）

v0.1 报告写过"C* 步数/最优中位 2.60×、最大 5.00×"。这个数字本身是真实的
（`reports/微图结果表.md`），但**归因必须收回**：

> 该比值只对**当前这一版适配、当前 17 个微图、当前"只要求目标格"的任务口径**成立。
> 它**不能**证明原 C* 差，也**不能**证明全部差距都来自任务口径。

已知的、尚未分离的候选原因至少四条：

1. **任务口径**：C* 要扫整个 allowed 区，我们只算目标格；
2. **采样退化**：整图公开后只采到边界环（`sampled_interior_cells = 0`，14/14 微图）；
3. **历史未注入**：账本不进核心（§1），核心从当前位置重新扫全 free；
4. **适配编码**：`public_map` 观测如何界定边界、`w=1` 的对齐相位、四邻接展开对角图边，
   都可能影响步数。

要归因，必须做**受控对照**：分别固定 1—4，逐项测量。本轮没有做，也不该用现有数字下结论。

---

## 5. 关于补漏代码的准确表述

v0.1 报告写过"适配器没有给 C* 加任何补漏 TSP 后处理"。这句话**不准确**：
代码里确实有一个 `completion_tsp` 分支。

准确的表述是：

> 默认（`completion_tsp=False`）的**评分路线不含补漏**：路线 = C* 自己的路线 + 固定返航。
> 存在一个**非默认**的可选分支 `completion_tsp=True`，打开时版本号带 `+completion`、
> `final_source` 标为 `completion_tsp_*`、`fallback_used=True`、`meta.completion_tsp.attribution`
> 明确写 "NOT part of the C* result"，并且**从不进入评分行**。

v0.2 的 102 次正式运行中，`completion_steps` 全为 0，`fallback_used` 全为 False。
按意见要求，**下一版不再扩展这个分支**。
