# DeepSeek 交付修订 v0.3（2026-10-18）

本目录是对 `../revision_v0.2/` 的**最小修订**，只闭合复核意见 A、B、C 三项。
v0.1 与 v0.2 的交付**原样保留**，没有原地刷新任何哈希。

## 1. 三项改动

| 项 | 复核指出的问题 | 现在的做法 |
|---|---|---|
| **A** | ε* 空任务分支只在连接前检查截止；`meta.deadline` 是开始时的快照 | 连接后、审核前后都检查；候选记录"生成/审核完成/接受"三时刻；**审核在截止后完成的路线只作诊断**，不进入评分；`meta.deadline` 末尾写入真实 `checks`/`elapsed`/`hit` |
| **B** | ε* 在 `finalize` 之前就停表，返回前审核不计入耗时 | `finalize`（含独立审计）在 `stop_total()` 之前执行；六个方法同一入口/出口边界 |
| **C** | 测试可绕过注册入口；写失败被 `except: pass` 吞掉；append-only 未实际验证 | 假时钟经 `registry.run(**kwargs)` 注入并有静态守卫；**两阶段账本**（先写 `start` 并 `fsync`，失败即中止；`end` 失败上报且**不封存批次**）；**前缀封存**（bytes/lines/SHA256，允许追加、禁止改写）；按 `run_id` 联结账本/清单/路线；删除、重复、篡改、孤儿行、写失败全有负例 |

逐条证据见 `证据_v0.3.md`，代码变更见 `变更表.md`。

## 2. 怎么跑

```powershell
$OUT = "D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018"
$V3  = "$OUT\revision_v0.3"
$py  = "D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$env:TEMP = "$V3\scratch"; $env:TMP = "$V3\scratch"

# 1) 只读验收（不启动规划器、不联网、不重建结果）
& $py -B -X utf8 "$V3\verify_v03.py"

# 2) 重跑本版测试（只向 logs_v03 追加登记，不改封存前缀）
Set-Location "$V3\tests_v03"
& $py -B -X utf8 -m unittest discover -s "$V3\tests_v03" -p "test_*.py" -v

# 3) 生成新一批正式微图调用（会重写 artifacts_v03 并重新封存账本）
Set-Location "$V3"
& $py -B -X utf8 "$V3\run_micro_v03.py" --kind formal
```

`verify_v03.py` 做六件事：核对 v0.1 与 v0.2 封存件未变、核对本版交付哈希、
用独立审计器重算每条保存路线并套语义门、**核查两阶段账本与 run_id 联结**、
校验**账本前缀封存**、运行语义门与账本审计器的负例自检。它不会启动规划器。

## 3. 目录

```
revision_v0.3/
  README_v03.md            本文件
  变更表.md                A/B/C 逐项状态 + 代码变更 + 数字对照
  证据_v0.3.md             逐项证据、复现命令、实测结果
  verify_v03.py            只读检查器（含账本审计与负例自检）
  run_micro_v03.py         正式微图入口（两阶段登记 + 封存 + 联结）
  src_v03/                 只放改动过的模块；其余只读复用 v0.2 / v0.1
    bootstrap_v03.py       解析顺序 src_v03 → src_v02 → src
    grading.py             语义门（检查器与测试共用）
    finalize.py            审计经模块属性调用，便于注入
    adapters/{__init__,registry,epsilon_star}.py
  tests_v03/               A / B / C 回归（20 项）
  artifacts_v03/           正式运行结果与逐格路线（含 run_id）
  logs_v03/                两阶段调用账本
  manifests_v03/           交付哈希 + 账本前缀封存
  tools/                   交付哈希生成
  scratch/                 测试/运行临时目录（不进交付哈希）
```

## 4. 边界

- **这是正确性微图批次，不是正式性能实验**；102 次正式调用只说明合法、可复现、口径一致；
- 逐格路线与 v0.2 相同（只改计时与截止语义），因此算法行为没有变；
- 仍不能判断 P2 是否已足够强，也不能据此选择底层算法；
- C* 仍是 restart 诊断版，账本不进核心；TRACE/LKH 仍只有规格；
- 权限没有再次修改或回滚；`.remote_Drone` 仍未写入；未提交、未推送。

## 5. 剩余缺口

1. ε* 的 `state_cycle` 仍是人为安全截断（已改名与注明，没有更强的终止策略）；
2. C* 的历史适配仍只有方案；
3. v0.1 / v0.2 时期未登记的调用数**未知**，只能标"未知"；
4. 下一轮协议的预算、任务数上限、种子与实例名单仍是 TBD。
