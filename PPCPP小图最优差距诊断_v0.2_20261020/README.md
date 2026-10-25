# 小图最优差距诊断：有效v0.2

执行完成、自检通过，**待研究负责人审核**。先看[结果报告](小图最优差距诊断结果.md)和[审核包](review_packet.md)。24槽位来自4基础道路；新图从运行起均为已见开发数据，不是最终留出。没有改进算法或下一轮自动运行。

本机实际环境Python3.12.14，Windows；使用项目便携Python运行算法、精确搜索和审核，只需标准库及原项目依赖。实际完整解释器路径和系统见protocol.json。不要把本次结果表述为其他电脑已验证。绘图额外用matplotlib，仅在临时目录安装，算法/审核不依赖它；版本另见plot_environment.json，PNG/SVG已保存。

项目根目录只读一键核验（不调用规划器、不重新精确求解）：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP小图最优差距诊断_v0.2_20261020/verify_delivery.py
```

核验manifest全部文件、原来源/输入哈希、4历史/24见证、原PPCPP逐决策、双指标、64精确搜索证书、前缀C/D/R、结束位置约束、reuse字节对应和报告表。搜索证书核验不只是路径上界审核，不需再跑BFS。verify.py是核心证书与数值核验，verify_delivery.py另审报告、复用记录和汇总。

需要重放时仅使用**不存在的同级新目录**，这会产生新的开发重放调用，不修改当前封存，也不并入本轮计数。当前交付没有重复执行这项性能重放：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP小图最优差距诊断_v0.2_20261020/replay.py --destination ./PPCPP小图诊断_独立重放
```

重放按已登记规则重做271夹具、4准备、2包装门槛、24原PPCPP与最多120精确查询，按例落盘，并与本轮保存的route/trace及精确长度/见证核对；只生成和审核原始证据，不生成沿用“复用准备”说法的报告。计时允许变化，不因限额终止提高上限。已有完整run.py可续接完整已落盘查询；若出现请求/证书已写、结果未写的半项，先保留故障证据，另版处理，不能覆盖重跑。

仅重画保存图（不调用算法）示例：

```powershell
$env:SMALLGAP_PLOT_DEPS=Join-Path $env:TEMP 'codex-smallgap-plot-deps'
& ./运行环境/python/python.exe -B -X utf8 PPCPP小图最优差距诊断_v0.2_20261020/plot.py
```

封存后优先只读核验；重建报告/图请在副本进行，不改manifest内文件。旧v0.1因门槛查找文件类型错误中止，详见STOPPED.md、版本影响说明.md、reuse.json；正式有效结果只来自v0.2。
