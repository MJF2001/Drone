# ε* 复刻忠实性核验与修订（2026-10-18）

依据 `../主会话验收_DeepSeek_20261018/epsilon复刻忠实性复审.md`，在新目录内
**独立核对作者原稿 → 定位实现偏差 → 重建核心 → 逐步轨迹核验**。

本轮不跑开发地图性能比较、不调参、不用留出、不改旧代码/旧结果/旧清单。

## 一句话结论

复审的两条主要问题在原文与源码里**都成立**，并且第 3 条（实现开销）也能指名到行：

1. **粗层级错位**：旧实现把整图当最粗层、把最细粗层标成 level 0 却从不给它算势场，
   2×2 那一层根本不存在。重建后 4×4 → 4 个 2×2、8×8 → 16 个 2×2 + 4 个 4×4，
   六张图逐层通过"互不重叠且覆盖外域"的断言。
2. **两条原决策分支从不执行**：旧实现在 ST 就先记覆盖、移动即记账，于是进入 CP0 时
   当前格已是 E，"当前格未探索"（Alg.1 L3）恒假，L4–L6 整段不可达——不只是少了
   WT 作业，**"上下都未覆盖时先上下移动"的往返组织规则也一起消失**。
   改成"只在作业时更新控制账本"后，L3–L6 真实触发（轨迹里 L6 触发 16/20/43/62/66 次，
   L5 在含障碍/环形图上触发 1–6 次），物理覆盖仍由审计器按路线重算且完整。
3. **实现开销**：整表扫描求 7×7 邻域、每次覆盖重建整张 state、逐层逐块重算粗势场——
   已按"等价数据结构替换"修掉（作业 n 次只做 n 次单格更新 + n×L 次祖先块更新，无全图重建）；
   连接器整图 BFS 与"每步重新决策"按原文语义**保持不动**。

另外发现一条复审没有点到的机制问题：**式 (5) 的转角成本不能设为 0**。
设 0 时 Alg.1 L5 的 {上,下} 两个候选代价相同，实测在环形房间地图上两格间来回震荡，
只能靠人工 `state_cycle` 截断。原文的转角项正是"继续直行更便宜"这一往返组织力的来源。

## 目录

```
sources/literature/          作者预印本文本（只读复制）
sources/v01/                 封存的 problem/result/common_geometry/audit_independent/model
sources/v02_epsilon_core/    旧 epsilon 核心（只读复制，仅用于三臂对照）
sources/epsilon_star.py      旧适配器（只读复制）
src/maps_faithful.py         重建的 MAPS（层次 / 势场 / 邻域 / 直接可达）
src/etm_faithful.py          重建的 ETM（ST/CP0/CPℓ/WT/FN、Alg.1、Eq.(5)）
src/adapter.py               统一入口：PlanRequest → 审计 → 结果行
src/bootstrap.py             解析顺序与隔离断言
tools/probe_structure.py     结构探针（0 次调用）
tools/probe_trace.py         三臂逐步轨迹（20 次调用）
tools/run_interface.py       统一接口微跑（4 次调用）
tests/test_epsilon_faithful.py   20 项单元测试（0 次调用）
reports/原文对应表.md        原文条款 → 代码 → 状态（保留/适配/未实现）
reports/修改说明.md          三条确认问题、修复方式、没改的东西
reports/核验证据.md          结构/轨迹/逃逸/势场/接口的实测证据
reports/未适配与限制.md      未实现项与适配项，逐条给理由
logs/call_ledger.csv         轨迹调用的逐步账本（48 行 = 3 次尝试，含被取代的 2 次）
logs/interface_ledger.csv    接口微跑账本（4 行）
logs/design_probe.md         11 次设计探针记录（选逃逸用例，未入交付账本）
artifacts/                   结构探针 JSON、轨迹 CSV/JSON、接口结果
```

## 复现命令

```powershell
$E  = "D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_epsilon忠实性核验_20261018"
$py = "D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$env:TEMP = "$E\tmp"; $env:TMP = "$E\tmp"

# 0) 只读检查（不启动规划器、不写文件）
& $py -B -X utf8 "$E\verify.py"

# 1) 结构探针：层次与邻域（0 次规划器调用）
Set-Location "$E"; & $py -B -X utf8 "$E\tools\probe_structure.py"

# 2) 单元测试（0 次调用）
Set-Location "$E\tests"; & $py -B -X utf8 -m unittest discover -s "$E\tests" -p "test_*.py" -v

# 3) 逐步轨迹（会新增 20 次调用；幂等重跑会在账本里追加新行）
Set-Location "$E"; & $py -B -X utf8 "$E\tools\probe_trace.py"

# 4) 统一接口微跑（4 次调用）
& $py -B -X utf8 "$E\tools\run_interface.py"
```

## 调用上限（预先声明）

| 类别 | 上限 | 实际 |
|---|---:|---:|
| 结构探针 | 0 | 0 |
| 逐步轨迹一次交付批次 | 20 | 20（另有 28 行被取代的尝试，保留未删） |
| 统一接口微跑 | 4 | 4 |
| 设计探针（选逃逸用例） | 12 | 11 |
| **合计** | **64** | **63** |

规则：不改参数反复试、每轮只改一件、被取代的尝试留在账本里、没有一次未登记调用。

## 边界

- 这是**机制核验**，不是性能结论。旧版 300 项结果保留，但不能用它证明
  "ε* 原文机制比 P2 差"，也不能用本轮的微图去替代。
- 新版本标注 `epsilon_star_faithful_v1_20261018`；它与旧版的关系见
  `reports/修改说明.md` §6。
- 原文的连续运动/连续时间反馈与单位步网格之间仍有语义差，本轮证明的是
  "层次、势场、邻域、分支可达性、逃逸尺度与原文一致"，**不是**"轨迹逐步等同"。
