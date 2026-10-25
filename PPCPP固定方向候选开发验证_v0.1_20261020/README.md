# PPCPP固定方向候选阶段A交付

已封存，待负责人审核。先读结果报告.md和方向语义审查.md。

- stage_a_prereg.json：零规划器源码/整数边界检查规则。
- stage_a_results.json：20源码SHA256、真实旧worker导入来源/哈希及54输入哈希/216个边界判断。
- stage_a.py / stage_a.log：纯标准库源审，不导入或调用规划器，不运行BFS/路径搜索。
- review_packet.md：停止原因及负责人待裁决点。
- manifest.json / verify.py / verify.log：只读复核；manifest只排除自身和验证日志。

在项目根执行：

```powershell
./运行环境/python/python.exe -B -X utf8 PPCPP固定方向候选开发验证_v0.1_20261020/verify.py
```

本目录沿用执行稿目录名仅作阶段A证据容器。PPCPP_ORIENT4_v0.1尚未实现、未验收、无性能结果。未进行216核心门槛、3组合入口、486正式入口或其内部调用。
