# 修订后的证据表（v2，离线派生）

由 `tools/derive_v2.py` 从已保存的 300 条开发结果派生，未启动任何规划器，未修改原结果、账本、协议或原报告。

## V1 引擎停止原因（替代原先的 `termination.natural`）

| 方法 | 自然收敛 | 内部时限 | 核心失败 | 预算截断 | 未知 |
|---|---:|---:|---:|---:|---:|
| P2_MULTI | 32 | 0 | 0 | 28 | 0 |
| TREE_MST | 40 | 0 | 0 | 20 | 0 |
| OARP_CORE2 | 49 | 6 | 5 | 0 | 0 |
| PPCPP_CORE4 | 60 | 0 | 0 | 0 | 0 |
| EPSILON_STAR | 42 | 0 | 0 | 18 | 0 |

原先记录为 `natural=True` 的 234 条中，按引擎自身证据只有 223 条真正自然收敛；**11 条属过度宣称**（OARP 的 rank 内部时限/不可行被记成自然完成）。

## V2 输出结果与来源

| 来源 | 次数 |
|---|---:|
| no_route | 18 |
| legal_in_budget | 234 |
| legal_over_budget | 48 |

| 方法 | 核心产出 | 共享保底 |
|---|---:|---:|
| P2_MULTI | 52 | 8 |
| TREE_MST | 32 | 28 |
| OARP_CORE2 | 46 | 14 |
| PPCPP_CORE4 | 48 | 12 |
| EPSILON_STAR | 60 | 0 |

## V3 同一样本上的速度比（不再用不同分母的中位数相除）

比值 = 该方法 `call_total_seconds` / 同一 case+seed 上的 P2 `call_total_seconds`；只在双方都有合法路线时计算。

| 方法 | 子集 | n | 最小 | p25 | 中位 | p75 | 最大 |
|---|---|---:|---:|---:|---:|---:|---:|
| TREE_MST | 双方合法 | 60 | 0.091 | 0.153 | 0.227 | 0.994 | 1.008 |
| TREE_MST | 双方都在预算内 | 32 | 0.091 | 0.128 | 0.154 | 0.166 | 0.241 |
| OARP_CORE2 | 双方合法 | 60 | 0.005 | 0.019 | 0.097 | 0.228 | 0.876 |
| OARP_CORE2 | 双方都在预算内 | 32 | 0.005 | 0.017 | 0.095 | 0.212 | 0.308 |
| PPCPP_CORE4 | 双方合法 | 60 | 0.001 | 0.004 | 0.041 | 0.069 | 0.405 |
| PPCPP_CORE4 | 双方都在预算内 | 32 | 0.001 | 0.003 | 0.041 | 0.065 | 0.222 |
| EPSILON_STAR | 双方合法 | 42 | 0.036 | 0.121 | 0.203 | 0.443 | 0.653 |
| EPSILON_STAR | 双方都在预算内 | 32 | 0.036 | 0.112 | 0.165 | 0.207 | 0.470 |

## V4 P2 的改进时间线（LONG120）

引擎相对时间；`首次改进` 是第一次被接受的合法候选，`达到最终质量` 是第一次得到最终步数。

| 图 | 种子 | 首次改进(s) | 首次步数 | 达到最终质量(s) | 最终步数 | 完整调用(s) | 最后停在 |
|---|---|---:|---:|---:|---:|---:|---|
| `large_g1` | 20261018 | 0.072 | 1243 | 31.707 | 941 | 120.6 | shuffle_0_opt |
| `large_g1` | 20261019 | 0.071 | 1243 | 31.770 | 941 | 120.6 | perturb_V_opt |
| `large_g2` | 20261018 | 0.008 | 563 | 27.441 | 561 | 71.9 | shuffle_1_expand |
| `large_g2` | 20261019 | 0.009 | 563 | 0.009 | 563 | 72.6 | shuffle_1_expand |
| `large_g3` | 20261018 | 0.075 | 1617 | 100.673 | 1387 | 120.8 | reverse_H_opt |
| `large_g3` | 20261019 | 0.082 | 1617 | 85.745 | 1387 | 120.6 | reverse_H_opt |
| `large_g4` | 20261018 | 0.020 | 1477 | 35.403 | 1219 | 120.2 | H_scan_deep |
| `large_g4` | 20261019 | 0.020 | 1477 | 35.926 | 1219 | 120.2 | H_scan_deep |
| `medium_g1` | 20261018 | 0.010 | 395 | 2.073 | 299 | 14.1 | shuffle_1_expand |
| `medium_g1` | 20261019 | 0.010 | 395 | 2.116 | 299 | 13.8 | shuffle_1_expand |
| `medium_g2` | 20261018 | 0.004 | 347 | 4.275 | 303 | 15.7 | shuffle_1_expand |
| `medium_g2` | 20261019 | 0.004 | 347 | 4.388 | 303 | 17.1 | shuffle_1_expand |
| `medium_g4` | 20261018 | 0.005 | 405 | 6.556 | 349 | 19.4 | shuffle_1_expand |
| `medium_g4` | 20261019 | 0.005 | 405 | 6.415 | 345 | 21.7 | shuffle_1_expand |
| `small_g2` | 20261018 | 0.001 | 89 | 0.069 | 71 | 0.4 | shuffle_1_expand |
| `small_g2` | 20261019 | 0.001 | 89 | 0.070 | 71 | 0.4 | shuffle_1_expand |
| `small_g3` | 20261018 | 0.003 | 133 | 0.101 | 87 | 0.6 | shuffle_1_expand |
| `small_g3` | 20261019 | 0.003 | 133 | 0.329 | 85 | 0.7 | shuffle_1_expand |
| `small_g4` | 20261018 | 0.000 | 46 | 0.015 | 42 | 0.1 | shuffle_1_expand |
| `small_g4` | 20261019 | 0.000 | 46 | 0.015 | 42 | 0.1 | shuffle_1_expand |

公共入口的首次改进时刻**未知**：引擎时钟在适配器内部起算，保存记录里没有引擎启动前的时刻，因此不能用 `call_total` 倒推。

## V5 P2 阶段成本与边际收益（LONG120，按图）

`改进` 是该阶段名与 `improvements[].source` 精确匹配到的新增改进次数；子过程 `*_passes` 事件不在保存的阶段里，阶段之间不重叠（已核对：无 `_passes` 键）。

| 图 | 种子 | 阶段 | 秒 | 新增改进 | 是否最终来源 |
|---|---|---|---:|---:|---|
| `large_g1` | 20261018 | `perturb_V_opt` | 24.33 | 0 |  |
| `large_g1` | 20261018 | `H_nearest` | 23.79 | 0 |  |
| `large_g1` | 20261018 | `shuffle_0_opt` | 18.33 | 0 |  |
| `large_g1` | 20261018 | `perturb_H_opt` | 17.39 | 0 |  |
| `large_g1` | 20261018 | `reverse_V_opt` | 8.02 | 0 |  |
| `large_g1` | 20261018 | `V_scan_opt` | 6.52 | 0 |  |
| `large_g1` | 20261018 | `V_NN_opt` | 4.81 | 0 |  |
| `large_g1` | 20261018 | `H_NN_opt` | 4.61 | 1 | 是 |
| `large_g1` | 20261018 | `H_scan_opt` | 3.18 | 0 |  |
| `large_g1` | 20261018 | `V_scan_deep` | 1.61 | 0 |  |
| `large_g1` | 20261018 | `V_NN_deep` | 1.59 | 0 |  |
| `large_g1` | 20261018 | `H_scan_deep` | 1.57 | 0 |  |
| `large_g1` | 20261018 | `reverse_H_opt` | 1.56 | 0 |  |
| `large_g1` | 20261018 | `H_NN_deep` | 1.53 | 0 |  |
| `large_g1` | 20261018 | `H_raw` | 0.02 | 1 |  |
| `large_g1` | 20261018 | `H_NN_raw` | 0.01 | 1 |  |
| `large_g1` | 20261019 | `perturb_H_opt` | 50.58 | 0 |  |
| `large_g1` | 20261019 | `H_nearest` | 23.68 | 0 |  |
| `large_g1` | 20261019 | `perturb_V_opt` | 9.66 | 0 |  |
| `large_g1` | 20261019 | `reverse_V_opt` | 8.07 | 0 |  |
| `large_g1` | 20261019 | `V_scan_opt` | 6.41 | 0 |  |
| `large_g1` | 20261019 | `V_NN_opt` | 4.83 | 0 |  |
| `large_g1` | 20261019 | `H_NN_opt` | 4.68 | 1 | 是 |
| `large_g1` | 20261019 | `H_scan_opt` | 3.27 | 0 |  |
| `large_g1` | 20261019 | `V_NN_deep` | 1.68 | 0 |  |
| `large_g1` | 20261019 | `V_scan_deep` | 1.60 | 0 |  |
| `large_g1` | 20261019 | `H_scan_deep` | 1.59 | 0 |  |
| `large_g1` | 20261019 | `reverse_H_opt` | 1.57 | 0 |  |
| `large_g1` | 20261019 | `H_NN_deep` | 1.52 | 0 |  |
| `large_g1` | 20261019 | `H_raw` | 0.02 | 1 |  |
| `large_g1` | 20261019 | `H_NN_raw` | 0.01 | 1 |  |
| `large_g2` | 20261018 | `shuffle_0_opt` | 20.28 | 0 |  |
| `large_g2` | 20261018 | `shuffle_1_opt` | 19.87 | 0 |  |
| `large_g2` | 20261018 | `perturb_H_opt` | 6.95 | 1 | 是 |
| `large_g2` | 20261018 | `perturb_V_opt` | 4.16 | 0 |  |
| `large_g2` | 20261018 | `V_NN_opt` | 4.14 | 0 |  |
| `large_g2` | 20261018 | `H_NN_opt` | 4.01 | 0 |  |
| `large_g2` | 20261018 | `H_scan_opt` | 3.68 | 0 |  |
| `large_g2` | 20261018 | `reverse_H_opt` | 3.41 | 0 |  |
| `large_g2` | 20261018 | `H_nearest` | 1.43 | 0 |  |
| `large_g2` | 20261018 | `V_scan_opt` | 1.06 | 0 |  |
| `large_g2` | 20261019 | `shuffle_0_opt` | 20.22 | 0 |  |
| `large_g2` | 20261019 | `shuffle_1_opt` | 20.20 | 0 |  |
| `large_g2` | 20261019 | `perturb_H_opt` | 6.00 | 0 |  |
| `large_g2` | 20261019 | `perturb_V_opt` | 5.27 | 0 |  |
| `large_g2` | 20261019 | `V_NN_opt` | 4.20 | 0 |  |
| `large_g2` | 20261019 | `H_NN_opt` | 4.04 | 0 |  |
| `large_g2` | 20261019 | `H_scan_opt` | 3.76 | 0 |  |
| `large_g2` | 20261019 | `reverse_H_opt` | 3.46 | 0 |  |
| `large_g2` | 20261019 | `H_nearest` | 1.43 | 0 |  |
| `large_g2` | 20261019 | `V_scan_opt` | 1.04 | 0 |  |
| `large_g3` | 20261018 | `H_nearest` | 29.98 | 0 |  |
| `large_g3` | 20261018 | `V_scan_opt` | 24.63 | 0 |  |
| `large_g3` | 20261018 | `V_scan_deep` | 20.16 | 1 | 是 |
| `large_g3` | 20261018 | `reverse_H_opt` | 16.07 | 0 |  |
| `large_g3` | 20261018 | `H_scan_opt` | 12.75 | 0 |  |
| `large_g3` | 20261018 | `V_NN_deep` | 3.25 | 0 |  |
| `large_g3` | 20261018 | `H_scan_deep` | 3.06 | 0 |  |
| `large_g3` | 20261018 | `V_NN_opt` | 3.02 | 0 |  |
| `large_g3` | 20261018 | `H_NN_deep` | 2.96 | 0 |  |
| `large_g3` | 20261018 | `H_NN_opt` | 2.91 | 0 |  |
| `large_g3` | 20261018 | `V_nearest` | 1.07 | 0 |  |
| `large_g3` | 20261018 | `H_NN_raw` | 0.01 | 1 |  |
| `large_g3` | 20261018 | `H_raw` | 0.01 | 1 |  |
| `large_g3` | 20261019 | `reverse_H_opt` | 31.59 | 0 |  |
| `large_g3` | 20261019 | `H_nearest` | 25.56 | 0 |  |
| `large_g3` | 20261019 | `V_scan_opt` | 20.64 | 0 |  |
| `large_g3` | 20261019 | `V_scan_deep` | 18.27 | 1 | 是 |
| `large_g3` | 20261019 | `H_scan_opt` | 10.25 | 0 |  |
| `large_g3` | 20261019 | `V_NN_deep` | 2.65 | 0 |  |
| `large_g3` | 20261019 | `H_scan_deep` | 2.54 | 0 |  |
| `large_g3` | 20261019 | `V_NN_opt` | 2.53 | 0 |  |
| `large_g3` | 20261019 | `H_NN_opt` | 2.50 | 0 |  |
| `large_g3` | 20261019 | `H_NN_deep` | 2.43 | 0 |  |
| `large_g3` | 20261019 | `H_NN_raw` | 0.01 | 1 |  |
| `large_g3` | 20261019 | `H_raw` | 0.01 | 1 |  |
| `large_g4` | 20261018 | `H_scan_deep` | 52.16 | 0 |  |
| `large_g4` | 20261018 | `H_scan_opt` | 15.98 | 1 |  |
| `large_g4` | 20261018 | `V_NN_opt` | 15.88 | 0 |  |
| `large_g4` | 20261018 | `V_scan_opt` | 15.84 | 0 |  |
| `large_g4` | 20261018 | `H_NN_opt` | 15.19 | 1 | 是 |
| `large_g4` | 20261018 | `H_nearest` | 4.18 | 0 |  |
| `large_g4` | 20261018 | `H_NN_raw` | 0.01 | 1 |  |
| `large_g4` | 20261019 | `H_scan_deep` | 49.91 | 0 |  |
| `large_g4` | 20261019 | `V_scan_opt` | 16.81 | 0 |  |
| `large_g4` | 20261019 | `V_NN_opt` | 16.57 | 0 |  |
| `large_g4` | 20261019 | `H_scan_opt` | 15.88 | 1 |  |
| `large_g4` | 20261019 | `H_NN_opt` | 15.86 | 1 | 是 |
| `large_g4` | 20261019 | `H_nearest` | 4.13 | 0 |  |
| `large_g4` | 20261019 | `H_NN_raw` | 0.01 | 1 |  |
| `medium_g1` | 20261018 | `shuffle_1_opt` | 3.98 | 0 |  |
| `medium_g1` | 20261018 | `shuffle_0_opt` | 3.90 | 0 |  |
| `medium_g1` | 20261018 | `perturb_H_opt` | 1.41 | 0 |  |
| `medium_g1` | 20261018 | `perturb_V_opt` | 1.25 | 0 |  |
| `medium_g1` | 20261018 | `H_nearest` | 1.00 | 0 |  |
| `medium_g1` | 20261018 | `H_scan_opt` | 0.55 | 1 |  |
| `medium_g1` | 20261018 | `H_NN_opt` | 0.31 | 1 |  |
| `medium_g1` | 20261018 | `V_scan_opt` | 0.16 | 1 | 是 |
| `medium_g1` | 20261018 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g1` | 20261019 | `shuffle_0_opt` | 3.96 | 0 |  |
| `medium_g1` | 20261019 | `shuffle_1_opt` | 3.88 | 0 |  |
| `medium_g1` | 20261019 | `perturb_H_opt` | 1.30 | 0 |  |
| `medium_g1` | 20261019 | `H_scan_opt` | 0.59 | 1 |  |
| `medium_g1` | 20261019 | `H_NN_opt` | 0.32 | 1 |  |
| `medium_g1` | 20261019 | `V_scan_opt` | 0.17 | 1 | 是 |
| `medium_g1` | 20261019 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g2` | 20261018 | `shuffle_1_opt` | 3.91 | 0 |  |
| `medium_g2` | 20261018 | `shuffle_0_opt` | 3.89 | 0 |  |
| `medium_g2` | 20261018 | `perturb_H_opt` | 2.31 | 0 |  |
| `medium_g2` | 20261018 | `reverse_H_opt` | 1.61 | 0 |  |
| `medium_g2` | 20261018 | `perturb_V_opt` | 1.01 | 0 |  |
| `medium_g2` | 20261018 | `H_NN_opt` | 0.15 | 1 |  |
| `medium_g2` | 20261018 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g2` | 20261018 | `reverse_V_raw` | 0.00 | 1 | 是 |
| `medium_g2` | 20261019 | `shuffle_0_opt` | 4.13 | 0 |  |
| `medium_g2` | 20261019 | `shuffle_1_opt` | 3.88 | 0 |  |
| `medium_g2` | 20261019 | `perturb_H_opt` | 2.43 | 0 |  |
| `medium_g2` | 20261019 | `perturb_V_opt` | 1.93 | 0 |  |
| `medium_g2` | 20261019 | `reverse_H_opt` | 1.72 | 0 |  |
| `medium_g2` | 20261019 | `H_NN_opt` | 0.15 | 1 |  |
| `medium_g2` | 20261019 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g2` | 20261019 | `reverse_V_raw` | 0.00 | 1 | 是 |
| `medium_g4` | 20261018 | `shuffle_0_opt` | 5.76 | 0 |  |
| `medium_g4` | 20261018 | `shuffle_1_opt` | 5.75 | 0 |  |
| `medium_g4` | 20261018 | `perturb_H_opt` | 2.09 | 1 | 是 |
| `medium_g4` | 20261018 | `perturb_V_opt` | 1.19 | 0 |  |
| `medium_g4` | 20261018 | `H_scan_opt` | 0.58 | 1 |  |
| `medium_g4` | 20261018 | `V_scan_opt` | 0.48 | 1 |  |
| `medium_g4` | 20261018 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g4` | 20261018 | `reverse_V_raw` | 0.00 | 1 |  |
| `medium_g4` | 20261019 | `shuffle_1_opt` | 6.19 | 0 |  |
| `medium_g4` | 20261019 | `shuffle_0_opt` | 6.07 | 0 |  |
| `medium_g4` | 20261019 | `perturb_V_opt` | 2.93 | 0 |  |
| `medium_g4` | 20261019 | `perturb_H_opt` | 2.16 | 1 | 是 |
| `medium_g4` | 20261019 | `H_scan_opt` | 0.56 | 1 |  |
| `medium_g4` | 20261019 | `V_scan_opt` | 0.50 | 1 |  |
| `medium_g4` | 20261019 | `H_NN_raw` | 0.00 | 1 |  |
| `medium_g4` | 20261019 | `reverse_V_raw` | 0.00 | 1 |  |
| `small_g2` | 20261018 | `H_scan_opt` | 0.01 | 1 |  |
| `small_g2` | 20261018 | `V_scan_opt` | 0.01 | 1 |  |
| `small_g2` | 20261018 | `reverse_V_raw` | 0.00 | 1 | 是 |
| `small_g2` | 20261018 | `H_NN_raw` | 0.00 | 1 |  |
| `small_g2` | 20261019 | `H_scan_opt` | 0.01 | 1 |  |
| `small_g2` | 20261019 | `V_scan_opt` | 0.01 | 1 |  |
| `small_g2` | 20261019 | `reverse_V_raw` | 0.00 | 1 | 是 |
| `small_g2` | 20261019 | `H_NN_raw` | 0.00 | 1 |  |
| `small_g3` | 20261018 | `V_scan_opt` | 0.02 | 1 | 是 |
| `small_g3` | 20261018 | `H_scan_opt` | 0.02 | 1 |  |
| `small_g3` | 20261018 | `H_NN_opt` | 0.01 | 1 |  |
| `small_g3` | 20261018 | `H_NN_raw` | 0.00 | 1 |  |
| `small_g3` | 20261018 | `H_raw` | 0.00 | 1 |  |
| `small_g3` | 20261019 | `perturb_V_opt` | 0.06 | 1 | 是 |
| `small_g3` | 20261019 | `V_scan_opt` | 0.03 | 1 |  |
| `small_g3` | 20261019 | `H_scan_opt` | 0.02 | 1 |  |
| `small_g3` | 20261019 | `H_NN_opt` | 0.01 | 1 |  |
| `small_g3` | 20261019 | `H_NN_raw` | 0.00 | 1 |  |
| `small_g3` | 20261019 | `H_raw` | 0.00 | 1 |  |
| `small_g4` | 20261018 | `H_NN_opt` | 0.00 | 1 | 是 |
| `small_g4` | 20261019 | `H_NN_opt` | 0.00 | 1 | 是 |

## V6 阶段成本占比（同一批次同一方法的分母）

分母 = 该批次该方法所有 `call_total_seconds` 之和；各阶段之和略小于分母，差额是阶段之间的未计时间隙。

| 批次 | 方法 | 阶段 | 合计秒 | 占该批调用总时 |
|---|---|---|---:|---:|
| LONG120 | P2_MULTI | `engine:H_nearest` | 117.27 | 12.1% |
| LONG120 | P2_MULTI | `engine:H_scan_deep` | 114.12 | 11.7% |
| LONG120 | P2_MULTI | `engine:V_scan_opt` | 94.83 | 9.8% |
| LONG120 | P2_MULTI | `engine:perturb_H_opt` | 92.82 | 9.6% |
| LONG120 | P2_MULTI | `engine:shuffle_0_opt` | 87.23 | 9.0% |
| LONG120 | P2_MULTI | `engine:H_scan_opt` | 72.43 | 7.4% |
| LONG120 | P2_MULTI | `engine:shuffle_1_opt` | 68.31 | 7.0% |
| LONG120 | P2_MULTI | `engine:reverse_H_opt` | 63.42 | 6.5% |
| LONG120 | P2_MULTI | `engine:V_NN_opt` | 58.45 | 6.0% |
| LONG120 | P2_MULTI | `engine:H_NN_opt` | 55.92 | 5.8% |
| LONG120 | P2_MULTI | `engine:perturb_V_opt` | 52.85 | 5.4% |
| LONG120 | P2_MULTI | `engine:V_scan_deep` | 43.44 | 4.5% |
| LONG120 | P2_MULTI | `engine:reverse_V_opt` | 18.75 | 1.9% |
| LONG120 | P2_MULTI | `engine:V_NN_deep` | 10.95 | 1.1% |
| LONG120 | P2_MULTI | `engine:H_NN_deep` | 10.13 | 1.0% |
| LONG120 | P2_MULTI | `engine:V_nearest` | 5.20 | 0.5% |
| BUDGET20 | P2_MULTI | `engine:H_nearest` | 95.09 | 35.9% |
| BUDGET20 | P2_MULTI | `engine:H_scan_opt` | 41.70 | 15.7% |
| BUDGET20 | P2_MULTI | `engine:shuffle_0_opt` | 27.89 | 10.5% |
| BUDGET20 | P2_MULTI | `engine:shuffle_1_opt` | 27.65 | 10.4% |
| BUDGET20 | P2_MULTI | `engine:reverse_H_opt` | 12.02 | 4.5% |
| BUDGET20 | P2_MULTI | `engine:perturb_H_opt` | 11.52 | 4.3% |
| BUDGET20 | P2_MULTI | `engine:V_NN_opt` | 10.77 | 4.1% |
| BUDGET20 | P2_MULTI | `engine:H_NN_opt` | 10.18 | 3.8% |
| BUDGET20 | P2_MULTI | `engine:perturb_V_opt` | 8.86 | 3.3% |
| BUDGET20 | P2_MULTI | `engine:V_scan_opt` | 3.93 | 1.5% |
| BUDGET20 | P2_MULTI | `engine:H_scan_deep` | 3.31 | 1.2% |
| BUDGET20 | P2_MULTI | `engine:V_NN_deep` | 1.82 | 0.7% |
| BUDGET20 | P2_MULTI | `engine:V_scan_deep` | 1.81 | 0.7% |
| BUDGET20 | P2_MULTI | `engine:H_NN_deep` | 1.69 | 0.6% |
| BUDGET20 | P2_MULTI | `engine:reverse_V_opt` | 1.58 | 0.6% |
| BUDGET1 | P2_MULTI | `engine:H_nearest` | 10.60 | 59.6% |
| BUDGET1 | P2_MULTI | `engine:H_scan_opt` | 2.50 | 14.1% |
