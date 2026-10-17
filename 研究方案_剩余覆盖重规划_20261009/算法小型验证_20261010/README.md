# P1/P2首轮小型验证：使用说明

> 2026-10-10最新模型：正下方单格采集，障碍格未完成目标单独记为暂不可检查。当前结果见[单格模型重跑](results/run_14_single_cell_v3/结果报告.md)，入口为scenarios_v3.py与run_v3.py。下面关于3×3足迹与早期结果的内容仅作历史记录，不是当前实验规则。

> OARP-Replan两阶段核心及单格适配已实现，见[实现说明](oarp_replan/README.md)和[标准GLNS配置对照结果](results/run_16_oarp_default_v3/结果报告.md)。这不等于原论文端到端系统复现。

日期：2026-10-10。当前实现共同离散覆盖模型、两个完整原型、独立路径审计、规则场景生成、结果回放及静态路径图。

## 先看哪些结果？

- [当前较强初始路线组](results/run_04_incumbent_optimized/结果报告.md)
- [当前蛇形初始路线组](results/run_03_incumbent_snake/结果报告.md)
- [路径对照图](results/run_04_incumbent_optimized/paths_overview.png)

run_01和run_02是调试历史，缺少后续增加的共同旧路线候选规则，保留以展示过程，不与run_03/04合并报成绩。当前可复核结果以run_03/04为准，两者使用相同当前算法版本，但不同初始路线策略；不少快照相同，不能当作64个独立随机样本。

## 当前实际实现

P1：保留仍能承担未完成覆盖的旧访问顺序，失效位置跳过并补充覆盖责任，新采集位置按最低连接增量插入，最后展开合法路径并返航。

P2：重新生成全部剩余目标的离散采集位置，比较两种蛇形排列及最近邻初解，再做最多8轮2-opt，展开并返航。它不保证最优，也没有实现连续覆盖条带整数规划。

两者都保留仍合法、完整覆盖更新后任务且满足预算的旧后缀作为候选，并按最终实际路径长度选已得到的可行解。没有把旧后缀作为“必须保留”的全局顺序约束。

两者不是OARP-Replan、TRACE或C*的严格复现。P3、P4尚未实现。

## 本轮模型选择

- 单位格长、四邻接运动、固定3×3足迹，每到一个合法格点采集；转场与返航都应用同一采集规则。
- 待检道路外有2格通行余量；障碍仅是固定高度禁入投影，额外图像遮挡未模拟。
- 不可飞位置下方的目标保留，可以由邻近合法位置的足迹完成名义几何覆盖；不能解释为实物障碍可被看穿。
- 距离预算为通行域格数的4倍，只作宽松资源代理，不标定真实电池。
- 事件后位置固定，最长规划5秒；没有并发飞行、现场感知、真实图像或能耗模型。
- 所有32个场景均为探索性规则输入，不是现场采样、随机独立样本或最终确认集。

这些是本轮工程默认配置，不代表用户已审核通过最终论文物理模型。配置保存在config.json及每次运行的manifest.json中。

## 运行

使用Python 3.10以上。核心算法、测试、实验与回放仅用标准库；绘图需要Pillow。当前已使用Codex捆绑Python成功运行。

在本目录执行：

```powershell
python -m unittest -v test_validation
python run_experiments.py --output results/my_snake_run --initial-policy snake
python run_experiments.py --output results/my_optimized_run --initial-policy optimized
python replay_audit.py results/my_optimized_run
python render_paths.py results/my_optimized_run
```

结果目录已存在则拒绝覆盖；重新运行请换目录名。初始路线优化在事件前完成，耗时不计入事件后重规划。

## 可审计内容

- snapshots.json：每例完整输入，包含R、F、C、位置、基地、旧剩余路线及事件元数据。
- results.json：每次实际路线、状态、独立审计和时间。
- results.csv：逐次指标。
- summary.json：程序汇总。
- manifest.json：Python环境、有效配置和源码SHA-256。
- source_snapshot：run_03/04执行源码副本与有效配置，复制前校验与运行哈希一致。

14项定向测试通过，包含绕障、缓存更新、非法跳跃、漏覆盖、返航、资源不足不误称不可行、目标责任保留、新任务不追认、超时不误报完成、旧后缀不劣化等。测试通过只证明覆盖到的离散案例，不证明任意地图完备性。

对run_03与run_04各192条保存结果进行回放审计，均无不一致。来源哈希可追溯，但本轮没有将独立审计声称为连续运动或真实图像验证。

## 四原型第二轮
P3/P4已实现，入口run_four.py，输入复用既有snapshots.json。最终串行结果为results/run_07_four_optimized_serial与results/run_08_four_snake_serial；run_05/run_06为时间重叠的调试运行。每组384次执行，已独立replay审计；源码归档在各组source_snapshot内。P3并非TRACE增量树维护；P4并非OARP整数规划复现。详细限制见资料汇总目录12号报告。

## 机制对照与敏感性
最终结果为results/run_10_mechanisms_fixed_budget，协议见MECHANISM_PROTOCOL.md，入口run_mechanisms.py，保存文件核验verify_mechanisms.py。run_09是预算变量混入的调试记录，最终已固定原预算重跑。23项测试通过；128条机制记录与180条敏感性记录，410条实际路径独立复核无错误。结果解释见资料目录13号报告。此轮不作可靠计时比较，不是论文方法复现或独立确认集。

## 固定飞行域v0.2诊断
模型规范为资料目录14号文档，结果解释见15号文档。入口run_v2.py，生成器scenarios_v2.py，最终输出results/run_11_fixed_domain_v2。64个快照、P1/P2共128次执行；26项检查通过，verify_v2.py核验保存路径及共同历史、固定D无错误。render_v2_model.py生成输入语义示意图。仍是探索性仿真，不代表真实围栏在目标扩展时必定不变。

## 固定采集点精确排序参照
协议EXACT_ORDER_PROTOCOL.md；入口run_exact_order.py；求解器exact_order.py；最终输出results/run_12_exact_order。64个快照/128点池，64池精确、64池因超过14点未求解；不删目标。30项测试通过；verify_exact_order.py以BFS距离和独立递推重算精确值，复核1664条实际路线无错误。不是面积覆盖最优值或下界，不作与P2公平计时对比。结果解释见资料目录16号报告。

## 采集网格偏移诊断
协议PHASE_PROTOCOL.md；实现phase_search.py；入口run_phase_search.py。最终结果results/run_13_phase_search，64个快照、P2/SHIFT/REPEAT各2次，共384次输出；34项测试通过，verify_phase_search.py独立核查384条路线及4608个完整点池无错误。SHIFT在8例缩短、56例同长，总少1.21%，计算中位数约为P2的19.4倍。不是创新结论；详细审查见资料目录17号报告。
