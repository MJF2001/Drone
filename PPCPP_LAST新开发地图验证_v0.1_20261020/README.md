# 固定LAST新开发地图验证 v0.1

**执行完成，待负责人审核。** 先看[结果报告](LAST新开发地图验证结果.md)及[审核包](review_packet.md)。54状态由9基础道路共享历史派生，不是54独立图或最终留出。算法固定不改，本轮精确搜索调用0。

项目根目录一键只读核验：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST新开发地图验证_v0.1_20261020/verify_v02.py
```

核9准备、54历史/可行见证、108等价门槛、540正式全部P0/P1/final逐决策和双指标、270P0配对、108组5重复、143旧输入比较、D4形状第二实现、54报告行及manifest。重做审核BFS，不调用规划器、精确搜索或追加图，约需十余秒。本机Python3.12.14/Windows，项目便携运行时；不声称其他电脑已验证。

运行模块candidate/runtime/worker与audit/common逐字节复用已审核版。audit_adapter仅在计时外缓存同输入的独立BFS距离，前置60查询与未缓存版本双核，不进入生产，不算算法提速。旧218边界/9截止/8夹具界只引用封存；新几何和障碍首备、历史被挡、当前采集、尺寸/可达门槛均正式前完成。

spec/setup/几何坐标表/几何概览为生成前固定规则，protocol保护规则、旧数据来源和依赖；old_input_catalog/novelty逐条对照旧143原件；prep保存9事件前输入/结果/日志；inputs/witnesses为54新状态与前缀/可行见证；gates/gate_index为108新调用等价门槛；input/source_seal在正式前封存；jobs/execution为540独立进程完整输出及读路径；analysis含全部状态、调用与分支/分层/时间；CSV可独立导入。

无准备或正式失败/迟到、无重复或超规模槽位。交付审核首版verify.py因calls中tuple/JSON list表示不同整表比较失败，原脚本及verify_initial.log保留；verify_v02仅规范化这一比较，不改正式代码或结果，不重跑。不能称所有流程一遍通过。

需要全流程重放时，指定不存在的同级新目录；这会产生新的9准备、108门槛及540正式重放调用，不并入本轮计数：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST新开发地图验证_v0.1_20261020/replay.py --destination ./PPCPP_LAST新开发_独立重放
```

当前交付未额外执行这项全量重放；本轮已有5次稳定性和全部独立规则审核。重放比较完整route/trace和分支状态，计时允许变化；不提高预算或换图。已有完整结果可续接；若job/日志已写而结果缺失，先保留中断证据另版处理，不覆盖重试。

封存后只读verify，重建报告/图在副本进行。plot.py仅绘保存输出，matplotlib位于临时依赖路径（plot_environment.json记录），不影响生产。未用留出、未改历史/冻结，不提交推送GitHub，固定矩阵结束后无自动下一轮。
