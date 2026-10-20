# ε* 机制澄清与可靠接口集成（2026-10-18）

依据 `../主会话验收_DeepSeek_20261018/DeepSeek执行稿_epsilon机制澄清与可靠接口集成_20261018.md`
与 `epsilon新版本阶段验收.md`。本目录（OUT）是本轮唯一交付目录。

**交付的是可审核的实现与证据，不是性能排名。** 未跑开发地图、未跑 300 项旧对照、
未跑其它方法、未使用留出、未调参。

## 一句话

机制核验版的判定规则保留下来，但生产接口是**重写**的：它现在有公共软截止（含连接器返回后
的检查）、候选"生成→审核→接受"边界、由独立审计裁决的成功状态、资源/空任务/输入拒绝的
明确状态，以及两阶段登记账本。24 个预定微图任务、18 次边界调用、10 次轨迹补跑全部登记，
**96 次调用达到本轮上限**，`verify.py` 347 项只读检查通过。

## 目录

```
protocol/    protocol.json, method_config.json, cases.json, planned_runs.csv (+ v1_1/v1_2),
             test_plan.md, sha256.json, sha256_v1_1.json
sources/     只读副本：v01 请求/结果/几何/审计 + model、v02 Deadline、v03 finalize/grading、
             机制核验版核心、原文、三份验收稿
src/         bootstrap.py, inputs.py(输入包装), core/{maps,etm}.py, adapters/{registry,epsilon_star}.py,
             run_task.py
tests/       test_core_pure.py(18 项, 0 调用), test_boundaries.py(11 项, 18 调用)
tools/       build_cases, build_protocol, run_batch(硬看门狗+封存), build_manifest
artifacts/   runs/INT2*(24 条交付), runs/INT*(被取代), traces/INT3*(10 条逐条决策),
             console/, status_*.csv, batch_*.json
logs/        call_ledger.csv(96 次尝试的两阶段账本)
manifests/   ledger_seal_*.json(前缀封存), known_ledger_events.json, delivery_sha256.json
reports/     原文机制与场景适配对应表.md / 代码修改与行为影响.md / 验证结果与未闭合项.md
verify.py    只读复核
```

## 只读复核（推荐）

```powershell
$taskRoot = 'D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_epsilon机制与接口集成_20261018'
$taskPython = 'D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe'
& $taskPython -B -X utf8 "$taskRoot\verify.py"
```

`verify.py` 不启动规划器、不写文件、不追加账本；失败时非零退出。

## 会写账本的命令（每次调用都计数）

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$env:TEMP = "$taskRoot\tmp"; $env:TMP = "$taskRoot\tmp"

# 纯函数测试：18 项，0 次规划器调用
Set-Location "$taskRoot\tests"
& $taskPython -B -X utf8 -m unittest test_core_pure -v

# 边界测试：11 项，约 18 次完整调用，会追加账本
$env:EPS_TEST_BATCH = "b3"
& $taskPython -B -X utf8 -m unittest test_boundaries -v

# 重新跑预定集成批（24 次调用，会新增账本行；不覆盖旧结果）
& $taskPython -B -X utf8 "$taskRoot\tools\run_batch.py" `
    --plan "$taskRoot\protocol\planned_runs_v1_1.csv" --batch INTEGRATION_RERUN
```

## 冻结的配置

| 项 | 值 |
|---|---|
| 控制模式 | `task`（只在 WT 更新控制账本） |
| travel_cost / turn_cost | 1.0 / 1.0（每步 / 每度，90° = 90 步的代价） |
| 初始朝向 | 无（不捏造真实历史朝向） |
| 控制迭代上限 | 20 000 |
| 公共软截止 | 10 s（集成批），子进程硬看门狗 15 s |
| 候选版本 | core `epsilon_star_core_integrated_v1_20261018`，adapter `epsilon_star_adapter_integrated_v1_20261018` |

## 边界（不要误解）

- 不是原文的完整复现：连续运动、连续时间反馈、障碍禁飞带都没有建模；
- Theorem 1 / Corollary 1 只保留"每格只作业一次"的规则，**不构成**本模型下的定理证明；
- Remark 3.2 的 flood fill 明确未实现（已发布地图没有该信息缺口）；
- 不是性能结论：`finished` 只表示本次调用合法完成，不表示比旧版或别的方法更好；
- 未闭合项见 `reports/验证结果与未闭合项.md` §5：14 条交付批缺逐条决策轨迹、
  v1.0→v1.1 的冻结后改动、冻结前 20 次冒烟。
