# PPCPP_CORE4 适配规格（文献核心适配，不是完整 PPCPP）

原文：PPCPP 作者机构接受稿，本地副本
`sources/literature/文献基线核查_20261014/候选原文补查/PPCPP_author_manuscript.pdf`；
核查记录见 `sources/reports_referenced/61_对比基线总表与四种经典方法适配成本_20261016.md`
与 `47/49/50` 号报告（见 `sources/reports_referenced` 的入口文件）。

版本：`PPCPP_CORE4 v0.1_20261014`，源码
`sources/reference_tree/.../candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py`，
权重 `profile.json` 里 `omega_s=2.0`、`omega_b=0.5`。

## 1. 原机制 → 源码位置 → 当前适配

| 原机制 | 源码位置 | 当前适配 | 保留 / 损失 |
|---|---|---|---|
| 三奖励驱动的邻域选择（距离/直线/边界） | `reward_options()` | 四邻接真实相邻的未完成格；`distance_reward` 为到 predator 点的归一化距离，`straight_reward` 为 `(dot+1)/2`，`boundary_reward=(4-n)/4`；`score = r_d + ω_s·r_s + ω_b·r_b` | 保留三项；**归一化与 predator 位置是我们的实现约定**，原文的具体标度需对照正文 |
| 权重由离线网格选择 | `profile.json`，`selection_objective` 记录了排序目标 | 16 权重 × 12 开发状态一次性网格选择，选定 (2.0, 0.5) | 保留"离线选权"这一步；**网格选出的权重不是全局最优** |
| 选择 `argmax score`，平局按坐标 | `choose_neighbor()` | 保留 | 保留 |
| 死端恢复：局部无未完成邻居时跳到最近的未完成目标 | `core_route()` 的 `else` 分支 | 用共同几何的精确 BFS 距离选目标，并按 **实际经过的逐格** 记账（`credit_segment`） | 保留"死端恢复"；原文的恢复路径规则需对照正文，这里用统一连接器 |
| 实际经过即采集 | `credit_segment()` | 每一格经过都要计入 pending | 与本项目模型一致，**这是适配**，原文的作业/移动时序不同 |
| 返回基地 | `core_route()` 末尾 `g.path(route[-1], s.base)` | 保留 | 适配：原文以覆盖结束为终止 |
| 共同保底 | `common_fallback()`（旧路线 / 共同贪心） | 与冻结三基线同一套保底，先提交、只在更长时被替换 | 保留，且 `fallback_selected` 单独上报 |

## 2. 冻结参数与不可外推项

- `predator_for(targets, base)`：在目标包围盒左/右侧一格，取决于基地偏向哪边。
  原文 predator 的定义与移动规则需逐式核对，本文件不声称等价。
- 权重只在一批开发状态上选过一次；`PPCPP_CORE4` 参与过那批状态的调参，
  因此**任何用同一批状态做的比较都不是独立测试**。
- `seed_used_for_decisions = False`：核心路线是确定性的，种子只影响引擎记录的种子字段。
  小改动会让"重复运行波动"这一列对它恒为 0，报告里必须说明。

## 3. 状态与终止

| status | 触发 |
|---|---|
| `finished` | 核心路线完整构造并在截止前通过 `single_cell_audit` |
| `deadline` | 软截止；若核心未通过校验则 `core_status='not_validated_before_deadline'` |
| `no_legal_candidate` | 保底与核心都没有合法完整路线 |
| `planning_failure` | `NoPath` |
| `environment_infeasible` | 共同几何 `precheck()` 判定不可行 |

核心与保底分别审计：`core_independent_audit` 与 `independent_audit` 都不计入求解秒数。

## 4. 已知损失

1. 不是完整 PPCPP：没有在线权重优化、没有对角运动、没有动力学；
2. 三奖励的归一化方式、predator 规则是适配约定；
3. 权重来自一次开发网格选择，不是原文参数；
4. 死端恢复用的是统一最短路，不是原文恢复规则；
5. 与冻结三基线共用保底，因此"PPCPP 胜出"必须扣掉保底贡献才能解释。

## 5. 本轮接入方式

`src/adapters/reference_methods.py` 直接调用候选自带的、会校验 manifest 的
`load_candidate.solve(snapshot, initial_targets, budget, seed)`；
`tests/test_contract_and_identity.py` 逐案例比较适配器与直接调用的路线完全一致，
并用候选 manifest 复核源码哈希。
