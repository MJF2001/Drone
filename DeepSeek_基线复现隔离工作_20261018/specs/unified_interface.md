# 统一接口规格（本轮实现）

本文件描述 `src/problem.py`、`src/result.py`、`src/adapters/registry.py` 实际实现的接口，
不是设想。所有方法——四个已有方法、ε*、C*——只通过这一个入口被调用。

## 1. 输入：`PlanRequest`

| 字段 | 含义 | 约束 |
|---|---|---|
| `case_id` | 实例标识 | 与夹具文件名一致 |
| `free` | 当前自由格集合 F（四邻接可通行） | frozenset of `(x, y)` |
| `published_targets` | 当前已发布目标集合 P | 含已被遮挡的暂缓目标 |
| `covered` | 真实覆盖账本 C | 必须 ⊆ P；不得包含从未经过的格 |
| `current` | 真实当前位置 | 必须在 F 内 |
| `base` | 基地 | 必须在 F 内 |
| `old_route` | 旧剩余路线（允许缺失，`()`） | 允许经过事件后已被封的格，见 §4 |
| `remaining_resource` | 剩余资源（可通行步数上限，`None` 表示不限） | > 0 |
| `seed` | 随机种子 | 决定所有随机决策 |
| `termination` | `Termination(time_limit_seconds, natural, extra)` | `time_limit_seconds` 是硬墙钟安全上限，不是自然终止条件 |
| `initial_targets` | 事件前的已发布目标（可选） | 仅用于 OARP_CORE2 的旧 rank 参照 |

派生量（不单独存储，避免与输入不一致）：

```
Q = pending  = (P - C) ∩ F          当前待完成
D = deferred = (P - C) - F          暂缓，不删除、不计完成
Q ∩ D = ∅
```

`to_snapshot()` 把请求转换为冻结 v2 需要的 `Snapshot`：`targets = P ∩ F`、`covered = C`、
`radius = 0`、`distance_budget = remaining_resource`。暂缓目标因此不会进入 `targets`，
但始终通过 `PlanRequest.deferred` 单独导出，报告中逐案例列出。

## 2. 校验：先报错，不悄悄删任务

`validate_inputs()` 对硬矛盾抛 `InputError(code, detail)`：

| code | 触发条件 |
|---|---|
| `input_types` | `free`/`published_targets` 不是 frozenset |
| `current_not_free` | 当前位置不可通行 |
| `base_not_free` | 基地不可通行 |
| `covered_not_published` | 账本含未发布的目标 |
| `nonpositive_resource` | 剩余资源 ≤ 0 |
| `nonpositive_time_limit` | 墙钟上限 ≤ 0 |

软提示（不阻断，写入报告）：

| code | 含义 |
|---|---|
| `old_route_crosses_blocked` | 旧剩余路线经过事件后新封的格。这是历史，不是矛盾 |
| `covered_target_now_blocked` | 已覆盖目标后来被遮挡。完成不撤销，只是不能再飞入 |

可达性由 `reachability()` 独立用四邻接 BFS 判定，`base_unreachable` / `target_unreachable`
作为**环境不可行**返回，与"规划器没找到"区分开。

## 3. 输出：`PlanResult`

| 字段 | 内容 |
|---|---|
| `method_id` / `method_version` | 方法与版本 |
| `status` / `reason` | 见 §5 |
| `route` | 完整逐格路线（`((x,y), ...)`），从 `current` 到 `base` |
| `route_steps` | `len(route)-1`，含返航 |
| `covered_physical` | 由独立审计器从路线重算的目标集合，不是自报 |
| `resource_check` | `{limit, used, ok}` 以及（已有方法）引擎自报秒数与预算 |
| `termination` | `{natural: bool, reason, ...}` |
| `fallback_used` / `fallback_steps` | 是否最终采用共同保底，以及该保底的步数 |
| `best_candidate_source` / `final_source` | 算法自身最好候选来源 / 最终输出来源 |
| `stage_seconds` | 真实插桩的阶段耗时；没有插桩就留空，不做推断 |
| `errors` | 错误或缺失说明 |
| `meta` | 方法特定细节（引擎状态、improvements、ε* 决策、C* 图统计等） |

无完整合法路线时同样输出记录：`route = ()`、`status` 说明原因、`meta` 保留 traceback。

## 4. 独立审计：`src/audit_independent.py`

只读输入与保存的逐格路线，重新计算：

1. 起点必须是 `current`，终点必须是 `base`；
2. 每一步 `|dx|+|dy| == 1`（斜跳直接拒绝）；
3. 每一格都在 `free` 内；
4. 覆盖 = `(C ∪ 路线经过格) ∩ P`，`Q` 必须全部被访问；
5. 资源 `route_steps <= remaining_resource`；
6. 暂缓目标既不在物理覆盖集合中，也不被飞越；
7. 统计重复经过、方向变化、目标访问次数。

它不 import 规划器的覆盖函数，也不读 `PlanResult.covered_physical`，
因此"规划器自报成功"不能通过审计。

## 5. 状态词表

| status | 含义 |
|---|---|
| `finished` / `planned` / `planned_at_timeout` / `complete_coverage` | 有合法路线；`planned_at_timeout` 仍要求路线合法且覆盖完整 |
| `environment_infeasible` | 独立可达性判定为不可行（基地或目标不可达），`route = ()` |
| `no_legal_route_within_resource` | 引擎本身没给出满足资源上限的候选；已有方法在冻结实现里会误报为自然结束，适配器已降级 |
| `resource_exceeded` | 有完整路线但超出资源上限，路线仍保存，状态显式说明 |
| `coverage_incomplete` | 路线合法但漏目标，`errors` 写明数量 |
| `input_precondition_unmet` | 方法自身的输入前提出不满足（例：OARP_CORE2 的旧路线必须枚举原待完成格） |
| `adapter_assertion` | 方法内部断言失败，traceback 记入 `meta` |
| `planning_failure` / `timeout` / `no_legal_candidate` | 冻结实现原有状态，原样透传 |

## 6. 共同连接器

- 已有四个方法：保持冻结实现里的 `UnifiedGeometry`（同一对端点只生成一种几何），
  以便行为不变；
- ε* 与 C*：使用 `src/common_geometry.py::GridMetric`，策略相同（精确 BFS 距离、
  每对无序端点一条规范最短路径、四邻接），实现独立，避免"用被检代码给自己作证"。
- `tests/test_exact_and_connector.py` 在所有微图上逐对比较两者距离，
  并要求路径长度一致、每步四邻接。

## 7. 隔离

`src/bootstrap.py` 只从 `OUT/sources/reference_tree` 载入冻结源码与固定依赖，
并断言 `baseline_suite.__file__` 位于 OUT 内。运行期不 import `.remote_Drone` 中的任何模块，
也不向其写文件。
