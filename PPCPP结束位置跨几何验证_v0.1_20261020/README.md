# 结束位置损失跨几何验证 v0.1

**执行完成，待负责人审核。** 先看[结果报告](结束位置跨几何验证结果.md)、[审核包](review_packet.md)。有限36开发槽位，6基础道路，全部保留；本目录没有新规划算法。

本机实际运行项目便携Python3.12.14/Windows。算法、精确搜索、独立复算/审核均标准库和已有项目依赖，plot.py另用matplotlib（临时路径/版本见plot_environment.json）。不声称另一台电脑已运行。

项目根目录一键只读核验：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP结束位置跨几何验证_v0.1_20261020/verify_delivery_v02.py
```

该命令不运行PPCPP或BFS/Dijkstra，只审封存、原请求/证书、保存的全部独立复算、账本/历史/输入、原逐决策、双指标、等价组、完整报告36行、固定图选取。verify.py只审核心输入与证书；verify_delivery另审复算证据与报告。搜索证书审核包含父边层序和低层后继闭包，不仅检查一条可行上界。

原始证据：prep为6准备输入/完整route/trace；inputs/witnesses/candidates为36状态/历史可行见证/预先选emin；execution为36正式PPCPP；exact按状态保存A/B/C请求、结果及gzip父边层序证书，mapping说明C复用；rechecks为93次独立frozenset-Dijkstra复算，60秒/查询子进程墙钟；call_ledger分账正式、门槛和审核；analysis含每槽位全部指标/分解与形状/完整状态等价。

需要重新执行时，仅使用不存在的同级新目录，产生新的复算证据，不并入本轮正式计数：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP结束位置跨几何验证_v0.1_20261020/replay.py --destination ./PPCPP结束位置验证_独立重放
```

这会按固定规则重新运行门槛、6准备、36正式PPCPP、最多108精确查询及其独立复算。全部逐例落盘，计时可变化；与封存完整route/trace和精确状态/长度/见证对照。当前交付没有额外运行这项全量重放；已有93主查询已全部经另一表示Dijkstra实际复算。若到限不加限，unresolved如实保留。对已有目录，完整原结果可续接；若发现请求/证书已落盘而结果未写的半项，先保留中断证据另版处理，禁止覆盖重试。

重画保存图可在副本中执行plot.py，设置SMALLGAP_PLOT_DEPS为已安装matplotlib目录即可，不需要算法调用。封存后的原报告/图/源码不要覆盖，优先只读verify。
