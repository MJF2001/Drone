# LAST距离查询等价提速 v0.2

执行完成，待负责人审核。先读[结果](LAST距离查询等价提速结果.md)和[审核包](review_packet.md)。810正式调用后已停止；未覆盖历史或使用留出。

- protocol.json、预登记.md、input_seal.json、formal_order.json：调用前固定114输入、10夹具、810顺序/共同20秒/停止规则。
- 修改范围与等价依据.md、minimal_candidate.diff、wrapper.diff、candidate_v1.py/v2.py、runtime.py、isolation.py/worker.py：唯一机制改动及必要隔离；source_seal.json是通过门槛后、正式前的封存。
- gate_index.json、gates/：259新门槛完整原输出/外审；cache_gate、path_direction_gate、bfs_internal_deadline、distance_diagnostics：缓存/连接/截止/54几何查询。无精确覆盖调用。
- jobs/、execution/、actual_order.jsonl、completion.json、run.log：全部810新任务、结果、日志与真实顺序；每份输出含输入哈希、唯一读取、模块来源和关键生产源码哈希。
- analysis.json、810调用时间与分段.csv、54状态配对.csv、分层时间配对.csv、完整路线指标.csv：独立逐决策和双指标重核，所有重复、不利候选及分层均保留。
- imported_dependency_inventory.json：计时后补充的完整导入文件清单。90个预加载可选包文件未事前逐文件封存，不能把此清单当成事前证明。failures.json包含此来源限制和一次离线统计启动次序失败，正式失效/重跑0。
- manifest.json：交付内容哈希，含全部原始/源码/输入/日志；只排除manifest自身与会被复核命令输出的verify.log。verify.py只读重审，不调用规划器。

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST距离查询等价提速_v0.2_20261020/verify.py
```
