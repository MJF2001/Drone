# 开发比较结果表（由 tools/report.py 生成）

读取 311 条保存结果；计划任务 312 条。

## T1 逐批次×方法汇总

`n` 为计划数；`可计入` 指合法且 `within_budget=true`；`自然/截断` 在上述可计入项内区分；`均值步数`、`均值总时` 只用可计入项。

| 批次 | 方法 | n | 已执行 | 可计入 | 自然 | 截断 | 无合法路线 | 前提拒绝 | 环境不可行 | 均值步数 | 均值总时(s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG120 | P2 | 20 | 20 | 14 | 14 | 0 | 0 | 0 | 0 | 244.3 | 17.763 |
| LONG120 | MST | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 536.7 | 17.626 |
| LONG120 | OARP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 557.9 | 0.781 |
| LONG120 | PPCPP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 558.3 | 0.147 |
| LONG120 | eps* | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 577.1 | 18.926 |
| BUDGET20 | P2 | 20 | 20 | 12 | 12 | 0 | 0 | 0 | 0 | 191.3 | 8.484 |
| BUDGET20 | MST | 20 | 20 | 14 | 14 | 0 | 0 | 0 | 0 | 256.3 | 2.189 |
| BUDGET20 | OARP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 557.9 | 0.782 |
| BUDGET20 | PPCPP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 558.3 | 0.147 |
| BUDGET20 | eps* | 20 | 20 | 14 | 14 | 0 | 6 | 0 | 0 | 286.9 | 2.157 |
| BUDGET1 | P2 | 20 | 20 | 6 | 6 | 0 | 0 | 0 | 0 | 66.3 | 0.393 |
| BUDGET1 | MST | 20 | 20 | 6 | 6 | 0 | 0 | 0 | 0 | 73.3 | 0.066 |
| BUDGET1 | OARP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 609.1 | 0.374 |
| BUDGET1 | PPCPP | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 558.3 | 0.149 |
| BUDGET1 | eps* | 20 | 20 | 8 | 8 | 0 | 12 | 0 | 0 | 141 | 0.213 |

## T2 逐图步数（两个种子逐项）

同一格内为 `种子A/种子B`；`×` 表示该次不可计入（失败或超预算）。

| 图 | P2 L120 | P2 B20 | P2 B1 | MST L120 | MST B20 | MST B1 | OARP L120 | OARP B20 | OARP B1 | PPCPP L120 | PPCPP B20 | PPCPP B1 | eps* L120 | eps* B20 | eps* B1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `small_g2` | 71 / 71 | 71 / 71 | 71 / 71 | 75 / 75 | 75 / 75 | 75 / 75 | 79 / 79 | 79 / 79 | 73 / 73 | 83 / 83 | 83 / 83 | 83 / 83 | 85 / 87 | 85 / 87 | 85 / 87 |
| `small_g3` | 87 / 85 | 87 / 85 | 87 / 85 | 99 / 99 | 99 / 99 | 99 / 99 | 101 / 101 | 101 / 101 | 101 / 101 | 95 / 95 | 95 / 95 | 95 / 95 | 101 / 101 | 101 / 101 | 101 / 101 |
| `small_g4` | 42 / 42 | 42 / 42 | 42 / 42 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 46 / 46 | 60 / 60 | 60 / 60 | 60 / 60 |
| `medium_g1` | 299 / 299 | 299 / 299 | × / × | 351 / 351 | 351 / 351 | × / × | 359 / 359 | 359 / 359 | 325 / 325 | 367 / 367 | 367 / 367 | 367 / 367 | 363 / 367 | 363 / 367 | × / × |
| `medium_g2` | 303 / 303 | 303 / 303 | × / × | 315 / 315 | 315 / 315 | × / × | 311 / 311 | 311 / 311 | 347 / 347 | 323 / 323 | 323 / 323 | 323 / 323 | 317 / 317 | 317 / 317 | 317 / 317 |
| `medium_g4` | 349 / 345 | 349 / 345 | × / × | 345 / 345 | 345 / 345 | × / × | 343 / 343 | 343 / 343 | 343 / 343 | 397 / 397 | 397 / 397 | 397 / 397 | 417 / 425 | 417 / 425 | × / × |
| `large_g1` | × / × | × / × | × / × | 935 / 935 | × / × | × / × | 1199 / 1199 | 1199 / 1199 | 1199 / 1199 | 941 / 941 | 941 / 941 | 941 / 941 | 1073 / 1073 | × / × | × / × |
| `large_g2` | 561 / 563 | × / × | × / × | 563 / 563 | 563 / 563 | × / × | 557 / 557 | 557 / 557 | 563 / 563 | 563 / 563 | 563 / 563 | 563 / 563 | 663 / 653 | 663 / 653 | × / × |
| `large_g3` | × / × | × / × | × / × | 1383 / 1383 | × / × | × / × | 1391 / 1391 | 1391 / 1391 | 1617 / 1617 | 1389 / 1389 | 1389 / 1389 | 1389 / 1389 | 1389 / 1389 | × / × | × / × |
| `large_g4` | × / × | × / × | × / × | 1255 / 1255 | × / × | × / × | 1193 / 1193 | 1193 / 1193 | 1477 / 1477 | 1379 / 1379 | 1379 / 1379 | 1379 / 1379 | 1301 / 1301 | × / × | × / × |

## T3 相对 P2 的配对比较（只在双方都可计入的配对里计算）

相对差 = (L_method − L_P2) / L_P2，负数表示该方法更短。`基数0` 计入 `P2=0` 的配对，另列。

| 批次 | 方法 | 有效配对 | 短/平/长 | 有效配对的均值相对差 | 地图等权均值相对差 | 基数0配对 |
|---|---|---:|---|---:|---:|---:|
| LONG120 | MST | 14 | 1/2/11 | 0.0732 | 0.0732 | 0 |
| LONG120 | OARP | 14 | 4/0/10 | 0.0842 | 0.0842 | 0 |
| LONG120 | PPCPP | 14 | 0/1/13 | 0.1155 | 0.1155 | 0 |
| LONG120 | eps* | 14 | 0/0/14 | 0.2094 | 0.2094 | 0 |
| BUDGET20 | MST | 12 | 1/1/10 | 0.0851 | 0.0851 | 0 |
| BUDGET20 | OARP | 12 | 2/0/10 | 0.0997 | 0.0997 | 0 |
| BUDGET20 | PPCPP | 12 | 0/0/12 | 0.1344 | 0.1344 | 0 |
| BUDGET20 | eps* | 12 | 0/0/12 | 0.2158 | 0.2158 | 0 |
| BUDGET1 | MST | 6 | 0/0/6 | 0.1010 | 0.1010 | 0 |
| BUDGET1 | OARP | 6 | 0/0/6 | 0.0993 | 0.0993 | 0 |
| BUDGET1 | PPCPP | 6 | 0/0/6 | 0.1230 | 0.1230 | 0 |
| BUDGET1 | eps* | 6 | 0/0/6 | 0.2715 | 0.2715 | 0 |

## T4 质量与时间二维表（可计入项）

中位步数、中位端到端时间与两者同时给出的位置；不能只按一个指标宣布冠军。

| 批次 | 方法 | 中位步数 | 中位总时(s) | 可计入率 | 步数最短次数 |
|---|---|---:|---:|---:|---:|
| LONG120 | P2 | 299.0 | 13.951 | 0.70 | 10 |
| LONG120 | MST | 348.0 | 2.216 | 1.00 | 4 |
| LONG120 | OARP | 351.0 | 0.321 | 1.00 | 6 |
| LONG120 | PPCPP | 382.0 | 0.062 | 1.00 | 0 |
| LONG120 | eps* | 392.0 | 2.299 | 1.00 | 0 |
| BUDGET20 | P2 | 193.0 | 7.336 | 0.60 | 10 |
| BUDGET20 | MST | 315.0 | 1.476 | 0.70 | 0 |
| BUDGET20 | OARP | 351.0 | 0.310 | 1.00 | 6 |
| BUDGET20 | PPCPP | 382.0 | 0.061 | 1.00 | 4 |
| BUDGET20 | eps* | 317.0 | 0.617 | 0.70 | 0 |
| BUDGET1 | P2 | 71.0 | 0.420 | 0.30 | 6 |
| BUDGET1 | MST | 75.0 | 0.071 | 0.30 | 0 |
| BUDGET1 | OARP | 345.0 | 0.278 | 1.00 | 6 |
| BUDGET1 | PPCPP | 382.0 | 0.063 | 1.00 | 8 |
| BUDGET1 | eps* | 94.0 | 0.093 | 0.40 | 2 |

## T5 P2 的阶段证据（引擎自报 `events`，已剔除父子包含）

只统计 P2 的行；`出现次数` 是该阶段有真实计时的记录数，缺插桩的阶段不会被填 0。

| 批次 | 阶段 | 出现次数 | 合计秒 | 中位秒 |
|---|---|---:|---:|---:|
| LONG120 | `H_nearest` | 20 | 117.270 | 0.6448 |
| LONG120 | `H_scan_deep` | 20 | 114.116 | 0.3078 |
| LONG120 | `V_scan_opt` | 20 | 94.834 | 0.3677 |
| LONG120 | `perturb_H_opt` | 16 | 92.817 | 1.7501 |
| LONG120 | `shuffle_0_opt` | 15 | 87.230 | 3.9034 |
| LONG120 | `H_scan_opt` | 20 | 72.431 | 0.6201 |
| LONG120 | `shuffle_1_opt` | 14 | 68.307 | 3.8814 |
| LONG120 | `reverse_H_opt` | 18 | 63.424 | 0.6083 |
| LONG120 | `V_NN_opt` | 20 | 58.454 | 0.5293 |
| LONG120 | `H_NN_opt` | 20 | 55.920 | 0.4433 |
| LONG120 | `perturb_V_opt` | 16 | 52.854 | 1.0979 |
| LONG120 | `V_scan_deep` | 18 | 43.437 | 0.1077 |
| LONG120 | `reverse_V_opt` | 16 | 18.752 | 0.1543 |
| LONG120 | `V_NN_deep` | 18 | 10.945 | 0.1075 |
| BUDGET20 | `H_nearest` | 20 | 95.092 | 0.7393 |
| BUDGET20 | `H_scan_opt` | 16 | 41.698 | 0.5762 |
| BUDGET20 | `shuffle_0_opt` | 12 | 27.889 | 2.0899 |
| BUDGET20 | `shuffle_1_opt` | 12 | 27.651 | 2.0499 |
| BUDGET20 | `reverse_H_opt` | 14 | 12.016 | 0.5663 |
| BUDGET20 | `perturb_H_opt` | 12 | 11.516 | 0.7017 |
| BUDGET20 | `V_NN_opt` | 14 | 10.767 | 0.1599 |
| BUDGET20 | `H_NN_opt` | 14 | 10.181 | 0.1628 |
| BUDGET20 | `perturb_V_opt` | 12 | 8.855 | 0.5024 |
| BUDGET20 | `V_scan_opt` | 14 | 3.930 | 0.1694 |
| BUDGET20 | `H_scan_deep` | 14 | 3.309 | 0.1007 |
| BUDGET20 | `V_NN_deep` | 14 | 1.820 | 0.1000 |
| BUDGET20 | `V_scan_deep` | 14 | 1.807 | 0.1056 |
| BUDGET20 | `H_NN_deep` | 14 | 1.690 | 0.0803 |
| BUDGET1 | `H_nearest` | 20 | 10.595 | 0.5993 |
| BUDGET1 | `H_scan_opt` | 11 | 2.499 | 0.0152 |
| BUDGET1 | `shuffle_1_opt` | 6 | 0.653 | 0.1236 |
| BUDGET1 | `shuffle_0_opt` | 6 | 0.653 | 0.1221 |
| BUDGET1 | `H_NN_opt` | 10 | 0.600 | 0.0131 |
| BUDGET1 | `fallback` | 20 | 0.212 | 0.0033 |
| BUDGET1 | `perturb_V_opt` | 6 | 0.202 | 0.0376 |
| BUDGET1 | `perturb_H_opt` | 6 | 0.173 | 0.0316 |
| BUDGET1 | `H_raw` | 20 | 0.099 | 0.0022 |
| BUDGET1 | `V_scan_opt` | 6 | 0.070 | 0.0101 |
| BUDGET1 | `reverse_H_opt` | 6 | 0.060 | 0.0101 |
| BUDGET1 | `reverse_V_opt` | 6 | 0.052 | 0.0082 |
| BUDGET1 | `V_NN_opt` | 6 | 0.034 | 0.0038 |
| BUDGET1 | `H_generate` | 20 | 0.029 | 0.0005 |

## T7 保底来源与覆盖（哪些成绩其实不是该方法自己的路线）

`保底` 指该方法最终提交的是共享保底候选（旧路线后缀 / 共同贪心），不是它自己的核心构造结果。这一列必须和方法名一起读。

| 批次 | 方法 | 结果数 | 保底 | 核心 | 核心链路可计速率 | 主要 final_source |
|---|---|---:|---:|---:|---:|---|
| LONG120 | P2 | 20 | 1 | 19 | 13/19 | `H_NN_opt`×6, `reverse_V_raw`×4, `perturb_H_opt`×3 |
| LONG120 | MST | 20 | 4 | 16 | 16/16 | `MST_preorder_2opt`×16, `common_GD_adapter`×2, `common_old_suffix`×2 |
| LONG120 | OARP | 20 | 2 | 18 | 18/18 | `RANK_and_TOUR`×18, `old_suffix`×2 |
| LONG120 | PPCPP | 20 | 4 | 16 | 16/16 | `PPCPP_core4`×16, `common_fallback`×2, `old_suffix`×2 |
| LONG120 | eps* | 20 | 0 | 20 | 20/20 | `etm_core_route`×20 |
| BUDGET20 | P2 | 20 | 2 | 18 | 12/18 | `H_raw`×4, `reverse_V_raw`×4, `V_scan_opt`×3 |
| BUDGET20 | MST | 20 | 10 | 10 | 10/10 | `MST_preorder_2opt`×10, `common_GD_adapter`×8, `common_old_suffix`×2 |
| BUDGET20 | OARP | 20 | 2 | 18 | 18/18 | `RANK_and_TOUR`×18, `old_suffix`×2 |
| BUDGET20 | PPCPP | 20 | 4 | 16 | 16/16 | `PPCPP_core4`×16, `common_fallback`×2, `old_suffix`×2 |
| BUDGET20 | eps* | 20 | 0 | 20 | 14/20 | `etm_core_route`×14, ``×6 |
| BUDGET1 | P2 | 20 | 5 | 15 | 6/15 | `common_fallback`×5, `H_raw`×4, `H_NN_opt`×3 |
| BUDGET1 | MST | 20 | 14 | 6 | 4/6 | `common_GD_adapter`×12, `MST_preorder_2opt`×6, `common_old_suffix`×2 |
| BUDGET1 | OARP | 20 | 10 | 10 | 10/10 | `RANK_and_TOUR`×10, `common_fallback`×8, `old_suffix`×2 |
| BUDGET1 | PPCPP | 20 | 4 | 16 | 16/16 | `PPCPP_core4`×16, `common_fallback`×2, `old_suffix`×2 |
| BUDGET1 | eps* | 20 | 0 | 20 | 8/20 | ``×12, `etm_core_route`×8 |

## T8 配对覆盖：被排除的配对在哪里

`双方可计入` 才是 T3 的分母。P2 超预算的格子会被整对排除，因此 T3 的结果条件于“P2 在预算内完成”。

| 批次 | 图 | 种子 | P2 可计入 | 可配对方法数 | 说明 |
|---|---|---|---:|---:|---|
| LONG120 | `small_g2` | 20261018 | 是 | 4 |  |
| LONG120 | `small_g2` | 20261019 | 是 | 4 |  |
| LONG120 | `small_g3` | 20261018 | 是 | 4 |  |
| LONG120 | `small_g3` | 20261019 | 是 | 4 |  |
| LONG120 | `small_g4` | 20261018 | 是 | 4 |  |
| LONG120 | `small_g4` | 20261019 | 是 | 4 |  |
| LONG120 | `medium_g1` | 20261018 | 是 | 4 |  |
| LONG120 | `medium_g1` | 20261019 | 是 | 4 |  |
| LONG120 | `medium_g2` | 20261018 | 是 | 4 |  |
| LONG120 | `medium_g2` | 20261019 | 是 | 4 |  |
| LONG120 | `medium_g4` | 20261018 | 是 | 4 |  |
| LONG120 | `medium_g4` | 20261019 | 是 | 4 |  |
| LONG120 | `large_g1` | 20261018 | 否 | 0 | P2 status=finished total=120.6s |
| LONG120 | `large_g1` | 20261019 | 否 | 0 | P2 status=finished total=120.6s |
| LONG120 | `large_g2` | 20261018 | 是 | 4 |  |
| LONG120 | `large_g2` | 20261019 | 是 | 4 |  |
| LONG120 | `large_g3` | 20261018 | 否 | 0 | P2 status=finished total=120.8s |
| LONG120 | `large_g3` | 20261019 | 否 | 0 | P2 status=finished total=120.6s |
| LONG120 | `large_g4` | 20261018 | 否 | 0 | P2 status=finished total=120.2s |
| LONG120 | `large_g4` | 20261019 | 否 | 0 | P2 status=finished total=120.2s |
| BUDGET20 | `small_g2` | 20261018 | 是 | 4 |  |
| BUDGET20 | `small_g2` | 20261019 | 是 | 4 |  |
| BUDGET20 | `small_g3` | 20261018 | 是 | 4 |  |
| BUDGET20 | `small_g3` | 20261019 | 是 | 4 |  |
| BUDGET20 | `small_g4` | 20261018 | 是 | 4 |  |
| BUDGET20 | `small_g4` | 20261019 | 是 | 4 |  |
| BUDGET20 | `medium_g1` | 20261018 | 是 | 4 |  |
| BUDGET20 | `medium_g1` | 20261019 | 是 | 4 |  |
| BUDGET20 | `medium_g2` | 20261018 | 是 | 4 |  |
| BUDGET20 | `medium_g2` | 20261019 | 是 | 4 |  |
| BUDGET20 | `medium_g4` | 20261018 | 是 | 4 |  |
| BUDGET20 | `medium_g4` | 20261019 | 是 | 4 |  |
| BUDGET20 | `large_g1` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=20.6s |
| BUDGET20 | `large_g1` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=20.6s |
| BUDGET20 | `large_g2` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=20.1s |
| BUDGET20 | `large_g2` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=20.1s |
| BUDGET20 | `large_g3` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=20.6s |
| BUDGET20 | `large_g3` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=20.6s |
| BUDGET20 | `large_g4` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=20.3s |
| BUDGET20 | `large_g4` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=20.3s |
| BUDGET1 | `small_g2` | 20261018 | 是 | 4 |  |
| BUDGET1 | `small_g2` | 20261019 | 是 | 4 |  |
| BUDGET1 | `small_g3` | 20261018 | 是 | 4 |  |
| BUDGET1 | `small_g3` | 20261019 | 是 | 4 |  |
| BUDGET1 | `small_g4` | 20261018 | 是 | 4 |  |
| BUDGET1 | `small_g4` | 20261019 | 是 | 4 |  |
| BUDGET1 | `medium_g1` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `medium_g1` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `medium_g2` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `medium_g2` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `medium_g4` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `medium_g4` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.0s |
| BUDGET1 | `large_g1` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |
| BUDGET1 | `large_g1` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |
| BUDGET1 | `large_g2` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.1s |
| BUDGET1 | `large_g2` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.1s |
| BUDGET1 | `large_g3` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |
| BUDGET1 | `large_g3` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |
| BUDGET1 | `large_g4` | 20261018 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |
| BUDGET1 | `large_g4` | 20261019 | 否 | 0 | P2 status=planned_at_timeout total=1.2s |

## T6 相对 P2 的极端例子（固定规则选取）

按配对相对差排序，取 P2 相对更长的最多 3 例和 P2 相对更短的最多 3 例；同一用例每个方法只出现一次。

| 方向 | 图 | 种子 | 方法 | 该方法步数 | P2 步数 | 相对差 |
|---|---|---|---|---:|---:|---:|
| P2 更长 | `large_g1` | 20261018 | PPCPP | 941 | 1239 | -0.2405 |
| P2 更长 | `medium_g1` | 20261018 | OARP | 325 | 395 | -0.1772 |
| P2 更长 | `medium_g4` | 20261018 | OARP | 343 | 377 | -0.0902 |
| P2 更短 | `small_g4` | 20261019 | eps* | 60 | 42 | +0.4286 |
| P2 更短 | `large_g1` | 20261019 | OARP | 1199 | 941 | +0.2742 |
| P2 更短 | `medium_g4` | 20261019 | eps* | 425 | 345 | +0.2319 |
