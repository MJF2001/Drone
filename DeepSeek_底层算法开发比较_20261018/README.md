# DeepSeek 底层算法开发比较（2026-10-18）

本轮按 `给DeepSeek的执行稿.md` 在 `NEW` 内准备、冻结并执行**有上限的开发诊断**，
到达停止点后停止，不进入留出、不做参数搜索、不新增算法改进。

## 1. 一句话结论

（由 `reports/结果报告.md` 填写；本文件只做导航与口径说明）

## 2. 目录

```
NEW/
  给DeepSeek的执行稿.md      本轮授权稿（原件，不改）
  README.md                 本文件
  verify.py                 只读检查器（不启动规划器、不写任何文件）
  交主会话验收.md            交付与验收索引
  sources/                  只读复制：冻结v2+依赖、v0.1/v0.2/v0.3 源码、10个状态、微图、文档
  src/                      本轮代码：bootstrap、inputs、classify、run_task、adapters/{registry,epsilon_star}
  protocol/                 冻结协议：protocol.json、method_config.json、input_index.csv、
                            planned_runs.csv、preflight_planned_runs.csv、sha256.json
  preflight/                预检的 2 个固定合成微图与输入
  runs/                     每批次的 results/console/status.csv/batch_summary.json
  logs/                     两阶段调用账本 call_ledger.csv、批次控制台日志
  manifests/                来源复制哈希、调用预算、账本封存、已知缺陷、账本修复记录
  reports/                  结果报告、tables.md、summary.json
  figures/                  相对 P2 的极端例子示意图
  tests/                    负例自测（只写 tmp/）
  tmp/                      临时与缓存（不进交付哈希）
```

## 3. 运行方式（全部在 NEW 内）

```powershell
$NEW = "D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_底层算法开发比较_20261018"
$py  = "D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$env:TEMP = "$NEW\tmp"; $env:TMP = "$NEW\tmp"

# 只读验收：不启动规划器、不联网、不写文件
& $py -B -X utf8 "$NEW\verify.py"

# 负例自测（只写 tmp/）
Set-Location "$NEW\tests"; & $py -B -X utf8 -m unittest discover -s "$NEW\tests" -p "test_*.py" -v

# 重新生成表格与图（只读结果，不启动规划器）
& $py -B -X utf8 "$NEW\tools\report.py" --figures

# 调用预算守卫
& $py -B -X utf8 "$NEW\tools\call_counter.py" --check
```

## 4. 口径（读结果前必须知道）

- **完整剩余任务**：`Q=(P−C)∩F` 全部重算，含返航；不加入 SEED/PLUS1 之类范围选择，
  不混入局部前后缀限制。旧路线对所有方法可见，但不要求必须使用。
- **公共软上限**：`LONG120=120s`、`BUDGET20=20s`、`BUDGET1=1s`；硬上限
  `135/35/15s` 由父进程看门狗执行。**120 秒不是"算完了"，也不是无限时间**。
- **预算判定**：`call_total_seconds`（含输入核验、预处理、构造、搜索、连接、返航、
  返回前审核）≤ 软上限才算"可计入"；超出的路线保留，但标 `within_budget=false`
  并给出超出秒数，不计入预算内成绩。
- **自然结束与截断分开**：`natural_complete_valid` 是引擎自己的终止规则；
  `truncated_with_valid_candidate` 是限时/人工上限触发但已有合法路线；
  两者都不等于最优。
- **相对差**：`(L_method − L_P2)/L_P2`，负数表示该方法更短。
- **两条边界**：快照来自 P2 事件前的初始计划，因此结论条件于这 10 个真实状态；
  参照集合不完整（TRACE/LKH 只有规格），**不能用本轮胜负宣称 P2 已足够强**。

## 5. 未做的与不能声称的

- 未使用留出、未做参数搜索、未新增算法改进或混合、未给 P2 加后处理；
- 未跑 C* 性能（它仍是 restart 诊断版），未接入 TRACE/LKH；
- 未修改 `sources/` 之外的任何旧交付、未改权限、未提交推送；
- 正确性微图不是正式论文实验；本轮是开发诊断，不是性能排名。
