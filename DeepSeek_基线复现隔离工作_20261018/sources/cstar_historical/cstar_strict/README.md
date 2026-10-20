# C* 核心算法独立复现

这是针对 Shen、Wilson、Gupta 的 C* 论文所做的可运行、可审计的二维单机器人复现。目标是对齐论文 III-B 与 Algorithm 1–4 的核心数据流，同时把原文歧义、离散化及必要执行状态保护写成显式约定。它使用离散方格环境和圆形覆盖审计；准确性边界见 [SPEC.md](SPEC.md)，不声称与作者代码逐行等价或复现原始 Player/Stage 性能数值。

原文：

- [arXiv 固定版本 v3](https://arxiv.org/abs/2505.13782v3)
- [HTML 全文](https://arxiv.org/html/2505.13782v3)
- [IEEE DOI](https://doi.org/10.1109/TRO.2026.3661719)

本目录没有使用作者官方代码，论文以以上固定版本链接为准。

## 运行

在 `cstar_strict` 目录执行：

```powershell
python run.py --seeds 3 --radius 5 --ablation --require-full-coverage
python -m unittest -v
python validate_suite.py
```

`--ablation` 会对每个场景各运行一次开启 TSP 和关闭 TSP 的版本。输出保存在 `results/`：

- `metrics.json`：状态、轨迹长度、转弯数、回退次数、TSP 次数、连续面积覆盖审计和 RCG 规模；
- `traces.json`：每个 waypoint 的传感器新增观测、RCG 节点/边快照、运动模式和 TSP 事件；
- `config.json`：本次运行参数。
- `validation.json`：跨传感半径验证、逐例信息时序及覆盖审计、源码 SHA-256。

规划器只接收 `World.observe()` 的观测。真值自由空间只用于实验结束后的覆盖与碰撞审计。

## 当前验证

2026-09-20 修复了射线角点遮挡顺序、已有 link 锚点丢失及两节点固定终点 TSP。定向测试覆盖原断连反例、短半径漏扫、逐段观测时序、节点状态更新、link 插入/复用和 TSP 端点。

跨半径验证使用 3 个固定场景与 15 个随机障碍场景，传感半径分别为 1、2、3、5，TSP 开/关，共 144 次；覆盖半径为 0.75、lap 间距为 1、每格 4×4 子格。144 次全部满足：

- `status=graph_exhausted`；
- 规划边不穿越真值障碍；
- 子格面积采样覆盖率为 100%；
- 保守 certified lower bound 为 100%。
- 逐段运动只使用当时已经公开的自由格。

`results/metrics.json` 和 `traces.json` 保留标准 12 次实验的更新结果。TSP 是启发式，个别地图开启后可能更长，不能宣称每例都优于关闭版。计时含 Python 首次调用与缓存影响，不宜用单次值比较算法速度。

这些结果证明当前测试族上的实现和覆盖审计通过，不能推出论文定理对任意连续环境已经被重新证明。

## 文件

- [geometry.py](geometry.py)：观测、几何边可行性、连续圆盘扫掠覆盖审计；
- [rcg.py](rcg.py)：RCG 增量扩展、essential 节点/边处理、剪枝、状态更新和 RCG A*；
- [planner.py](planner.py)：C* Algorithm 1–4、retreat、coverage hole 和 TSP；
- [run.py](run.py)：未知世界实验和消融；
- [test_strict.py](test_strict.py)：回归测试；
- [validate_suite.py](validate_suite.py)：144 次跨半径验证；
- [SPEC.md](SPEC.md)：原文规则、实现约定和限制；
- [results/validation.json](results/validation.json)：本轮验证记录。
