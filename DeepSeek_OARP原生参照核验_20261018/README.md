# OARP 原生参照建设与机制验收（2026-10-18）

一句话：在 OUT 内实现了**原生条带结构**和**两个可运行参照**
（`OARP_RANK0_FULLTOUR_SCENE`、`OARP_REPLAN2_NATIVE_SCENE`），跑完 3 次原生初始准备 +
32 次事件响应，交付只读复核、数学/GTSP 子问题核验与 MLC 规格。

**本轮通过只表示"参照的机制与接口达到声明范围内的门槛"，不表示复现了作者机器人系统、
不继承原文理论保证、不证明最优、也不决定论文主算法。** 实现中存在一个未闭合缺陷
（见 `reports/原生闭环核验报告.md` §2 与 `交主会话验收.md` §6），因此**不建议**现在进入性能比较。

## 环境

```powershell
$taskRoot = 'D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_OARP原生参照核验_20261018'
$taskPython = 'D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe'
```

只读解释器 + 锁定依赖（SCIP / GLNS，位于
`..\DeepSeek_底层算法开发比较_20261018\sources\reference_tree\...\.deps`，
只读引用，不复制、不修改）。所有项目模块从 OUT 载入。

## 真实命令

```powershell
# 只读复核（不导入规划入口、不调用 solver、不写文件）
& $taskPython -B -X utf8 "$taskRoot\verify_delivery.py"

# 纯结构测试（不调用 solver）
Set-Location "$taskRoot\tests"; & $taskPython -B -X utf8 -m unittest test_native -v

# 会追加账本的接口测试（每跑一次都占调用预算）
$env:OARP_TEST_BATCH = "b2"
& $taskPython -B -X utf8 -m unittest test_entry -v

# 重新跑闭环（3 次准备 + 32 次响应，会追加账本，不覆盖旧结果）
& $taskPython -B -X utf8 "$taskRoot\src\run_micro.py"

# 重新跑数学/GTSP 子问题（42 + 4 次，不经过公共入口，单独计）
& $taskPython -B -X utf8 "$taskRoot\tools\run_math.py"
```

## 目录

```
protocol/   protocol.json method_config.json cases.json planned_runs.csv test_plan.md
            sha256.json（v1.0）sha256_v1_1.json（实际交付源码的摘要）
sources/    只读副本：v01 请求/结果/几何/审计、v02 Deadline、v03 finalize/grading、
            冻结 model+oarp_replan、主会话探针证据、原文与 MLC 第5章、验收稿
src/        bootstrap.py native.py methods.py entry.py run_micro.py adapters/registry.py
tests/      test_native.py（纯）、test_entry.py（含真实调用）
tools/      build_protocol.py run_math.py rebuild_summary.py
artifacts/  plans/ executions/ events/ responses/ requests/ 数学与 GTSP 结果、superseded/
logs/       calls_ledger.csv（两阶段账本）
manifests/  known_ledger_events.json、delivery_sha256.json
reports/    原文_适配_实现对应表.md 原生闭环核验报告.md 认证修复核查.md
            MLC适用子集与未来实现规格.md
verify_delivery.py  只读复核
```

## 停止点与限制

- 未运行十张真实开发图、未用留出、未跑 1/20/120 秒矩阵、未调参、未实现 MLC；
- 未开始"改进 OARP"，未把本轮任何步数差写成算法收益；
- 调用：完整入口 **75/75**（上限即停）、独立条带子问题 42/56、精确 GTSP 4/8；
- 未闭合：replan2 的原生块复用存在实现缺陷（17/24 配置退回保底，含无变化用例），
  账本中多次重跑产生重复 `run_id`（已逐条披露）。详见 `交主会话验收.md`。
