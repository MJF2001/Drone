# DeepSeek 基线复现隔离工作（2026-10-18）

本目录是《给DeepSeek的执行稿.md》的交付物。所有新代码、复制来源、依赖、测试、
路线产物、日志与报告都只在这里；`.remote_Drone` 只被只读复制，从未被写入。

## 1. 这一轮到底做了什么（先说结论）

1. **清点并逐字节复制**了四个已有方法的实际源码与固定依赖，用各自的 manifest
   复核 SHA256，并保留源端/副本双哈希。
2. **接入统一接口**：`P2_MULTI`、`TREE_MST`、`OARP_CORE2`、`PPCPP_CORE4` 原样调用，
   没有重新实现；用"适配器调用 vs 直接调用冻结入口"的逐案例比较证明行为未变。
3. **新增两个方法**：`EPSILON_STAR`（ε* 核心适配，保留多尺度 MAPS 与 ETM 状态机）
   与 `CSTAR`（历史未知环境复现的当前模型适配）。
4. **独立正确性验收**：17 个微图 × 6 个方法 = 102 次运行，全部合法或显式标注，
   0 个"硬问题"；另有独立审计器的负例测试、精确最优对照、连接器等价性测试。
5. **写规格不写代码**：`TRACE` 与 `LKH` 本轮只交付规格
   （`specs/TRACE_spec.md`、`specs/LKH_spec.md`）。
6. **写下一轮比较协议草案**：`reports/P2现状与下一轮比较协议草案.md`。本轮**没有**跑
   开发地图性能排名、参数搜索或留出实验。

## 2. 真实完成状态（不要读成"全部复现成功"）

| 项 | 状态 | 证据 |
|---|---|---|
| 来源清点与复制 | 完成 | `inventory.csv`、`manifests/source_copy_sha256.json` |
| 四个已有方法接入 | 完成，行为未变 | `tests/test_contract_and_identity.py` |
| ε* 核心适配 | 完成，含明确损失清单 | `specs/epsilon_star_adaptation.md` |
| C* 历史复现适配 | 完成，含机制退化证据 | `specs/cstar_adaptation.md` |
| 独立审计器与负例 | 完成 | `tests/test_audit_negative.py` |
| 微图正确性 | 完成（102 次，全部合法或显式标注） | `artifacts/runs/micro_runs.json` |
| 精确最优对照 | 完成（15 个可精确求解的微图） | `artifacts/runs/exact_micro.json` |
| TRACE / LKH | **仅规格**，未实现、未下载 | `specs/TRACE_spec.md`、`specs/LKH_spec.md` |
| 下一轮比较协议 | 草案完成，未执行 | `reports/P2现状与下一轮比较协议草案.md` |
| 性能排名 / 参数搜索 / 留出 | **未做**（本轮禁止） | — |

两个方法有**未解决的输入前提**，已在 `specs/method_original_mapping.md` §3 列明：
`OARP_CORE2` 要求旧剩余路线枚举出全部原待完成格；冻结方法在资源上限不足时会误报"自然结束"。

## 3. 依赖

| 依赖 | 版本 | 位置 |
|---|---|---|
| Python | 3.12.14（Windows x64，便携版） | `.remote_Drone\运行环境\python\python.exe`（**只读调用**，不安装任何包） |
| numpy | 2.5.4 | `sources/reference_tree/.../算法小型验证_20261010/.deps/numpy` |
| pyscipopt | 6.2.1 | 同上 `.deps/pyscipopt` |
| glns（作者维护的 C++ 版 GLNS python 扩展） | 0.1.0 | 同上 `.deps/glns` |

依赖是从既有研究目录**复制**进 OUT 的冻结副本，没有全局安装、没有联网下载。
本交付自身只用到标准库（ε*、C* 连接器、审计器、测试、检查器）。

## 4. 精确运行命令

所有命令在 PowerShell 中执行。**必须**关闭字节码写入并固定 UTF-8：

```powershell
$OUT = "D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018"
$py  = "D:\0A无人机仿真02\问题分析+文献分析\.remote_Drone\运行环境\python\python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TEMP = "$OUT\tmp"; $env:TMP = "$OUT\tmp"
```

### 4.1 只读验收（不启动规划器、不联网、不重建结果）

```powershell
& $py -B -X utf8 "$OUT\verify_delivery.py"
```

退出码 0 = 全部通过。它复核：副本与源端哈希、冻结/候选 bundle 的 manifest、
`.remote_Drone` 是否被改动、每条保存路线用独立审计器重算、
夹具哈希、交付清单哈希、以及是否残留 `__pycache__`。

### 4.2 重跑微图正确性（会启动规划器，但只跑微图）

```powershell
Set-Location "$OUT\src"
& $py -B -X utf8 "$OUT\src\run_micro.py"
```

输出：`artifacts/runs/micro_runs.json`、`artifacts/runs/exact_micro.json`、
`artifacts/routes/<case>/<method>.json`、`logs/run_micro_<stamp>.log`，
并往 `logs/call_ledger.csv` 追加每一次调用（重复调用不冒充独立样本）。

### 4.3 重跑全部测试

```powershell
Set-Location "$OUT\tests"
& $py -B -X utf8 -m unittest discover -s "$OUT\tests" -p "test_*.py" -v
```

### 4.4 重新生成夹具（**不要**在验收后运行；会改变夹具哈希）

```powershell
& $py -B -X utf8 "$OUT\tests\build_fixtures.py"
```

夹具一旦交付就冻结；`verify_delivery.py` 会比对 `micro_runs.json` 中记录的夹具哈希。

## 5. 目录

```
sources/            复制进来的来源（只读使用）
  reference_tree/   冻结 v2 + PPCPP 候选 + 固定依赖，保持原始相对布局
  cstar_historical/ 历史 C* 复现（未知环境）
  literature/       三篇原文、提取文本、ε* 页图、机制核查 JSON
  reports_referenced/ 本轮引用的编号报告
src/                本轮代码
  bootstrap.py      OUT 内源码/依赖装载与隔离断言
  problem.py        PlanRequest / Q,D 派生 / 校验 / 可达性
  result.py         PlanResult / StageClock
  common_geometry.py 共同四邻接连接器与精确度量
  audit_independent.py 独立审计器（只读输入与路线）
  epsilon_core/     ε* 的 MAPS 与 ETM 状态机
  cstar_core/       C* 移植：public_map / rcg / planner
  adapters/         六个方法的适配器 + registry
  run_micro.py      唯一的微图运行入口
specs/
  unified_interface.md      统一接口契约
  method_original_mapping.md 方法身份与四个已有方法的代码级对应表
  oarp_core2_mechanism.md   OARP_CORE2 适配规格
  ppcpp_core4_mechanism.md  PPCPP_CORE4 适配规格
  epsilon_star_adaptation.md ε* 适配规格与损失清单
  cstar_adaptation.md       C* 适配规格、机制表与退化实测
  TRACE_spec.md             TRACE 规格（本轮仅规格）
  LKH_spec.md               LKH 规格（本轮仅规格）
tests/
  build_fixtures.py         微图夹具生成器（交付后不要重跑）
  fixtures/cases/*.json     17 个冻结夹具
  exact_reference.py        独立的精确最优（状态空间 BFS）
  test_*.py                 78 项测试
artifacts/
  routes/<case>/<method>.json  每条保存路线 + 当时的审计结论
  runs/micro_runs.json         102 次运行总表
  runs/exact_micro.json        精确最优
  epsilon_trace/               ε* 手算决策轨迹
  cstar_trace/                 C* 决策轨迹与退化实测
logs/               运行日志与调用账本（call_ledger.csv）
manifests/          来源/副本哈希、保护基线、方法矩阵、交付清单
reports/            本轮报告、自动生成的微图结果表、下一轮协议草案
vendor/             故意留空，说明见 vendor/README.md
inventory.csv       来源清点（复制清单）
tmp/                临时脚本与 TEMP 重定向目标（不进交付哈希清单）
```

## 6. 边界（不要越读）

- 本交付**没有**证明任何方法是"最好的"，也**没有**做性能比较；
- 微图上的步数只说明"在这个小例子上某方法离精确最优多远"，不是排名；
- ε* 与 C* 都是**适配**，不是原文实验的复现；不能继承原文的完备性/长度界；
- `TREE_MST` 不是 TRACE/C*；`OARP_CORE2` 不是 OARP-Original 或完整 OARP-Replan；
- 冻结方法在资源不足时会误报完成，适配器已降级但**没有修改冻结源码**。

详见 `reports/本轮复现与适配报告.md` 与 `交主会话验收.md`。
